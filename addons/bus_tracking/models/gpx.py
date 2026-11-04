"""Reading a GPX file: the line of a route and, optionally, its stops.

A GPX file comes from someone's phone or a mapping site, so it is untrusted input: entities are not
expanded and nothing is fetched from the network (no billion-laughs, no external entities)."""
from lxml import etree

MAX_BYTES = 5 * 1024 * 1024


class GpxError(ValueError):
    """The file cannot be used; the message says why, in English (the caller translates the wording)."""

    def __init__(self, code, **values):
        super().__init__(code)
        self.code = code
        self.values = values


def _local(tag):
    return tag.rsplit('}', 1)[-1] if isinstance(tag, str) else ''


def _point(node):
    try:
        lat, lon = float(node.get('lat')), float(node.get('lon'))
    except (TypeError, ValueError):
        return None
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0) or lat != lat or lon != lon:
        return None
    return [lat, lon]


def parse_gpx(data):
    """(line, waypoints): the line is a list of [lat, lon] (the longest track, else the longest route);
    waypoints is a list of (name, lat, lon). Raises GpxError."""
    if len(data) > MAX_BYTES:
        raise GpxError('too_big')
    parser = etree.XMLParser(resolve_entities=False, no_network=True, load_dtd=False, dtd_validation=False,
                             huge_tree=False, remove_comments=True, remove_pis=True)
    try:
        root = etree.fromstring(data, parser)
    except etree.XMLSyntaxError:
        raise GpxError('not_xml')
    if _local(root.tag) != 'gpx':
        raise GpxError('not_gpx')

    tracks, routes, waypoints = [], [], []
    for node in root:
        kind = _local(node.tag)
        if kind == 'trk':
            tracks.append([p for p in (_point(n) for n in node.iter() if _local(n.tag) == 'trkpt') if p])
        elif kind == 'rte':
            routes.append([p for p in (_point(n) for n in node if _local(n.tag) == 'rtept') if p])
        elif kind == 'wpt':
            point = _point(node)
            if point:
                name = next((c.text.strip() for c in node if _local(c.tag) == 'name' and c.text), '')
                waypoints.append((name, point[0], point[1]))
    candidates = [line for line in tracks if len(line) > 1] or [line for line in routes if len(line) > 1]
    if not candidates:
        raise GpxError('no_line')
    return max(candidates, key=len), waypoints
