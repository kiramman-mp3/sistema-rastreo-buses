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
