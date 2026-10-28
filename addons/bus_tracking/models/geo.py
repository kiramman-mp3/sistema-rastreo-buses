"""Distances along a road path: where a bus is on it, and how far it is from it."""
import math

METERS_PER_DEGREE = 111320.0


class PathMeasure:
    """A polyline of [lat, lon] points that can place a position on itself.

    Uses a flat projection around the path's first point: exact enough (centimetres) over the
    tens of kilometres of a bus line."""

    def __init__(self, points):
        self.points = points
        lat0 = points[0][0] if points else 0.0
        self._kx = METERS_PER_DEGREE * math.cos(math.radians(lat0))
        self._xy = [(p[1] * self._kx, p[0] * METERS_PER_DEGREE) for p in points]
        self.cumulative = [0.0]
        for a, b in zip(self._xy, self._xy[1:]):
            self.cumulative.append(self.cumulative[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))

    @property
    def length(self):
        return self.cumulative[-1]

    def locate(self, lat, lon):
        """(metres from the start along the path, metres away from the path) of the closest point."""
        px, py = lon * self._kx, lat * METERS_PER_DEGREE
        best_off, best_along = None, 0.0
        for i in range(len(self._xy) - 1):
            ax, ay = self._xy[i]
            bx, by = self._xy[i + 1]
            dx, dy = bx - ax, by - ay
            span = dx * dx + dy * dy
            t = 0.0 if span == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / span))
            off = math.hypot(px - ax - t * dx, py - ay - t * dy)
            if best_off is None or off < best_off:
                best_off = off
                best_along = self.cumulative[i] + t * math.sqrt(span)
        return best_along, (best_off if best_off is not None else math.inf)


def thin(points, min_gap_m):
    """Drop points closer than min_gap_m to the previous kept one (a parked bus draws a cloud of them)."""
    kept = []
    for lat, lon in points:
        if not kept:
            kept.append([lat, lon])
            continue
        dx = (lon - kept[-1][1]) * METERS_PER_DEGREE * math.cos(math.radians(lat))
        dy = (lat - kept[-1][0]) * METERS_PER_DEGREE
        if math.hypot(dx, dy) >= min_gap_m:
            kept.append([lat, lon])
    return kept


def simplify(points, tolerance_m):
    """Douglas-Peucker: the fewest points that stay within tolerance_m of the original line."""
    if len(points) < 3:
        return [list(p) for p in points]
    lat0 = points[0][0]
    kx = METERS_PER_DEGREE * math.cos(math.radians(lat0))
    xy = [(p[1] * kx, p[0] * METERS_PER_DEGREE) for p in points]
    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        ax, ay = xy[first]
        bx, by = xy[last]
        dx, dy = bx - ax, by - ay
        span = dx * dx + dy * dy
        far, far_dist = None, tolerance_m
        for i in range(first + 1, last):
            px, py = xy[i]
            t = 0.0 if span == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / span))
            dist = math.hypot(px - ax - t * dx, py - ay - t * dy)
            if dist > far_dist:
                far, far_dist = i, dist
        if far is not None:
            keep[far] = True
            stack.extend([(first, far), (far, last)])
    return [list(p) for p, flag in zip(points, keep) if flag]
