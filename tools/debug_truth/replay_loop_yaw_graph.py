#!/usr/bin/env python3
"""Replay the saved 074-02 loop_fusion 4DoF graph offline with one yaw-weight ablation.

Run inside the project's fixed d435i-vins:dev image. The Ceres backend sees only
saved VIO keyframes and PnP loop constraints. Gazebo truth is read later by this
evaluation script and never enters the optimizer.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools/debug_truth"))
from evaluate_odometry import rotation
from evaluate_vio_quality_alignment import _interpolate_position, _interpolate_quaternion

RUN_ID = "real-loop-20261022-074-02"
DEFAULT_RUN = ROOT / "artifacts/runs" / RUN_ID
GRAPH_POSITION_TOL_M = 5e-4
GRAPH_ROTATION_TOL_DEG = 0.01
TRANSFORM_POSITION_TOL_M = 5e-4
TRANSFORM_ROTATION_TOL_DEG = 0.01
TRAJECTORY_POSITION_RMSE_TOL_M = 1e-3
TRAJECTORY_YAW_RMSE_TOL_DEG = 0.01
MIN_LOOP_RESIDUAL_REDUCTION_FRACTION = 0.20
MIN_CYCLE7_YAW_RMSE_REDUCTION_FRACTION = 0.10
MAX_CYCLE7_POSITION_RMSE_REGRESSION_FRACTION = 0.05


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def wrap_deg(value):
    return (float(value) + 180.0) % 360.0 - 180.0


def ypr_matrix(yaw_deg, pitch_deg, roll_deg):
    yaw, pitch, roll = np.radians([yaw_deg, pitch_deg, roll_deg])
    rz = np.array([[np.cos(yaw), -np.sin(yaw), 0.0],
                   [np.sin(yaw), np.cos(yaw), 0.0],
                   [0.0, 0.0, 1.0]])
    ry = np.array([[np.cos(pitch), 0.0, np.sin(pitch)],
                   [0.0, 1.0, 0.0],
                   [-np.sin(pitch), 0.0, np.cos(pitch)]])
    rx = np.array([[1.0, 0.0, 0.0],
                   [0.0, np.cos(roll), -np.sin(roll)],
                   [0.0, np.sin(roll), np.cos(roll)]])
    return rz @ ry @ rx


def yaw_deg(matrix):
    return float(np.degrees(np.arctan2(matrix[1, 0], matrix[0, 0])))


def matrix_ypr_deg(matrix):
    n, o, a = matrix[:, 0], matrix[:, 1], matrix[:, 2]
    y = np.arctan2(n[1], n[0])
    p = np.arctan2(-n[2], n[0] * np.cos(y) + n[1] * np.sin(y))
    r = np.arctan2(a[0] * np.sin(y) - a[1] * np.cos(y),
                   -o[0] * np.sin(y) + o[1] * np.cos(y))
    return np.degrees([y, p, r]).tolist()


def rotation_error_deg(left, right):
    delta = left @ right.T
    cosine = np.clip((np.trace(delta) - 1.0) * 0.5, -1.0, 1.0)
    return float(np.degrees(np.arccos(cosine)))


def compile_replay(directory):
    source = ROOT / "tools/debug_truth/loop_graph_ceres_replay.cc"
    binary = directory / "loop_graph_ceres_replay"
    command = ["g++", "-std=c++17", "-O3", "-DNDEBUG", "-I/usr/include/eigen3",
               str(source), "-o", str(binary), "-lceres", "-lglog", "-lgflags", "-pthread"]
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError("Ceres replay helper did not compile:\n" + result.stderr)
    return binary, command


def make_stages(observation, diagnostics):
    relative_yaw = {entry["current_index"]: entry["relative_yaw_deg"]
                    for entry in observation["candidate_diagnostics"]
                    if entry.get("accepted")}
    revisions = []
    last_optimizations = 0
    for revision in observation["graph_revisions"]:
        keyframes, loops, optimizations = revision["revision"]
        if optimizations > last_optimizations:
            if optimizations != last_optimizations + 1:
                raise ValueError("Optimizer revisions contain a gap")
            if loops != optimizations:
                raise ValueError("This replay expects one optimization per accepted loop")
            graph = revision["graph"]
            if len(graph) != keyframes or graph[-1]["index"] != keyframes - 1:
                raise ValueError("Graph revision does not contain its full contiguous prefix")
            loop_nodes = [node for node in graph if node.get("loop_index", -1) >= 0]
            if len(loop_nodes) != loops:
                raise ValueError("Graph revision loop count differs from revision counters")
            for node in loop_nodes:
                if node["index"] not in relative_yaw:
                    raise ValueError(f"Missing captured PnP yaw for loop {node['index']}")
            first_loop_index = min(node["loop_index"] for node in loop_nodes)
            revisions.append({
                "optimization": optimizations,
                "verified_loops": loops,
                "current_index": graph[-1]["index"],
                "first_loop_index": first_loop_index,
                "graph": graph,
            })
            last_optimizations = optimizations
    if len(revisions) != 4:
        raise ValueError(f"Expected four optimizer snapshots, found {len(revisions)}")

    for stage in revisions:
        graph = stage["graph"]
        start, end = stage["first_loop_index"], stage["current_index"]
        rows = []
        for node in graph[start:end + 1]:
            loop_index = int(node.get("loop_index", -1))
            rel_t = node.get("loop_relative_t", [0.0, 0.0, 0.0])
            rows.append({
                "index": int(node["index"]),
                "vio_xyz": node["vio_xyz"],
                "vio_q_xyzw": node["vio_q_xyzw"],
                "loop_index": loop_index,
                "loop_relative_t": rel_t,
                "loop_relative_yaw_deg": relative_yaw.get(node["index"], 0.0),
            })
        stage["input_nodes"] = rows
        stage["first_loop_index"] = start
        stage["current_index"] = end
    if revisions[-1]["verified_loops"] != len(diagnostics["candidate_diagnostics"]["accepted_candidates"]):
        raise ValueError("Candidate diagnostic summary and graph disagree")
    return revisions


def encode_stage(stage, yaw_scale):
    nodes = stage["input_nodes"]
    first, current = stage["first_loop_index"], stage["current_index"]
    lines = [f"{first} {current} {yaw_scale:.17g} {len(nodes)}"]
    for n in nodes:
        xyz = n["vio_xyz"]
        q = n["vio_q_xyzw"]
        t = n["loop_relative_t"]
        has_loop = int(n["loop_index"] >= 0)
        lines.append(" ".join(str(v) for v in [
            n["index"], *xyz, *q, has_loop, n["loop_index"], *t,
            n["loop_relative_yaw_deg"]]))
    return "\n".join(lines) + "\n"


def run_one(binary, stage, yaw_scale):
    result = subprocess.run([str(binary)], input=encode_stage(stage, yaw_scale),
                            text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(f"Ceres replay failed for optimization {stage['optimization']}:\n{result.stderr}")
    parsed = {"nodes": {}, "summary": None}
    for line in result.stdout.splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == "SUMMARY":
            parsed["summary"] = {"initial_cost": float(fields[1]),
                                 "final_cost": float(fields[2]),
                                 "iterations": int(fields[3])}
        elif fields[0] == "NODE":
            values = [float(x) for x in fields[2:]]
            parsed["nodes"][int(fields[1])] = {
                "xyz": values[0:3], "ypr_deg": values[3:6],
                "rotation": ypr_matrix(*values[3:6]),
            }
    if parsed["summary"] is None or len(parsed["nodes"]) != len(stage["input_nodes"]):
        raise RuntimeError("Ceres replay returned an incomplete result")
    return parsed


def graph_baseline_check(stages, results):
    maxima = {"position_m": 0.0, "rotation_deg": 0.0, "yaw_deg": 0.0}
    checks = []
    for stage, replay in zip(stages, results):
        snapshot = {node["index"]: node for node in stage["graph"]}
        stage_max = {"position_m": 0.0, "rotation_deg": 0.0, "yaw_deg": 0.0}
        for index, pose in replay["nodes"].items():
            expected = snapshot[index]
            position_error = float(np.linalg.norm(np.asarray(pose["xyz"]) - expected["xyz"]))
            expected_r = rotation(expected["q_xyzw"])
            angle_error = rotation_error_deg(pose["rotation"], expected_r)
            yaw_error = abs(wrap_deg(yaw_deg(pose["rotation"]) - yaw_deg(expected_r)))
            stage_max["position_m"] = max(stage_max["position_m"], position_error)
            stage_max["rotation_deg"] = max(stage_max["rotation_deg"], angle_error)
            stage_max["yaw_deg"] = max(stage_max["yaw_deg"], yaw_error)
        for key in maxima:
            maxima[key] = max(maxima[key], stage_max[key])
        checks.append({"optimization": stage["optimization"], **stage_max,
                       "within_tolerance":
                           stage_max["position_m"] <= GRAPH_POSITION_TOL_M and
                           stage_max["rotation_deg"] <= GRAPH_ROTATION_TOL_DEG})
    return {"maxima": maxima, "snapshots": checks,
            "passed": all(item["within_tolerance"] for item in checks)}


def make_transforms(stages, results, drift_report):
    event_by_index = {step["nearest_loop_edge"]["current_index"]: step
                      for step in drift_report["measured_pose_transform_steps"]}
    transforms = []
    for stage, replay in zip(stages, results):
        index = stage["current_index"]
        if index not in event_by_index:
            raise ValueError(f"No measured odometry transform event for keyframe {index}")
        step = event_by_index[index]
        raw = next(node for node in stage["graph"] if node["index"] == index)
        raw_r = rotation(raw["vio_q_xyzw"])
        raw_yaw = yaw_deg(raw_r)
        optimized = replay["nodes"][index]
        delta_yaw = optimized["ypr_deg"][0] - raw_yaw
        delta_r = ypr_matrix(delta_yaw, 0.0, 0.0)
        raw_t = np.asarray(raw["vio_xyz"], dtype=float)
        drift_t = np.asarray(optimized["xyz"], dtype=float) - delta_r @ raw_t
        transforms.append({"optimization": stage["optimization"], "current_index": index,
                           "event_source_ns": int(step["source_ns"]),
                           "yaw_drift_deg": float(delta_yaw), "rotation": delta_r,
                           "translation": drift_t,
                           "graph_keyframe": {"vio_xyz": raw["vio_xyz"],
                                              "vio_q_xyzw": raw["vio_q_xyzw"],
                                              "optimized_xyz": optimized["xyz"],
                                              "optimized_ypr_deg": optimized["ypr_deg"]}})
    if [item["current_index"] for item in transforms] != [
            step["nearest_loop_edge"]["current_index"]
            for step in drift_report["measured_pose_transform_steps"]]:
        raise ValueError("Optimization order differs from observed transform order")
    return transforms


def compare_event_transforms(transforms, observation, raw_by_stamp):
    corrected_by_stamp = {int(row["source_ns"]): row for row in observation["odometry"]}
    checks = []
    for transform in transforms:
        stamp = transform["event_source_ns"]
        if stamp not in raw_by_stamp or stamp not in corrected_by_stamp:
            raise ValueError(f"Missing raw/corrected odometry pair at {stamp}")
        raw = raw_by_stamp[stamp]
        corrected = corrected_by_stamp[stamp]
        expected_p = transform["rotation"] @ np.asarray(raw["xyz"]) + transform["translation"]
        actual_p = np.asarray(corrected["xyz"], dtype=float)
        expected_r = transform["rotation"] @ rotation(raw["q_xyzw"])
        actual_r = rotation(corrected["q_xyzw"])
        position_error = float(np.linalg.norm(expected_p - actual_p))
        angle_error = rotation_error_deg(expected_r, actual_r)
        checks.append({"optimization": transform["optimization"], "source_ns": stamp,
                       "position_m": position_error, "rotation_deg": angle_error,
                       "within_tolerance": position_error <= TRANSFORM_POSITION_TOL_M and
                           angle_error <= TRANSFORM_ROTATION_TOL_DEG})
    return {"checks": checks, "passed": all(x["within_tolerance"] for x in checks)}


def evaluate_rows(transforms, comparison_rows, raw_by_stamp, truth_t, truth_p, truth_q,
                  align_r, align_t, lever):
    ordered = sorted(transforms, key=lambda item: item["event_source_ns"])
    output = []
    for row in comparison_rows:
        stamp = int(row["source_ns"])
        if stamp not in raw_by_stamp:
            raise ValueError(f"Comparison row has no captured raw VIO sample: {stamp}")
        raw = raw_by_stamp[stamp]
        transform = None
        for candidate in ordered:
            if candidate["event_source_ns"] <= stamp:
                transform = candidate
            else:
                break
        if transform is None:
            corr_r = np.eye(3)
            corr_t = np.zeros(3)
        else:
            corr_r, corr_t = transform["rotation"], transform["translation"]
        raw_p = np.asarray(raw["xyz"], dtype=float)
        raw_r = rotation(raw["q_xyzw"])
        corrected_p = corr_r @ raw_p + corr_t
        corrected_r = corr_r @ raw_r
        truth_pos, gap = _interpolate_position(truth_t, truth_p, stamp)
        if gap > 40_000_000:
            raise ValueError(f"Truth interpolation gap exceeds 40ms at {stamp}")
        truth_r = rotation(_interpolate_quaternion(truth_t, truth_q, stamp))
        actual_imu = truth_pos + truth_r @ lever
        raw_est = align_r @ raw_p + align_t
        corrected_est = align_r @ corrected_p + align_t
        aligned_raw_r = align_r @ raw_r
        aligned_corrected_r = align_r @ corrected_r
        output.append({
            "source_ns": stamp,
            "raw_position_error_m": float(np.linalg.norm(raw_est - actual_imu)),
            "corrected_position_error_m": float(np.linalg.norm(corrected_est - actual_imu)),
            "raw_yaw_error_deg": wrap_deg(yaw_deg(aligned_raw_r) - yaw_deg(truth_r)),
            "corrected_yaw_error_deg": wrap_deg(yaw_deg(aligned_corrected_r) - yaw_deg(truth_r)),
        })
    return output


def summarize_window(rows, begin_ns, end_ns):
    selected = [row for row in rows if begin_ns <= row["source_ns"] < end_ns]
    if len(selected) < 3:
        raise ValueError(f"Insufficient samples in return window: {len(selected)}")
    pos = np.asarray([row["corrected_position_error_m"] for row in selected])
    yaw = np.asarray([row["corrected_yaw_error_deg"] for row in selected])
    return {"samples": len(selected),
            "position_rmse_m": float(np.sqrt(np.mean(pos ** 2))),
            "yaw_rmse_deg": float(np.sqrt(np.mean(yaw ** 2)))}


def loop_residuals(stage, result):
    residuals = []
    for node in stage["graph"]:
        old = int(node.get("loop_index", -1))
        if old < 0:
            continue
        diag = next(d for d in stage["input_nodes"] if d["index"] == node["index"])
        old_yaw = result["nodes"][old]["ypr_deg"][0]
        current_yaw = result["nodes"][node["index"]]["ypr_deg"][0]
        residual = wrap_deg(current_yaw - old_yaw - diag["loop_relative_yaw_deg"])
        residuals.append({"old_index": old, "current_index": node["index"],
                          "target_yaw_deg": diag["loop_relative_yaw_deg"],
                          "residual_deg": residual, "absolute_residual_deg": abs(residual)})
    return residuals


def loop_factor_diagnostics(stage, result, yaw_scale):
    by_index = {node["index"]: node for node in stage["input_nodes"]}
    diagnostics = []
    for current in stage["graph"]:
        old_index = int(current.get("loop_index", -1))
        if old_index < 0:
            continue
        old_pose = result["nodes"][old_index]
        current_pose = result["nodes"][current["index"]]
        current_input = by_index[current["index"]]
        old_r = ypr_matrix(*old_pose["ypr_deg"])
        delta_world = np.asarray(current_pose["xyz"]) - np.asarray(old_pose["xyz"])
        predicted_relative_t = old_r.T @ delta_world
        translation_residual = (predicted_relative_t -
                                np.asarray(current_input["loop_relative_t"], dtype=float))
        yaw_residual = wrap_deg(current_pose["ypr_deg"][0] -
                                old_pose["ypr_deg"][0] -
                                current_input["loop_relative_yaw_deg"]) * yaw_scale
        # HuberLoss(delta=0.1) acts on the norm of the complete 4D residual block.
        # Here that block mixes meter-valued translation and degree-valued yaw.
        residual_norm = float(np.sqrt(np.dot(translation_residual, translation_residual)
                                       + yaw_residual * yaw_residual))
        rho_prime = 1.0 if residual_norm <= 0.1 else 0.1 / residual_norm
        diagnostics.append({
            "old_index": old_index, "current_index": current["index"],
            "translation_residual_xyz_m": translation_residual.tolist(),
            "translation_residual_norm_m": float(np.linalg.norm(translation_residual)),
            "scaled_yaw_residual_deg_numeric": float(yaw_residual),
            "combined_residual_norm_numeric": residual_norm,
            "huber_rho_prime": float(rho_prime),
            "huber_sqrt_irls_weight": float(np.sqrt(rho_prime)),
        })
    return diagnostics


def run(args):
    run_dir = args.run_dir.resolve()
    if run_dir.name != RUN_ID:
        raise ValueError(f"Expected the immutable run {RUN_ID}, got {run_dir}")
    load = lambda name: json.loads((run_dir / name).read_text())
    observation = load("loop-observation.json")
    candidate_summary = load("candidate-diagnostics-summary.json")
    drift_report = load("loop-drift-comparison.json")
    source_evaluation = load("real-loop-evaluation.json")
    previous_audit = json.loads((ROOT / "progress/evidence/loop-yaw-weight-audit-20261022-076.json").read_text())
    if observation["epoch"] != source_evaluation["epoch"] or observation["epoch"] != drift_report["epoch"]:
        raise ValueError("Input artifacts span different VINS epochs")
    if not all(source_evaluation["checks"].values()):
        raise ValueError("Original independent loop evaluation has failed checks")
    if not candidate_summary["integrity_checks"]["no_truth_input_to_backend"]:
        raise ValueError("Original loop backend had truth input")

    stages = make_stages(observation, candidate_summary)
    loop_steps = drift_report["measured_pose_transform_steps"]
    if len(loop_steps) != 4:
        raise ValueError("Expected four measured output-transform updates")

    with tempfile.TemporaryDirectory(prefix="loop-yaw-graph-replay-") as temp:
        binary, compiler_command = compile_replay(Path(temp))
        baseline = [run_one(binary, stage, 0.1) for stage in stages]
        graph_check = graph_baseline_check(stages, baseline)
        baseline_transforms = make_transforms(stages, baseline, drift_report)

        raw_rows = [entry for entry in (json.loads(line) for line in
                    (run_dir / "fixture-odometry.jsonl").read_text().splitlines())
                    if entry["kind"] == "raw"]
        raw_by_stamp = {int(entry["source_ns"]): entry for entry in raw_rows}
        event_check = compare_event_transforms(baseline_transforms, observation, raw_by_stamp)

        truth_rows = [json.loads(line) for line in
                      (run_dir / "fixture-truth.jsonl").read_text().splitlines()]
        truth_t = np.asarray([row["stamp_ns"] for row in truth_rows], dtype=np.int64)
        truth_p = np.asarray([row["xyz"] for row in truth_rows], dtype=float)
        truth_q = np.asarray([row["q_xyzw"] for row in truth_rows], dtype=float)
        alignment = drift_report["alignment"]
        align_r = np.asarray(alignment["rotation"], dtype=float)
        align_t = np.asarray(alignment["translation_m"], dtype=float)
        lever = np.asarray(alignment["model_to_imu_lever_arm_flu_m"], dtype=float)
        with (run_dir / "loop-drift-comparison.csv").open(newline="") as stream:
            comparison_rows = list(csv.DictReader(stream))
        for row in comparison_rows:
            row["source_ns"] = int(row["source_ns"])
        baseline_rows = evaluate_rows(baseline_transforms, comparison_rows, raw_by_stamp,
                                      truth_t, truth_p, truth_q, align_r, align_t, lever)
        baseline_trajectory_delta = {
            "max_position_error_difference_m": max(abs(a["corrected_position_error_m"] -
                float(b["loop_position_error_m"])) for a, b in zip(baseline_rows, comparison_rows)),
            "max_yaw_error_difference_deg": max(abs(wrap_deg(a["corrected_yaw_error_deg"] -
                float(b["loop_yaw_error_deg"]))) for a, b in zip(baseline_rows, comparison_rows)),
            "matched_rows": len(baseline_rows),
        }
        if len(baseline_rows) != len(comparison_rows):
            raise ValueError("Replayed output support differs from the saved paired comparison")

        return_windows = drift_report["repeated_return_hold_last_10_seconds"]
        baseline_window_checks = []
        cycle7_indices = [i for i, window in enumerate(return_windows) if window["cycle"] == 7]
        if len(cycle7_indices) != 1:
            raise ValueError("Expected one saved seventh-return window")
        replay_rows = baseline_rows
        for window in return_windows:
            begin_ns, end_ns = [int(round(value * 1e9))
                                for value in window["measurement_window_sim_s"]]
            measured = summarize_window(replay_rows, begin_ns, end_ns)
            saved = window["loop_corrected"]
            pos_delta = abs(measured["position_rmse_m"] -
                            saved["position_error_m"]["sample_rmse"])
            yaw_delta = abs(measured["yaw_rmse_deg"] -
                            saved["signed_yaw_error_deg"]["sample_rmse"])
            baseline_window_checks.append({"cycle": window["cycle"], **measured,
                "saved_position_rmse_m": saved["position_error_m"]["sample_rmse"],
                "saved_yaw_rmse_deg": saved["signed_yaw_error_deg"]["sample_rmse"],
                "position_delta_m": pos_delta, "yaw_delta_deg": yaw_delta,
                "within_tolerance": pos_delta <= TRAJECTORY_POSITION_RMSE_TOL_M and
                                    yaw_delta <= TRAJECTORY_YAW_RMSE_TOL_DEG})

        trajectory_baseline_check = {
            "paired_rows": len(comparison_rows),
            **baseline_trajectory_delta,
            "per_sample_within_tolerance":
                baseline_trajectory_delta["max_position_error_difference_m"] <= 5e-4 and
                baseline_trajectory_delta["max_yaw_error_difference_deg"] <= 0.01,
            "return_windows": baseline_window_checks,
            "all_windows_within_tolerance": all(x["within_tolerance"]
                                                for x in baseline_window_checks),
        }
        baseline_passed = (graph_check["passed"] and event_check["passed"] and
                           trajectory_baseline_check["per_sample_within_tolerance"] and
                           trajectory_baseline_check["all_windows_within_tolerance"])

        intervention = None
        if baseline_passed:
            changed = [run_one(binary, stage, 1.0) for stage in stages]
            changed_transforms = make_transforms(stages, changed, drift_report)
            changed_rows = evaluate_rows(changed_transforms, comparison_rows, raw_by_stamp,
                                         truth_t, truth_p, truth_q, align_r, align_t, lever)
            base_final_residuals = loop_residuals(stages[-1], baseline[-1])
            changed_final_residuals = loop_residuals(stages[-1], changed[-1])
            residual_before = float(np.mean([x["absolute_residual_deg"]
                                             for x in base_final_residuals]))
            residual_after = float(np.mean([x["absolute_residual_deg"]
                                            for x in changed_final_residuals]))
            residual_reduction = ((residual_before - residual_after) / residual_before
                                  if residual_before else 0.0)
            changed_windows = []
            for window in return_windows:
                begin_ns, end_ns = [int(round(value * 1e9))
                                    for value in window["measurement_window_sim_s"]]
                changed_windows.append({"cycle": window["cycle"],
                    **summarize_window(changed_rows, begin_ns, end_ns)})
            cycle7 = next(x for x in changed_windows if x["cycle"] == 7)
            baseline_cycle7 = next(x for x in baseline_window_checks if x["cycle"] == 7)
            yaw_reduction = ((baseline_cycle7["yaw_rmse_deg"] - cycle7["yaw_rmse_deg"])
                             / baseline_cycle7["yaw_rmse_deg"])
            position_regression = ((cycle7["position_rmse_m"] -
                                    baseline_cycle7["position_rmse_m"])
                                   / baseline_cycle7["position_rmse_m"])
            base_factor_diagnostics = loop_factor_diagnostics(stages[-1], baseline[-1], 0.1)
            changed_factor_diagnostics = loop_factor_diagnostics(stages[-1], changed[-1], 1.0)
            mean_huber_before = float(np.mean([x["huber_sqrt_irls_weight"]
                                               for x in base_factor_diagnostics]))
            mean_huber_after = float(np.mean([x["huber_sqrt_irls_weight"]
                                              for x in changed_factor_diagnostics]))
            yaw_effect_observed = (residual_reduction >= MIN_LOOP_RESIDUAL_REDUCTION_FRACTION and
                                   yaw_reduction >= MIN_CYCLE7_YAW_RMSE_REDUCTION_FRACTION)
            raw_cycle7 = next(x for x in return_windows if x["cycle"] == 7)["raw_vins"]
            position_reduction_vs_raw = (1.0 - cycle7["position_rmse_m"] /
                raw_cycle7["position_error_m"]["sample_rmse"])
            supported = (residual_reduction >= MIN_LOOP_RESIDUAL_REDUCTION_FRACTION and
                         yaw_reduction >= MIN_CYCLE7_YAW_RMSE_REDUCTION_FRACTION and
                         position_regression <= MAX_CYCLE7_POSITION_RMSE_REGRESSION_FRACTION)
            intervention = {
                "single_change": "loop yaw residual scale 0.1 -> 1.0; all input poses, translations, local factors, Huber(0.1), initialization, solver and five-iteration cap held fixed",
                "baseline_mean_abs_final_loop_yaw_residual_deg": residual_before,
                "scale1_mean_abs_final_loop_yaw_residual_deg": residual_after,
                "loop_residual_reduction_fraction": residual_reduction,
                "final_loop_yaw_residuals_scale01": base_final_residuals,
                "final_loop_yaw_residuals_scale1": changed_final_residuals,
                "return_windows_scale01": [x for x in baseline_window_checks],
                "return_windows_scale1": changed_windows,
                "cycle7_yaw_rmse_reduction_fraction": yaw_reduction,
                "cycle7_position_rmse_regression_fraction": position_regression,
                "cycle7_scale1_position_rmse_reduction_vs_raw_fraction": position_reduction_vs_raw,
                "final_loop_factor_diagnostics_scale01": base_factor_diagnostics,
                "final_loop_factor_diagnostics_scale1": changed_factor_diagnostics,
                "mean_huber_sqrt_irls_weight_scale01": mean_huber_before,
                "mean_huber_sqrt_irls_weight_scale1": mean_huber_after,
                "mean_huber_sqrt_irls_weight_change": mean_huber_after - mean_huber_before,
                "yaw_weight_limiter_effect_observed": bool(yaw_effect_observed),
                "position_tradeoff_within_predeclared_limit": bool(
                    position_regression <= MAX_CYCLE7_POSITION_RMSE_REGRESSION_FRACTION),
                "predeclared_decision_thresholds": {
                    "minimum_mean_abs_loop_yaw_residual_reduction_fraction": MIN_LOOP_RESIDUAL_REDUCTION_FRACTION,
                    "minimum_cycle7_yaw_rmse_reduction_fraction": MIN_CYCLE7_YAW_RMSE_REDUCTION_FRACTION,
                    "maximum_cycle7_position_rmse_regression_fraction": MAX_CYCLE7_POSITION_RMSE_REGRESSION_FRACTION,
                },
                "supports_weighting_hypothesis_under_joint_thresholds": bool(supported),
            }

        input_names = ["loop-observation.json", "candidate-diagnostics-summary.json",
                       "real-loop-evaluation.json", "loop-drift-comparison.json",
                       "loop-observer-manifest.json",
                       "fixture-odometry.jsonl", "fixture-truth.jsonl", "fixture-stages.json"]
        inputs = {name: sha256(run_dir / name) for name in input_names}
        source_names = [
            "src/vendor/vins_fusion/loop_fusion/src/pose_graph.cpp",
            "src/vendor/vins_fusion/loop_fusion/src/pose_graph.h",
            "src/vendor/vins_fusion/loop_fusion/src/pose_graph_node.cpp",
            "src/vendor/vins_fusion/loop_fusion/src/keyframe.cpp",
            "src/vendor/vins_fusion/loop_fusion/src/utility/utility.h",
            "tools/debug_truth/loop_graph_ceres_replay.cc",
            "tools/debug_truth/replay_loop_yaw_graph.py",
        ]
        source_hashes = {name: sha256(ROOT / name) for name in source_names}
        dependency_lock = (ROOT / "dependencies/sources.json").read_text()
        pinned_source_names = {
            "src/vendor/vins_fusion/loop_fusion/src/pose_graph.cpp",
            "src/vendor/vins_fusion/loop_fusion/src/pose_graph.h",
            "src/vendor/vins_fusion/loop_fusion/src/pose_graph_node.cpp",
        }
        lock_matches = {name: source_hashes[name] in dependency_lock
                        for name in sorted(pinned_source_names)}
        input_lock_matches = all(inputs[name] == digest for name, digest in
                                 previous_audit["input_sha256"].items())
        result = {
            "goal": "#077: deterministic offline replay of 074-02 loop_fusion 4DoF graph and single yaw-scale ablation",
            "status": "ab_test_completed" if baseline_passed else "baseline_replay_failed_ab_stopped",
            "run_id": RUN_ID,
            "epoch": observation["epoch"],
            "scope": "Offline only; no simulation, navigation, PX4, truth input to Ceres, production source/config/control change, or session stitching.",
            "execution_environment": {
                "image": "d435i-vins:dev",
                "image_id": json.loads((ROOT / "config/runtime.json").read_text())["image_id"],
                "network_disabled": True,
                "workspace_mount_read_only": True,
                "ceres_package": subprocess.run(["dpkg-query", "-W", "-f=${Version}", "libceres-dev"],
                    capture_output=True, text=True).stdout.strip(),
                "compiler": subprocess.run(["g++", "--version"], capture_output=True,
                    text=True).stdout.splitlines()[0],
                "compile_command": compiler_command,
                "solver": {"linear_solver": "SPARSE_NORMAL_CHOLESKY", "max_iterations": 5,
                           "loss": "Huber(0.1) for each loop block; none for local edges"},
            },
            "captured_graph": {"optimization_snapshots": len(stages),
                "keyframes_at_final_snapshot": len(stages[-1]["graph"]),
                "verified_loop_edges": stages[-1]["verified_loops"],
                "edge_sequence_ids": "all online keyframes are constructed with sequence=1; no sequence-0 fixed nodes",
                "yaw_targets_from_saved_candidate_diagnostics": True},
            "predeclared_baseline_tolerances": {
                "graph_max_position_error_m": GRAPH_POSITION_TOL_M,
                "graph_max_full_rotation_error_deg": GRAPH_ROTATION_TOL_DEG,
                "output_event_position_error_m": TRANSFORM_POSITION_TOL_M,
                "output_event_rotation_error_deg": TRANSFORM_ROTATION_TOL_DEG,
                "trajectory_per_sample_position_error_difference_m": 5e-4,
                "trajectory_per_sample_yaw_error_difference_deg": 0.01,
                "return_position_rmse_difference_m": TRAJECTORY_POSITION_RMSE_TOL_M,
                "return_yaw_rmse_difference_deg": TRAJECTORY_YAW_RMSE_TOL_DEG,
            },
            "baseline_replay": {
                "loop_yaw_scale": 0.1,
                "graph_check": graph_check,
                "measured_output_transform_check": event_check,
                "trajectory_check": trajectory_baseline_check,
                "passed": bool(baseline_passed),
                "optimizer_stage_summaries": [x["summary"] for x in baseline],
            },
            "intervention": intervention,
            "checks": {"all_original_independent_evaluation_checks_pass": all(source_evaluation["checks"].values()),
                       "no_truth_input_to_backend": candidate_summary["integrity_checks"]["no_truth_input_to_backend"],
                       "source_file_hashes_match_dependency_lock": lock_matches,
                       "previous_audit_input_hashes_rechecked": input_lock_matches},
            "source_sha256": source_hashes,
            "input_sha256": inputs,
            "limitations": [
                "A successful replay is a deterministic graph-level intervention on one saved run, not a repeated end-to-end result.",
                "Ceres receives only VIO poses and saved PnP edges; Gazebo truth is used only by the separate post-solve scorer.",
                "The scale-1.0 result is an offline diagnostic candidate and is not installed in the runtime or qualified for PX4 control.",
            ],
        }
        result["checks"]["baseline_replay_passed"] = bool(baseline_passed)
        result["checks"]["ab_intervention_run"] = intervention is not None
        result["checks"]["hypothesis_supported_under_predeclared_thresholds"] = (
            intervention["supports_weighting_hypothesis_under_joint_thresholds"] if intervention else None)
        result["checks"]["yaw_weight_limiter_effect_observed"] = (
            intervention["yaw_weight_limiter_effect_observed"] if intervention else None)
        return result


def render_markdown(report):
    baseline = report["baseline_replay"]
    lines = [
        "# #077：074-02 loop_fusion yaw权重离线重放",
        "",
        "## 预先约定与基线复现",
        "",
        "在同一 `d435i-vins:dev` 固定镜像内、断网且以只读方式挂载工作区，使用 Ceres 对四次保存的优化快照逐次重放。优化器输入只含 VIO 关键帧与已接受的 PnP 相对约束；真值只用于求解结束后的独立误差评分。基线固定为回环 yaw 残差缩放 0.1、Huber(0.1)、局部四邻边和最多5次迭代。",
        "",
        f"基线复现：**{'通过' if baseline['passed'] else '失败'}**。预设门限为关键帧位置最大差≤{report['predeclared_baseline_tolerances']['graph_max_position_error_m'] * 1000:.1f}mm、全姿态最大差≤{report['predeclared_baseline_tolerances']['graph_max_full_rotation_error_deg']:.3f}°；四个输出变换及4,586对轨迹样本也与074-02记录逐项对照。",
        "",
        "| 优化快照 | 最大位置差 | 最大姿态差 | 结果 |",
        "|---:|---:|---:|---|",
    ]
    for item in baseline["graph_check"]["snapshots"]:
        lines.append(f"| {item['optimization']} | {item['position_m'] * 1000:.6f} mm | {item['rotation_deg']:.8f}° | {'通过' if item['within_tolerance'] else '失败'} |")
    lines += ["", f"全程对照最大位置误差差值 {baseline['trajectory_check']['max_position_error_difference_m'] * 1000:.6f}mm；最大yaw误差差值 {baseline['trajectory_check']['max_yaw_error_difference_deg']:.8f}°。",
              "", "## 单变量干预", ""]
    intervention = report["intervention"]
    if not intervention:
        lines += ["基线未通过，因此按预设规则停止，没有运行权重干预。"]
    else:
        cycle7_base = next(x for x in intervention["return_windows_scale01"] if x["cycle"] == 7)
        cycle7_alt = next(x for x in intervention["return_windows_scale1"] if x["cycle"] == 7)
        lines += [
            "只将回环 yaw 残差缩放从0.1改为1.0；PnP数据、平移残差、局部边、Huber、初始化和Ceres选项保持一致。",
            "",
            "| 指标 | 缩放0.1 | 缩放1.0 | 变化 |",
            "|---|---:|---:|---:|",
            f"| 四条最终回环平均绝对yaw残差 | {intervention['baseline_mean_abs_final_loop_yaw_residual_deg']:.6f}° | {intervention['scale1_mean_abs_final_loop_yaw_residual_deg']:.6f}° | 降低 {intervention['loop_residual_reduction_fraction'] * 100:.2f}% |",
            f"| 第7次返航末10秒yaw RMSE | {cycle7_base['yaw_rmse_deg']:.6f}° | {cycle7_alt['yaw_rmse_deg']:.6f}° | {intervention['cycle7_yaw_rmse_reduction_fraction'] * 100:.2f}%降低 |",
            f"| 第7次返航末10秒位置RMSE | {cycle7_base['position_rmse_m'] * 100:.4f}cm | {cycle7_alt['position_rmse_m'] * 100:.4f}cm | {intervention['cycle7_position_rmse_regression_fraction'] * 100:.2f}%回归 |",
            "",
            f"yaw权重限制航向修正的作用**{'得到支持' if intervention['yaw_weight_limiter_effect_observed'] else '未得到支持'}**：回环残差和返航yaw RMSE均超过预设改善门限。但该单变量调整**{'通过' if intervention['supports_weighting_hypothesis_under_joint_thresholds'] else '未通过'}**完整接受门限，因为位置RMSE回归为{intervention['cycle7_position_rmse_regression_fraction'] * 100:.2f}%，上限为5%；不能据此直接提高默认权重。缩放1.0的位置RMSE仍比原始VINS低{intervention['cycle7_scale1_position_rmse_reduction_vs_raw_fraction'] * 100:.2f}%。",
            "",
            "| 回环边 | 平移残差范数 (0.1→1.0) | yaw残差块值 (0.1→1.0) | Huber平方根权重 (0.1→1.0) |",
            "|---|---:|---:|---:|",
        ]
        for before, after in zip(intervention["final_loop_factor_diagnostics_scale01"],
                                 intervention["final_loop_factor_diagnostics_scale1"]):
            lines.append(f"| {before['old_index']}→{before['current_index']} | {before['translation_residual_norm_m']:.4f}→{after['translation_residual_norm_m']:.4f} m | {before['scaled_yaw_residual_deg_numeric']:.4f}→{after['scaled_yaw_residual_deg_numeric']:.4f} | {before['huber_sqrt_irls_weight']:.4f}→{after['huber_sqrt_irls_weight']:.4f} |")
        lines += [
            "",
            f"同一Huber损失作用于含平移与yaw的整个4维回环残差块；按最终因子残差计算，其平均平方根权重由{intervention['mean_huber_sqrt_irls_weight_scale01']:.4f}变为{intervention['mean_huber_sqrt_irls_weight_scale1']:.4f}。这是位置回归可能与共享鲁棒降权耦合的线索；本轮没有单独干预Huber，因此不能认定它是回归原因。",
        ]
    lines += ["", "## 边界", "",
              "这是同一条已存档图上的离线干预，不能证明换权重后新回环更准确，也不能保证多次运行不漂移。缩放1.0尚未进入生产源码、参数或控制链路；不构成飞行验收。",
              "", f"运行身份、输入与源码SHA-256见同目录[JSON报告](loop-yaw-weight-replay-20261022-077.json)。基线状态：`{report['status']}`。", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path)
    args = parser.parse_args()
    report = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
    if args.markdown:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(render_markdown(report))
    print(json.dumps({"status": report["status"], "baseline_passed": report["baseline_replay"]["passed"],
                      "intervention_ran": report["intervention"] is not None,
                      "intervention_supported": report["checks"]["hypothesis_supported_under_predeclared_thresholds"],
                      "output": str(args.output)}, ensure_ascii=False))
    return 0 if report["baseline_replay"]["passed"] else 3


if __name__ == "__main__":
    sys.exit(main())
