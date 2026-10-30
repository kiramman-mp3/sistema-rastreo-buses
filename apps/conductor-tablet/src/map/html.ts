import type { RouteMap } from '../api/types';

export type MapBus = { lat: number; lon: number } | null;

export function buildMapHtml(route: RouteMap, bus: MapBus, nextStopId: number | null): string {
  const payload = JSON.stringify({ route, bus, nextStopId }).replace(/</g, '\\u003c');
  return `<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>html,body,#map{height:100%;margin:0;background:#e8e4da}</style>
</head><body>
<div id="map"></div>
<script>
const data = ${payload};
const map = L.map('map');
L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
  attribution: '&copy; OpenStreetMap'
}).addTo(map);
const color = data.route.color || '#3388ff';
const bounds = [];
(data.route.lines || []).forEach(function (line) {
  const latlngs = (line.points || []).map(function (p) { return [p[0], p[1]]; });
  if (latlngs.length) {
    L.polyline(latlngs, { color: color, weight: 5 }).addTo(map);
    latlngs.forEach(function (p) { bounds.push(p); });
  }
});
(data.route.stops || []).forEach(function (stop) {
  const marker = L.circleMarker([stop.lat, stop.lon], {
    radius: stop.id === data.nextStopId ? 10 : 6,
    color: stop.id === data.nextStopId ? '#B42318' : color,
    fillOpacity: 0.9
  }).addTo(map).bindPopup(stop.name);
  bounds.push([stop.lat, stop.lon]);
});
if (data.bus) {
  L.circleMarker([data.bus.lat, data.bus.lon], {
    radius: 11, color: '#B42318', fillColor: '#B42318', fillOpacity: 1
  }).addTo(map);
  bounds.push([data.bus.lat, data.bus.lon]);
}
if (bounds.length) map.fitBounds(bounds, { padding: [24, 24] });
else map.setView([-1.24, -78.62], 13);
</script>
</body></html>`;
}
