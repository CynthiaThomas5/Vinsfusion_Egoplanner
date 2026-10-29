"""Bounded B-spline evaluation for display only; no planning or control."""
import math


def sample_bspline(points, knots, degree, period, max_samples, max_points):
    """Evaluate the received knot/control-point representation with de Boor.

    Includes both endpoints. This draws the actual curve rather than the
    control polygon; it never modifies or republishes the received trajectory.
    """
    count = len(points)
    if (not 1 <= degree <= 5 or not degree + 1 <= count <= max_points
            or len(knots) != count + degree + 1 or max_samples < 2
            or not math.isfinite(period) or period <= 0):
        raise ValueError('invalid spline shape or display limits')
    if (any(len(p) != 3 or not all(math.isfinite(v) for v in p) for p in points)
            or not all(math.isfinite(v) for v in knots)
            or any(a > b for a, b in zip(knots, knots[1:]))):
        raise ValueError('nonfinite spline or unordered knots')
    begin, end = knots[degree], knots[count]
    duration = end - begin
    if duration <= 0 or not math.isfinite(duration):
        raise ValueError('invalid spline duration')
    segments = min(max_samples - 1, max(1, math.ceil(duration / period)))
    result = []
    for index in range(segments + 1):
        u = begin + duration * index / segments
        span = degree
        while span < count - 1 and knots[span + 1] < u:
            span += 1
        work = [list(points[span - degree + j]) for j in range(degree + 1)]
        for level in range(1, degree + 1):
            for j in range(degree, level - 1, -1):
                left = span - degree + j
                width = knots[left + degree - level + 1] - knots[left]
                weight = (u - knots[left]) / width if width > 0 else 0.0
                work[j] = [(1 - weight) * a + weight * b
                           for a, b in zip(work[j - 1], work[j])]
        point = tuple(work[degree])
        if not all(math.isfinite(v) for v in point):
            raise ValueError('nonfinite sampled point')
        result.append(point)
    return result
