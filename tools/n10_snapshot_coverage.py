"""Observer-only source-time coverage checks for N10 occupancy snapshots."""


def latest_roi_cloud_watermark(cloud_rows):
    """Return the newest recorded positive-ROI cloud stamp, if one exists."""
    candidates = []
    for index, row in enumerate(cloud_rows):
        try:
            if int(row.get("obstacle_roi_point_count", 0)) <= 0:
                continue
            stamp_ns = int(row["header_stamp_ns"])
            if stamp_ns < 0:
                continue
        except (KeyError, TypeError, ValueError):
            continue
        candidates.append((stamp_ns, index, row))
    if not candidates:
        return None
    stamp_ns, index, row = max(candidates, key=lambda item: (item[0], item[1]))
    return {
        "header_stamp_ns": stamp_ns,
        "receipt_sim_ns": row.get("receipt_sim_ns"),
        "frame_id": str(row.get("frame_id", "")),
        "obstacle_roi_point_count": int(row["obstacle_roi_point_count"]),
        "row_index": index,
    }


def assess_snapshot_source_coverage(snapshot_source_stamp_ns, watermark,
                                    snapshot_frame_id=None, *,
                                    attempt_count=1, max_attempts=5):
    """Classify whether a read-only map snapshot covers the recorded ROI cloud.

    A lagging source timestamp may be retried by the observer. Exhaustion is
    explicitly insufficient; it must never influence flight control.
    """
    if watermark is None:
        return {
            "status": "no_roi_cloud_observed",
            "covered": None,
            "should_retry": False,
            "watermark_stamp_ns": None,
            "snapshot_source_stamp_ns": snapshot_source_stamp_ns,
        }
    watermark_ns = int(watermark["header_stamp_ns"])
    watermark_frame = str(watermark.get("frame_id", ""))
    if (snapshot_frame_id and watermark_frame
            and str(snapshot_frame_id) != watermark_frame):
        return {
            "status": "frame_mismatch",
            "covered": False,
            "should_retry": False,
            "watermark_stamp_ns": watermark_ns,
            "watermark_frame_id": watermark_frame,
            "snapshot_frame_id": str(snapshot_frame_id),
            "snapshot_source_stamp_ns": snapshot_source_stamp_ns,
        }
    try:
        source_ns = int(snapshot_source_stamp_ns)
    except (TypeError, ValueError):
        source_ns = None
    if source_ns is not None and source_ns >= watermark_ns:
        return {
            "status": "covered",
            "covered": True,
            "should_retry": False,
            "watermark_stamp_ns": watermark_ns,
            "watermark_frame_id": watermark_frame,
            "snapshot_source_stamp_ns": source_ns,
            "source_minus_watermark_ns": source_ns - watermark_ns,
        }
    can_retry = int(attempt_count) < int(max_attempts)
    return {
        "status": "waiting_for_fusion" if can_retry else "insufficient_after_retry_limit",
        "covered": False,
        "should_retry": can_retry,
        "watermark_stamp_ns": watermark_ns,
        "watermark_frame_id": watermark_frame,
        "snapshot_source_stamp_ns": source_ns,
        "source_minus_watermark_ns": (
            source_ns - watermark_ns if source_ns is not None else None),
        "attempt_count": int(attempt_count),
        "max_attempts": int(max_attempts),
    }
