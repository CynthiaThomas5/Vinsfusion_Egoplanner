"""Validate a fresh read-only target query; this does not certify a path."""
import math


def stamp_seconds(stamp):
    return stamp.sec + stamp.nanosec / 1e9


def query_rejection(response, request, now_s, max_age_s):
    if not response.accepted or not response.free or response.reason != 'free':
        return 'map_query_' + (response.reason or 'rejected')
    if (response.epoch != request.expected_epoch
            or response.map_id != request.expected_map_id
            or response.header.frame_id != request.frame_id):
        return 'map_query_identity_mismatch'
    if (response.radius_m != request.radius_m
            or any(getattr(response.center, axis) != getattr(request.center, axis)
                   for axis in ('x', 'y', 'z'))):
        return 'map_query_geometry_mismatch'
    if response.unknown_count or response.occupied_count or response.free_count <= 0:
        return 'map_query_inconsistent_counts'
    for stamp in (response.header.stamp, response.last_depth_source_stamp,
                  response.last_fusion_stamp):
        source_s = stamp_seconds(stamp)
        age = now_s - source_s
        if source_s <= 0 or not math.isfinite(age) or not 0 <= age <= max_age_s:
            return 'map_query_stale'
    return ''
