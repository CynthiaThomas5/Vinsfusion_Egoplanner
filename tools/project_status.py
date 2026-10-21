#!/usr/bin/env python3
"""Read-only scaffold/design check. Never starts ROS or validates flight."""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

root = Path(__file__).resolve().parents[1]
errors = []
optional_artifact_links = []
required = ["README.md", "AGENTS.md", "docs/architecture.md", "docs/contracts.md",
            "docs/directory-layout.md", "docs/source-migration.md", "docs/acceptance.md",
            "dependencies/sources.json", "dependencies/initial-sources.json",
            "progress/CURRENT.md", "progress/milestones.json",
            "collaboration/dialogues/TEMPLATE.md", "progress/changes/TEMPLATE.md"]
for rel in required:
    if not (root / rel).is_file():
        errors.append("Missing required file: " + rel)
for rel in ["src/own", "src/vendor", "simulation/models", "simulation/worlds",
            "simulation/airframes", "config/components", "docker",
            "dependencies/patches", "progress/evidence", "artifacts", "external"]:
    if not (root / rel).is_dir():
        errors.append("Missing required directory: " + rel)

packages = []
for manifest in sorted((root / "src/own").glob("*/package.xml")):
    try:
        package = ET.parse(manifest).getroot()
        name = package.findtext("name")
        if name != manifest.parent.name:
            errors.append(str(manifest.relative_to(root)) + ": package name does not match directory")
        packages.append(name or manifest.parent.name)
    except (ET.ParseError, OSError) as exc:
        errors.append(str(manifest.relative_to(root)) + ": " + str(exc))

data = {}
for folder in ["config", "dependencies", "progress"]:
    for path in (root / folder).rglob("*.json"):
        try:
            data[path.relative_to(root).as_posix()] = json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            errors.append(str(path.relative_to(root)) + ": " + str(exc))

for name in ["debug_truth", "vio_mapping", "vio_closed_loop"]:
    key = "config/profiles/" + name + ".json"
    profile = data.get(key, {})
    status = profile.get("status")
    runtime_ready = profile.get("runtime_ready")
    if profile.get("name") != name:
        errors.append(key + ": profile name does not match its filename")
    if status not in ["design_only", "in_progress", "runtime_ready"]:
        errors.append(key + ": invalid profile lifecycle status")
    if not isinstance(runtime_ready, bool):
        errors.append(key + ": runtime_ready must be boolean")
    elif (status == "runtime_ready") != runtime_ready:
        errors.append(key + ": runtime_ready must match the lifecycle status")
    if name == "vio_closed_loop":
        for field in ["ground_truth_online_allowed", "px4_debug_position_allowed", "gps_position_aiding_allowed"]:
            if profile.get(field) is not False:
                errors.append(key + ": prohibited online aiding: " + field)
        if any(profile.get(field) != "vins" for field in ["mapping_localization", "planner_localization"]):
            errors.append(key + ": map and planner must use VINS")
        if profile.get("px4_position_source") != "vins_external_odometry":
            errors.append(key + ": PX4 must use VINS external odometry")

vio_bridge = data.get("config/components/px4_bridge/vio_closed_loop.json", {})
vio_frames = data.get("config/components/px4_bridge/frames_vio_closed_loop.json", {})
px4_clock_config = data.get("config/components/px4_bridge/debug_truth.json", {})
px4_parameter_config = data.get("config/components/px4_bridge/ekf2_debug_truth.json", {})
dds_time_sync = px4_clock_config.get("uxrce_dds_time_sync_enabled")
dds_time_sync_param = px4_parameter_config.get("parameters", {}).get("UXRCE_DDS_SYNCT")
if type(dds_time_sync) is not bool:
    errors.append("PX4 bridge config must declare uXRCE DDS time sync as a boolean")
elif dds_time_sync_param != int(dds_time_sync):
    errors.append("PX4 UXRCE_DDS_SYNCT must match the shared clock-domain config")
if px4_clock_config.get("px4_clock_domain") == "gazebo_lockstep" and dds_time_sync is not False:
    errors.append("Gazebo lockstep profile must use the direct simulation clock")
sensor_bridge_path = root / "config/components/simulation/d435i_bridge.yaml"
truth_bridge_path = root / "config/components/simulation/debug_truth_bridge.yaml"
vio_launch_path = root / "src/own/uav_px4_bridge/launch/vio_closed_loop_px4.launch.py"
if sensor_bridge_path.is_file() and "/debug_truth/" in sensor_bridge_path.read_text():
    errors.append("D435i sensor bridge must not expose debug_truth topics")
if truth_bridge_path.is_file() and "/debug_truth/base_odometry" not in truth_bridge_path.read_text():
    errors.append("debug truth bridge must contain the isolated Gazebo odometry input")
if vio_launch_path.is_file():
    vio_launch = vio_launch_path.read_text()
    if "d435i_bridge.yaml" not in vio_launch or "debug_truth" in vio_launch:
        errors.append("VIO launch must bridge D435i sensors without loading truth")
if vio_bridge:
    if vio_bridge.get("profile") != "vio_closed_loop":
        errors.append("VIO bridge config profile mismatch")
    if vio_bridge.get("shared_control_config") != "debug_truth.json":
        errors.append("VIO bridge must reference the single shared PX4 control configuration")
    if (type(vio_bridge.get("px4_autostart_id")) is not int
            or vio_bridge.get("px4_autostart_id") <= 4000
            or vio_bridge.get("px4_autostart_id")
            == data.get("config/components/px4_bridge/ekf2_debug_truth.json", {}).get("autostart_id")):
        errors.append("VIO bridge must use an isolated custom PX4 autostart ID")
    if any("debug_truth" in key for key in vio_bridge):
        errors.append("VIO bridge config must not contain debug_truth input keys")
    for key in ["control_rate_hz", "prestream_wall_s", "vehicle_odometry_topic",
                "system_id", "clock_mapping_min_samples"]:
        if key in vio_bridge:
            errors.append("VIO bridge config duplicates shared control setting: " + key)
    expected_topics = {
        "clock_topic": "/clock",
        "localization_status_topic": "/localization/status",
        "optimized_odometry_topic": "/localization/optimized_imu_odom",
    }
    for key, expected in expected_topics.items():
        if vio_bridge.get(key) != expected:
            errors.append("VIO bridge config has an unexpected " + key)
if vio_frames:
    if (vio_frames.get("profile") != "vio_closed_loop"
            or vio_frames.get("ground_truth_online_allowed") is not False
            or vio_frames.get("gps_position_aiding_allowed") is not False):
        errors.append("VIO frame contract must prohibit truth and GPS aiding")

milestones = data.get("progress/milestones.json", {})
for entry in [milestones.get("bootstrap", {})] + milestones.get("stages", []):
    if entry.get("status") not in ["not_started", "in_progress", "passed"]:
        errors.append("Invalid milestone status")
    if entry.get("status") == "passed":
        evidence = entry.get("evidence", [])
        if not evidence:
            errors.append("Passed milestone missing evidence")
        for rel in evidence:
            if not rel.startswith("progress/evidence/") or not (root / rel).is_file():
                errors.append("Missing or misplaced evidence: " + rel)

for folder in [root, root / "docs", root / "collaboration", root / "progress"]:
    paths = folder.glob("*.md") if folder == root else folder.rglob("*.md")
    for path in paths:
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", path.read_text()):
            if "://" in target or target.startswith("#") or "..." in target:
                continue
            resolved = (path.parent / target.split("#")[0]).resolve()
            if not resolved.exists():
                # Large historical run data is intentionally absent from source deliveries.
                if resolved.is_relative_to(root / "artifacts"):
                    optional_artifact_links.append(str(path.relative_to(root)) + ": " + target)
                else:
                    errors.append(str(path.relative_to(root)) + ": broken link " + target)

if optional_artifact_links:
    print("Optional historical artifact links absent:", len(optional_artifact_links))
for message in errors:
    print("ERROR:", message)
print("Structure/design check:", "FAIL" if errors else "PASS")
print("Self-maintained ROS package manifests:", ", ".join(packages) if packages else "none")
print("ROS builds and SITL are outside this structural check")
stages = {item.get("id"): item.get("status") for item in milestones.get("stages", [])}
next_stage = next((key for key in ["P0", "P1", "P2", "P3", "P4", "P5", "P6"]
                   if stages.get(key) != "passed"), None)
next_steps = {
    "P0": "finish source and dependency freeze",
    "P1": "finish camera model and sensor qualification",
    "P2": "qualify VIO health/degradation gates and freeze acceptance criteria",
    "P3": "integrate EGO trajectory and obstacle navigation with PX4 bridge",
    "P4": "qualify VINS map/fault response, trajectory tracking, snapshots and sustained runtime",
    "P5": "verify VIO bridge EKF2 fusion with GNSS disabled",
    "P6": "complete A-H final acceptance and handoff",
}
print("Next:", next_steps.get(next_stage, "all listed milestones passed; audit GOAL.md A-H"))
sys.exit(1 if errors else 0)
