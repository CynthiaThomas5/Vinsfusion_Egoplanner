#!/usr/bin/env python3
"""Package one captured EGO occupied cloud with same-epoch provenance."""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def map_id_at(log_path, epoch, wall_epoch_s):
    pattern = re.compile(
        r"\[INFO\] \[([0-9.]+)\] \[mapping_input_adapter\]: "
        r"plan_env cleared for map_id (\S+)"
    )
    matches = []
    for line in log_path.read_text(errors="replace").splitlines():
        match = pattern.search(line)
        if match and float(match.group(1)) <= wall_epoch_s:
            matches.append(match.group(2))
    if not matches:
        raise ValueError("no map reset acknowledgement precedes the cloud sample")
    selected = matches[-1]
    if not selected.startswith(f"{epoch}-"):
        raise ValueError("cloud sample and active map id belong to different epochs")
    return selected


def read_pcd(path):
    lines = path.read_text().splitlines()
    marker = lines.index("DATA ascii")
    header = {}
    for line in lines[:marker]:
        fields = line.split()
        if fields:
            header[fields[0]] = fields[1:]
    if header.get("FIELDS") != ["x", "y", "z"]:
        raise ValueError("unexpected PCD fields")
    points = [[float(value) for value in row.split()]
              for row in lines[marker + 1:] if row.strip()]
    if len(points) != int(header["POINTS"][0]):
        raise ValueError("PCD point count does not match its header")
    return points


def export(args):
    report = json.loads(args.run_report.read_text())
    probe = json.loads(args.probe.read_text())
    cloud = json.loads(args.cloud.read_text())
    epoch = report.get("session_epoch") or report.get("environment", {}).get("session_epoch")
    if not epoch:
        raise ValueError("run report has no session epoch")
    frame_id = cloud.get("frame_id", "")
    if frame_id != f"odom_{epoch}":
        raise ValueError("cloud frame does not match the run epoch")
    stamp_ns = int(cloud["stamp_ns"])
    samples = [sample for sample in probe.get("map_samples", [])
               if int(sample.get("stamp_ns", -1)) == stamp_ns
               and sample.get("frame_id") == frame_id]
    if not samples:
        raise ValueError("cloud stamp/frame has no matching live map sample")
    sample = samples[-1]
    points = cloud.get("points")
    if not isinstance(points, list) or len(points) != int(cloud["width"]) * int(cloud["height"]):
        raise ValueError("cloud dimensions do not match point data")
    if len(points) != int(sample["points"]):
        raise ValueError("captured cloud and live sample point counts differ")
    if any(len(point) != 3 or not all(math.isfinite(float(v)) for v in point)
           for point in points):
        raise ValueError("cloud contains malformed or non-finite xyz points")

    map_id = map_id_at(args.mapping_log, epoch, float(sample["wall_epoch_s"]))
    map_status = cloud.get("map_status")
    if map_status is not None:
        if (map_status.get("epoch") != epoch
                or map_status.get("map_id") != map_id
                or map_status.get("header_frame_id") != frame_id
                or int(map_status.get("last_occupancy_stamp_ns", -1)) != stamp_ns
                or int(map_status.get("occupied_point_count", -1)) != len(points)
                or not map_status.get("reset_acknowledged")
                or not map_status.get("input_ready")
                or not map_status.get("occupancy_cloud_received")):
            raise ValueError("MapStatus sample does not describe this ready same-epoch cloud")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    pcd_path = args.output_dir / "occupied_snapshot.pcd"
    with pcd_path.open("w") as stream:
        stream.write("VERSION .7\nFIELDS x y z\nSIZE 4 4 4\nTYPE F F F\n")
        stream.write("COUNT 1 1 1\nWIDTH %d\nHEIGHT 1\n" % len(points))
        stream.write("VIEWPOINT 0 0 0 1 0 0 0\nPOINTS %d\nDATA ascii\n" % len(points))
        for point in points:
            stream.write("%.9g %.9g %.9g\n" % tuple(float(v) for v in point))

    recovered = read_pcd(pcd_path)
    # PointCloud2 coordinates are float32; round-trip at that representation.
    import struct
    float32 = lambda value: struct.unpack("f", struct.pack("f", value))[0]
    if [[float32(v) for v in point] for point in recovered] != [
            [float32(float(v)) for v in point] for point in points]:
        raise ValueError("PCD readback changed occupied point coordinates")

    metadata = {
        "schema": "occupied-map-snapshot/v1",
        "run_id": report.get("run_id"),
        "epoch": epoch,
        "map_id": map_id,
        "frame_id": frame_id,
        "source_stamp_ns": stamp_ns,
        "point_count": len(points),
        "classification": "occupied points only; free and unknown voxels are not exported",
        "snapshot_scope": "one live plan_env occupancy sample; no cross-epoch stitching",
        "live_sample": {
            "wall_epoch_s": sample["wall_epoch_s"],
            "wall_elapsed_s": sample["wall_elapsed_s"],
            "clock_stamp_ns_at_receipt": sample.get("clock_stamp_ns_at_receipt"),
            "point_count_matches_cloud": True,
        },
        "map_status_observation": map_status,
        "calibration_sha256": sha256(args.camera_model),
        "input_config_sha256": sha256(args.input_config),
        "source": {
            "cloud_json": str(args.cloud),
            "cloud_json_sha256": sha256(args.cloud),
            "mapping_log": str(args.mapping_log),
            "mapping_log_sha256": sha256(args.mapping_log),
            "probe_json": str(args.probe),
            "probe_json_sha256": sha256(args.probe),
            "run_report": str(args.run_report),
            "run_report_sha256": sha256(args.run_report),
        },
        "occupied_snapshot": {
            "file": pcd_path.name,
            "sha256": sha256(pcd_path),
            "readback_point_count": len(recovered),
            "float32_coordinates_roundtrip_exact": True,
        },
        "qualification": "archive/readback evidence only; not map coverage, free-space, clearance, or planning acceptance",
    }
    metadata_path = args.output_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-report", type=Path, required=True)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--cloud", type=Path, required=True)
    parser.add_argument("--mapping-log", type=Path, required=True)
    parser.add_argument("--input-config", type=Path, required=True)
    parser.add_argument("--camera-model", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args), indent=2))


if __name__ == "__main__":
    main()
