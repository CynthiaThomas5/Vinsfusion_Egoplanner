"""Validate target-query identity and classification; age is observational."""


def query_rejection(response, request, collision_policy="known_free"):
    if collision_policy not in ("known_free", "official_ego"):
        return "map_query_policy_invalid"
    unobserved = (collision_policy == "official_ego"
                  and request.radius_m == 0.0
                  and response.reason == "unobserved_not_occupied")
    if not response.accepted or not response.free or (response.reason != 'free' and not unobserved):
        return 'map_query_' + (response.reason or 'rejected')
    if (response.epoch != request.expected_epoch
            or response.map_id != request.expected_map_id
            or response.header.frame_id != request.frame_id):
        return 'map_query_identity_mismatch'
    if (response.radius_m != request.radius_m
            or any(getattr(response.center, axis) != getattr(request.center, axis)
                   for axis in ('x', 'y', 'z'))):
        return 'map_query_geometry_mismatch'
    if unobserved:
        if response.unknown_count != 1 or response.occupied_count or response.free_count:
            return 'map_query_inconsistent_counts'
    elif response.unknown_count or response.occupied_count or response.free_count <= 0:
        return 'map_query_inconsistent_counts'
    return ''
