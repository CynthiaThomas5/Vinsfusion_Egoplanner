"""Read-only run/goal/epoch/map/runtime identity binding for N10 observers."""
import hashlib
import json
from pathlib import Path


def _read_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError, TypeError):
        return {}


def _first_text(*values):
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def read_run_identity(run_dir, *, goal_id=None, epoch=None, map_id=None,
                      frame_id=None):
    """Resolve a single run identity and report missing or conflicting inputs.

    This is evidence metadata only. It deliberately never raises for missing
    runtime files: the observer can continue, while the offline evaluator marks
    an incomplete identity as INSUFFICIENT.
    """
    run = Path(run_dir).resolve()
    manifests = [
        _read_json(run / "n10-run-manifest.json"),
        _read_json(run / "n10-cancel-run-manifest.json"),
        _read_json(run / "n09-run-manifest.json"),
        _read_json(run / "n10-capture-launch-manifest.json"),
    ]
    manifest = next((row for row in manifests if row), {})
    contract = _read_json(run / "runtime-contract.json")
    flight = _read_json(run / "flight.json")
    stack = run.parent / f"{run.name}-stack"
    session = _read_json(stack / "session" / "session.json")
    query = _read_json(run / "n10-map-point-queries.json")
    snapshot = _read_json(run / "n10-map-snapshot" / "metadata.json")
    obstacle = _read_json(run / "n10-live-obstacle-observation.json")

    runtime_sha = _first_text(contract.get("sha256"))
    declared_runtime_sha = _first_text(manifest.get("runtime_contract_sha256"))
    resolved_goal = _first_text(goal_id, flight.get("goal_id"))
    resolved_epoch = _first_text(
        epoch, session.get("epoch"), flight.get("localization_epoch"),
        (query.get("identity") or {}).get("epoch"), snapshot.get("epoch"),
        obstacle.get("epoch"),
    )
    resolved_map = _first_text(
        map_id, (query.get("identity") or {}).get("map_id"),
        snapshot.get("map_id"), obstacle.get("map_id_at_goal"),
    )
    resolved_frame = _first_text(
        frame_id, (query.get("identity") or {}).get("frame_id"),
        snapshot.get("frame_id"),
        f"odom_{resolved_epoch}" if resolved_epoch else "",
    )
    run_id = _first_text(manifest.get("run_id"), run.name)
    conflicts = []
    if manifest and manifest.get("run_id") and manifest["run_id"] != run.name:
        conflicts.append("run_manifest_directory_mismatch")
    if runtime_sha and declared_runtime_sha and runtime_sha != declared_runtime_sha:
        conflicts.append("runtime_contract_manifest_mismatch")
    if resolved_epoch and resolved_map and not resolved_map.startswith(resolved_epoch + "-"):
        conflicts.append("map_id_epoch_mismatch")
    if resolved_epoch and resolved_frame and resolved_frame != f"odom_{resolved_epoch}":
        conflicts.append("frame_epoch_mismatch")
    missing = [name for name, value in (
        ("run_id", run_id), ("runtime_contract_sha256", runtime_sha),
        ("goal_id", resolved_goal), ("epoch", resolved_epoch),
        ("map_id", resolved_map),
    ) if not value]
    if not declared_runtime_sha:
        conflicts.append("runtime_contract_sha256_not_declared_by_run_manifest")
    return {
        "schema": "n10-run-identity/v1",
        "run_id": run_id,
        "runtime_contract_sha256": runtime_sha,
        "declared_runtime_contract_sha256": declared_runtime_sha,
        "goal_id": resolved_goal,
        "epoch": resolved_epoch,
        "map_id": resolved_map,
        "frame_id": resolved_frame,
        "complete": not missing and not conflicts,
        "missing_fields": missing,
        "conflicts": conflicts,
        "source_files": {
            "run_manifest": next((name for name, row in (
                ("n10-run-manifest.json", manifests[0]),
                ("n10-cancel-run-manifest.json", manifests[1]),
                ("n09-run-manifest.json", manifests[2]),
                ("n10-capture-launch-manifest.json", manifests[3])) if row), None),
            "runtime_contract": "runtime-contract.json" if contract else None,
            "session_manifest": (f"../{run.name}-stack/session/session.json"
                                 if session else None),
            "flight_record": "flight.json" if flight else None,
        },
    }


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
