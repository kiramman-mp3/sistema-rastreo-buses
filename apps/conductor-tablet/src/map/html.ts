import type { RouteMap } from '../api/types';
import { LEAFLET_CSS, LEAFLET_JS } from './leafletAssets';

export type MapBus = { lat: number; lon: number } | null;

export function buildMapHtml(route: RouteMap, bus: MapBus, nextStopId: number | null): string {
  const payload = JSON.stringify({ route, bus, nextStopId }).replace(/</g, '\\u003c');
  return `<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"/>
<style>
${LEAFLET_CSS}
  html, body, #map { height: 100%; width: 100%; margin: 0; padding: 0; background: #E3E8E6; }
  /* Stops: a white disc ringed in the route colour; the next one in the signal yellow. */
  .stop-marker-badge {
    width: 22px;
    height: 22px;
    box-sizing: border-box;
    border-radius: 50%;
    border: 5px solid var(--c, #7A1A22);
    background: #FFFFFF;
  }
  .stop-marker-next {
    width: 32px;
    height: 32px;
    border-color: #172025;
    background: #FFC62B;
  }
  /* The bus: dark disc, white ring, a front view drawn in CSS. */
  .bus-marker-dot {
    width: 36px;
    height: 36px;
    box-sizing: border-box;
    border-radius: 50%;
    border: 4px solid #FFFFFF;
    background: #172025;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .bus-marker-dot i {
    width: 14px;
    height: 14px;
    border-radius: 3px;
    background: #FFFFFF;
    box-shadow: inset 0 -5px 0 #8A979B;
  }
</style>
<script>
${LEAFLET_JS}
</script>
</head><body>
<div id="map"></div>
<script>
(function() {
  const data = ${payload};
  const map = L.map('map', { zoomControl: true, attributionControl: false });
  L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png?key=cb1_500h_1_2faaa5c6c3a1e1bb863b25cb', {
    maxZoom: 19,
    subdomains: 'abcd'
  }).addTo(map);

  const routeColor = data.route.color || '#7A1A22';
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
      html: '<div class="stop-marker-badge ' + (isNext ? 'stop-marker-next' : '') + '" style="--c:' + routeColor + '"></div>',
      iconSize: isNext ? [32, 32] : [22, 22],
      iconAnchor: isNext ? [16, 16] : [11, 11]
    });
    L.marker([stop.lat, stop.lon], { icon: icon }).addTo(map)
      .bindPopup('<b>Parada ' + num + ':</b> ' + stop.name);
    bounds.push([stop.lat, stop.lon]);
  });

  // Draw bus fix
  if (data.bus) {
    const busIcon = L.divIcon({
      className: '',
      html: '<div class="bus-marker-dot"><i></i></div>',
      iconSize: [36, 36],
      iconAnchor: [18, 18]
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
