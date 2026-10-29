#!/usr/bin/env python3
"""Losslessly capture N10 stereo/IMU payload and source/receipt metadata.

The process is an offline observer. Recorder startup, write, disk, and coverage
errors are saved as evidence gaps and never affect navigation or PX4 control.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from n10_run_identity import read_run_identity, sha256_file
from observer_window import (safe_session_terminal_observed, install_observer_stop_handlers,
                             restore_observer_stop_handlers)


STREAM_ORDER = ("stereo_left_image", "stereo_right_image", "camera_imu")


def load_capture_inputs(root, config_path):
    root = Path(root).resolve()
    config_path = Path(config_path)
    if not config_path.is_absolute():
        config_path = root / config_path
    config = json.loads(config_path.read_text())
    if config.get("schema") != "uav-n10-capture/v1":
        raise ValueError("unsupported N10 capture config schema")
    sensor_path = root / config["sensor_config"]
    sensor = json.loads(sensor_path.read_text())
    topics = {stream: sensor[key]
              for stream, key in config["sensor_streams"].items()}
    if set(topics) != set(STREAM_ORDER) or len(set(topics.values())) != 3:
        raise ValueError("capture config must resolve three distinct sensor topics")
    return config, config_path, sensor_path, topics


def rosbag_command(run_dir, bag_dir, topics, identity, config_sha256,
                   cache_bytes=104857600):
    """Build the fixed-image rosbag2 command; this function has no ROS import."""
    command = [
        "ros2", "bag", "record", "--storage", "mcap", "--use-sim-time",
        "--disable-keyboard-controls", "--storage-preset-profile", "zstd_fast",
        "--max-cache-size", str(int(cache_bytes)),
        "--output", str(Path(bag_dir)), "--topics",
        *[topics[name] for name in STREAM_ORDER],
        "--custom-data", f"run_id={identity.get('run_id', '')}",
        f"runtime_contract_sha256={identity.get('runtime_contract_sha256', '')}",
        f"capture_config_sha256={config_sha256}",
    ]
    return command


def _atomic_json(path, data):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, allow_nan=False) + "\n")
    tmp.replace(path)


def _stamp_ns(stamp):
    return int(stamp.sec) * 1_000_000_000 + int(stamp.nanosec)


def record(run_dir, config_path, max_wall_s=1800.0, closeout_s=3.0):
    import rclpy
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.qos import (DurabilityPolicy, HistoryPolicy, QoSProfile,
                           ReliabilityPolicy)
    from rosgraph_msgs.msg import Clock
    from sensor_msgs.msg import Image, Imu
    from uav_interfaces.msg import MapStatus, NavigationCommand
    from rclpy.serialization import serialize_message
    run = Path(run_dir).resolve()
    config, config_file, sensor_file, topics = load_capture_inputs(ROOT, config_path)
    config_hash = sha256_file(config_file)
    sensor_hash = sha256_file(sensor_file)
    bag_dir = run / "n10-sensor-payload"
    receipt_path = run / "n10-sensor-receipts.jsonl"
    report_path = run / "n10-sensor-capture.json"
    if bag_dir.exists() or receipt_path.exists():
        raise FileExistsError("N10 sensor capture output already exists; use a new run directory")

    initial_identity = read_run_identity(run)
    command = rosbag_command(
        run, bag_dir, topics, initial_identity, config_hash,
        config["payload"]["rosbag_max_cache_bytes"])
    report = {
        "schema": "n10-sensor-capture/v1",
        "classification": "read-only offline capture; no flight decision",
        "read_only": True,
        "truth_subscribed": False,
        "control_published": False,
        "run_identity": initial_identity,
        "capture_config": str(config_file.relative_to(ROOT)),
        "capture_config_sha256": config_hash,
        "sensor_config": str(sensor_file.relative_to(ROOT)),
        "sensor_config_sha256": sensor_hash,
        "topics": topics,
        "payload_format": "rosbag2 MCAP with lossless zstd_fast chunk compression",
        "receipt_observer": {
            "sensor_subscription_qos": config["receipt_observer"][
                "sensor_subscription_qos"],
            "sensor_subscription_depth": config["receipt_observer"][
                "sensor_subscription_depth"],
            "flush_every_messages": config["receipt_observer"][
                "flush_every_messages"],
            "runtime_effect": False,
        },
        "receipt_metadata": receipt_path.name,
        "bag_directory": bag_dir.name,
        "bag_command": command,
        "capture_window": {"start_monotonic_ns": time.monotonic_ns()},
        "stream_counts": dict.fromkeys(STREAM_ORDER, 0),
        "source_stamp_regressions": dict.fromkeys(STREAM_ORDER, 0),
        "metadata_write_ok": True,
        "errors": [],
    }
    if int(config["payload"]["rosbag_max_cache_bytes"]) != 104857600:
        report["errors"].append("rosbag_cache_setting_differs_from_frozen_command")
    manifest_path = run / "n09-run-manifest.json"
    if not manifest_path.is_file():
        manifest_path = run / "n10-capture-launch-manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    declared_capture = manifest.get("n10_capture") or {}
    if declared_capture.get("enabled") is not True:
        report["errors"].append("n10_capture_not_enabled_in_run_manifest")
    if declared_capture.get("capture_config_sha256") != config_hash:
        report["errors"].append("capture_config_hash_differs_from_run_manifest")
    _atomic_json(report_path, report)

    bag_log = (run / "n10-sensor-bag.log").open("w")
    bag_process = None
    ledger = None
    node = None
    state = {"map": None, "command": None, "clock_ns": None}
    last_source = {}
    pending = 0
    safe_since = None
    stop_reason = "wall_timeout"
    started_mono = time.monotonic()
    stopped_by_signal = False
    previous_handlers = None
    executor = None
    monitor = None
    monitor_stop = threading.Event()
    window_finished = threading.Event()
    stop_state = {"reason": "wall_timeout"}
    bag_close_lock = threading.Lock()

    def close_bag():
        with bag_close_lock:
            if bag_process is None or bag_process.poll() is not None:
                return
            try:
                # Keep the receipt subscriber spinning until rosbag has stopped,
                # so all payload messages have a corresponding receipt row.
                report["bag_close_signal"] = "SIGTERM"
                os.killpg(bag_process.pid, signal.SIGTERM)
                bag_process.wait(timeout=30.0)
            except (OSError, subprocess.TimeoutExpired) as exc:
                report["errors"].append(
                    f"bag_close:{type(exc).__name__}:{exc}")
                if bag_process.poll() is None:
                    try:
                        report["bag_close_fallback_signal"] = "SIGKILL"
                        os.killpg(bag_process.pid, signal.SIGKILL)
                        bag_process.wait(timeout=5.0)
                    except (OSError, subprocess.TimeoutExpired):
                        pass
            report["bag_exit_code"] = bag_process.poll()

    def current_identity():
        mapping = state["map"]
        goal = state["command"]
        epoch = (getattr(mapping, "epoch", "") if mapping is not None else "")
        map_id = (getattr(mapping, "map_id", "") if mapping is not None else "")
        frame = (getattr(mapping.header, "frame_id", "")
                 if mapping is not None else "")
        goal_id = getattr(goal, "goal_id", "") if goal is not None else ""
        if not epoch and goal is not None:
            epoch = goal.epoch
        if not map_id and goal is not None:
            map_id = goal.map_id
        if not frame and epoch:
            frame = f"odom_{epoch}"
        identity = dict(initial_identity)
        identity.update({"goal_id": goal_id or initial_identity.get("goal_id", ""),
                         "epoch": epoch or initial_identity.get("epoch", ""),
                         "map_id": map_id or initial_identity.get("map_id", ""),
                         "frame_id": frame or initial_identity.get("frame_id", "")})
        identity["missing_fields"] = [key for key in (
            "run_id", "runtime_contract_sha256", "goal_id", "epoch", "map_id")
            if not identity.get(key)]
        conflicts = list(initial_identity.get("conflicts", []))
        if (identity.get("epoch") and identity.get("map_id")
                and not identity["map_id"].startswith(identity["epoch"] + "-")):
            conflicts.append("map_id_epoch_mismatch")
        if identity.get("epoch") and identity.get("frame_id") != f"odom_{identity['epoch']}":
            conflicts.append("frame_epoch_mismatch")
        identity["conflicts"] = sorted(set(conflicts))
        identity["complete"] = not identity["missing_fields"] and not identity["conflicts"]
        return identity

    try:
        try:
            bag_process = subprocess.Popen(command, stdout=bag_log, stderr=subprocess.STDOUT,
                                           start_new_session=True)
            report["bag_process_pid"] = bag_process.pid
        except (OSError, ValueError) as exc:
            report["errors"].append(f"bag_start:{type(exc).__name__}:{exc}")

        ledger = receipt_path.open("w", encoding="utf-8", buffering=1)
        rclpy.init()
        stop_request, previous_handlers = install_observer_stop_handlers()
        node = rclpy.create_node("n10_readonly_sensor_capture", parameter_overrides=[
            rclpy.parameter.Parameter("use_sim_time", value=True)])
        sensor_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=int(config["receipt_observer"]["sensor_subscription_depth"]),
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )
        clock_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=5,
            reliability=ReliabilityPolicy.BEST_EFFORT,
            durability=DurabilityPolicy.VOLATILE,
        )

        def on_stream(stream, message):
            nonlocal pending
            try:
                header = message.header
                source_ns = _stamp_ns(header.stamp)
                receipt_mono = time.monotonic_ns()
                old = last_source.get(stream)
                if old is not None and source_ns <= old:
                    report["source_stamp_regressions"][stream] += 1
                last_source[stream] = source_ns
                if hasattr(message, "data"):
                    data_bytes = len(message.data)
                else:
                    data_bytes = len(serialize_message(message))
                seq = getattr(message, "sequence", None)
                if seq is None:
                    seq = getattr(header, "seq", None)
                row = {
                    "stream": stream,
                    "topic": topics[stream],
                    "source_stamp_ns": source_ns,
                    "receipt_monotonic_ns": receipt_mono,
                    "receipt_wall_time_ns": time.time_ns(),
                    "sim_stamp_ns_at_receipt": state["clock_ns"],
                    "frame_id": str(header.frame_id),
                    "sequence_if_available": int(seq) if seq is not None else None,
                    "payload_data_bytes": data_bytes,
                    "identity": current_identity(),
                }
                ledger.write(json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n")
                pending += 1
                report["stream_counts"][stream] += 1
                report["last_receipt_monotonic_ns"] = receipt_mono
                if pending >= 32:
                    ledger.flush()
                    pending = 0
            except Exception as exc:  # evidence failure never escapes into control code
                report["metadata_write_ok"] = False
                error = f"receipt:{stream}:{type(exc).__name__}:{exc}"
                if error not in report["errors"]:
                    report["errors"].append(error)

        subscriptions = [
            node.create_subscription(Image, topics["stereo_left_image"],
                                     lambda msg: on_stream("stereo_left_image", msg),
                                     sensor_qos),
            node.create_subscription(Image, topics["stereo_right_image"],
                                     lambda msg: on_stream("stereo_right_image", msg),
                                     sensor_qos),
            node.create_subscription(Imu, topics["camera_imu"],
                                     lambda msg: on_stream("camera_imu", msg),
                                     sensor_qos),
            node.create_subscription(MapStatus, "/mapping/status",
                                     lambda msg: state.update(map=msg), 10),
            node.create_subscription(NavigationCommand, "/navigation/ego_goal",
                                     lambda msg: state.update(command=msg), 10),
            node.create_subscription(Clock, "/clock",
                                     lambda msg: state.update(clock_ns=_stamp_ns(msg.clock)),
                                     clock_qos),
        ]
        executor = SingleThreadedExecutor()
        executor.add_node(node)

        def monitor_window():
            nonlocal stop_reason, safe_since, stopped_by_signal
            while not monitor_stop.is_set():
                if stop_request.requested:
                    stopped_by_signal = True
                    stop_state["reason"] = ("observer_interrupted_after_safe_terminal"
                        if safe_session_terminal_observed(run)
                        else "observer_interrupted_before_safe_terminal")
                    break
                now = time.monotonic()
                if bag_process is not None and bag_process.poll() is not None:
                    report["bag_exit_code_before_close"] = bag_process.returncode
                    if "bag_process_exited_before_terminal" not in report["errors"]:
                        report["errors"].append("bag_process_exited_before_terminal")
                if safe_session_terminal_observed(run):
                    safe_since = safe_since or now
                    if now - safe_since >= closeout_s:
                        stop_reason = "safe_terminal_plus_closeout"
                        stop_state["reason"] = stop_reason
                        break
                else:
                    safe_since = None
                if now - started_mono >= max_wall_s:
                    stop_reason = "wall_timeout"
                    stop_state["reason"] = stop_reason
                    break
                monitor_stop.wait(0.05)
            close_bag()
            window_finished.set()
            executor.wake()

        monitor = threading.Thread(target=monitor_window,
                                   name="n10-capture-window-monitor", daemon=True)
        monitor.start()
        while not window_finished.is_set():
            executor.spin_once(timeout_sec=0.1)
        stop_reason = stop_state["reason"]
    except KeyboardInterrupt:
        stopped_by_signal = True
        stop_reason = ("observer_interrupted_after_safe_terminal"
                       if safe_session_terminal_observed(run)
                       else "observer_interrupted_before_safe_terminal")
    except Exception as exc:
        report["errors"].append(f"capture:{type(exc).__name__}:{exc}")
    finally:
        if previous_handlers is not None:
            restore_observer_stop_handlers(previous_handlers)
        monitor_stop.set()
        close_bag()
        if executor is not None:
            executor.shutdown(timeout_sec=5.0)
        if monitor is not None:
            monitor.join(timeout=5.0)
        report["capture_window"]["end_monotonic_ns"] = time.monotonic_ns()
        report["capture_window"]["wall_elapsed_s"] = time.monotonic() - started_mono
        report["capture_window"]["stop_reason"] = stop_reason
        report["capture_window"]["safe_session_terminal_observed"] = safe_session_terminal_observed(run)
        report["capture_window"]["observer_signal_received"] = stopped_by_signal
        report["run_identity_at_end"] = current_identity()
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()
        if ledger is not None:
            try:
                ledger.flush()
                ledger.close()
            except OSError as exc:
                report["metadata_write_ok"] = False
                report["errors"].append(f"receipt_close:{type(exc).__name__}:{exc}")
        if bag_process is not None:
            report["bag_exit_code"] = bag_process.poll()
        try:
            bag_log.close()
        except OSError:
            pass
        if receipt_path.is_file():
            report["receipt_sha256"] = sha256_file(receipt_path)
        report["bag_metadata_sha256"] = (
            sha256_file(bag_dir / "metadata.yaml")
            if (bag_dir / "metadata.yaml").is_file() else None)
        _atomic_json(report_path, report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--config", default="config/n10_capture.json")
    parser.add_argument("--max-wall-s", type=float, default=3600.0)
    parser.add_argument("--closeout-s", type=float, default=3.0)
    parser.add_argument("--dry-run", action="store_true",
                        help="print resolved topics, hash, storage bound, and rosbag2 command")
    args = parser.parse_args()
    run = args.run_dir.resolve()
    if not run.is_dir():
        parser.error("run directory must exist")
    try:
        config, config_file, _, topics = load_capture_inputs(ROOT, args.config)
        identity = read_run_identity(run)
        command = rosbag_command(run, run / "n10-sensor-payload", topics,
                                 identity, sha256_file(config_file),
                                 config["payload"]["rosbag_max_cache_bytes"])
        if args.dry_run:
            size = config["capacity_planning"]
            image_bps = (size["camera_resolution_px"][0]
                         * size["camera_resolution_px"][1]
                         * size["camera_rate_hz_each"]
                         * size["camera_stream_count"])
            payload_bps = (image_bps + size["imu_rate_hz"]
                           * size["imu_serialized_size_budget_bytes_per_message"])
            worst_case = int(payload_bps * size["planning_duration_sim_s"]
                             * size["safety_factor"])
            print(json.dumps({
                "run_identity": identity,
                "topics": topics,
                "config_sha256": sha256_file(config_file),
                "recommended_free_bytes": config["capacity_planning"]["recommended_free_bytes"],
                "computed_raw_with_reserve_bytes": worst_case,
                "receipt_queue_memory_budget_bytes": config["capacity_planning"][
                    "receipt_queue_memory_budget_bytes"],
                "runtime_admission_gate": False,
                "rosbag_command": command,
            }, indent=2))
            return
        record(run, args.config, args.max_wall_s, args.closeout_s)
    except Exception as exc:
        failure = {
            "schema": "n10-sensor-capture/v1",
            "classification": "INSUFFICIENT offline capture; no runtime effect",
            "read_only": True,
            "control_published": False,
            "run_identity": read_run_identity(run),
            "errors": [f"{type(exc).__name__}:{exc}"],
            "safe_session_terminal_observed": safe_session_terminal_observed(run),
        }
        failure_path = run / "n10-sensor-capture.json"
        if not failure_path.exists():
            _atomic_json(failure_path, failure)
        print(json.dumps({"capture": "INSUFFICIENT", "error": failure["errors"][0]}))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
