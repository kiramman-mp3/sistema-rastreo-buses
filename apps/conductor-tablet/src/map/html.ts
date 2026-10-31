import type { RouteMap } from '../api/types';

export type MapBus = { lat: number; lon: number } | null;

export function buildMapHtml(route: RouteMap, bus: MapBus, nextStopId: number | null): string {
  const payload = JSON.stringify({ route, bus, nextStopId }).replace(/</g, '\\u003c');
  return `<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"/>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  html, body, #map { height: 100%; width: 100%; margin: 0; padding: 0; background: #e2e8f0; }
  .stop-marker-badge {
    background: #0D684D;
    color: #fff;
    font-weight: 700;
    font-size: 11px;
    border-radius: 50%;
    width: 22px;
    height: 22px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 2px solid #ffffff;
    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
  }
  .stop-marker-next {
    background: #DC2626;
    transform: scale(1.3);
    box-shadow: 0 0 10px rgba(220, 38, 38, 0.8);
    border: 2px solid #ffffff;
    z-index: 1000 !important;
  }
  .bus-marker-dot {
    background: #2563EB;
    border-radius: 50%;
    width: 26px;
    height: 26px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 3px solid #ffffff;
    box-shadow: 0 0 12px rgba(37, 99, 235, 0.9);
    color: #fff;
    font-size: 14px;
    z-index: 2000 !important;
  }
</style>
</head><body>
<div id="map"></div>
<script>
(function() {
  const data = ${payload};
  const map = L.map('map', { zoomControl: true, attributionControl: false });
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19
  }).addTo(map);

  const routeColor = data.route.color || '#0D684D';
  const bounds = [];
  let hasLines = false;

  (data.route.lines || []).forEach(function (line) {
    const latlngs = (line.points || []).map(function (p) { return [p[0], p[1]]; });
    if (latlngs.length) {
      hasLines = true;
      L.polyline(latlngs, { color: routeColor, weight: 6, opacity: 0.85 }).addTo(map);
      latlngs.forEach(function (p) { bounds.push(p); });
    }
  });

  const stops = (data.route.stops || []).sort(function(a, b) {
    return (a.sequence || 0) - (b.sequence || 0);
  });

  // If no recorded tracks exist, draw polyline directly connecting stops
  if (!hasLines && stops.length >= 2) {
    const stopCoords = stops.map(function(s) { return [s.lat, s.lon]; });
    L.polyline(stopCoords, { color: routeColor, weight: 5, dashArray: '8, 8', opacity: 0.85 }).addTo(map);
  }

  // Draw stop markers
  stops.forEach(function (stop, idx) {
    const isNext = stop.id === data.nextStopId;
    const num = idx + 1;
    const icon = L.divIcon({
      className: '',
      html: '<div class="stop-marker-badge ' + (isNext ? 'stop-marker-next' : '') + '">' + num + '</div>',
      iconSize: [22, 22],
      iconAnchor: [11, 11]
    });
    L.marker([stop.lat, stop.lon], { icon: icon }).addTo(map)
      .bindPopup('<b>Parada ' + num + ':</b> ' + stop.name);
    bounds.push([stop.lat, stop.lon]);
  });

  // Draw bus fix
  if (data.bus) {
    const busIcon = L.divIcon({
      className: '',
      html: '<div class="bus-marker-dot">🚌</div>',
      iconSize: [26, 26],
      iconAnchor: [13, 13]
    });
    L.marker([data.bus.lat, data.bus.lon], { icon: busIcon }).addTo(map)
      .bindPopup('<b>Tu ubicación actual</b>');
    bounds.push([data.bus.lat, data.bus.lon]);
  }

  if (bounds.length > 1) {
    map.fitBounds(bounds, { padding: [35, 35], maxZoom: 16 });
  } else if (bounds.length === 1) {
    map.setView(bounds[0], 15);
  } else {
    map.setView([-1.24, -78.62], 13);
  }

  // Force Leaflet tile refresh when container mounts
  setTimeout(function() { map.invalidateSize(); }, 250);
  setTimeout(function() { map.invalidateSize(); }, 800);
  window.addEventListener('resize', function() { map.invalidateSize(); });
})();
</script>
</body></html>`;
}
