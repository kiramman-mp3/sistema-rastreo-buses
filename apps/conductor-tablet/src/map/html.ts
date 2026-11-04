import type { RouteMap } from '../api/types';
import { LEAFLET_CSS, LEAFLET_JS } from './leafletAssets';

export type MapBus = { lat: number; lon: number } | null;

/** What the page writes on the map, already translated. */
export type MapLabels = { stop: string; you: string; recenter: string };

/** Street level: the driver needs to see the next turns, not the whole line. */
export const FOLLOW_ZOOM = 17;

const DEFAULT_LABELS: MapLabels = { stop: 'Parada', you: 'Tu ubicación actual', recenter: 'Seguir mi ubicación' };

function safeJson(value: unknown): string {
  return JSON.stringify(value).replace(/</g, '\\u003c');
}

/**
 * The script that moves the bus and the next stop on a page that is already open. The page itself is
 * built once per route: rebuilding it for every GPS fix reloaded the map and reset the zoom.
 */
export function mapUpdateScript(bus: MapBus, nextStopId: number | null): string {
  return `window.busMap && window.busMap.update(${safeJson({ bus, nextStopId })}); true;`;
}

export function buildMapHtml(
  route: RouteMap,
  bus: MapBus,
  nextStopId: number | null,
  labels: MapLabels = DEFAULT_LABELS,
): string {
  const payload = safeJson({ route, bus, nextStopId, labels, zoom: FOLLOW_ZOOM });
  return `<!DOCTYPE html>
<html><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no"/>
<style>
${LEAFLET_CSS}
  html, body, #map { height: 100%; width: 100%; margin: 0; padding: 0; background: #E3E8E6; }
  /* Big zoom buttons: the tablet is used with a finger, on a moving bus. */
  .leaflet-touch .leaflet-bar a { width: 44px; height: 44px; line-height: 44px; font-size: 22px; }
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
  /* Shown only after the driver moved the map away from the bus. */
  #recenter {
    position: absolute;
    left: 10px;
    bottom: 10px;
    z-index: 1000;
    min-height: 48px;
    padding: 0 18px;
    border: 3px solid #172025;
    border-radius: 10px;
    background: #FFC62B;
    color: #172025;
    font: 700 16px/1 sans-serif;
  }
  #recenter[hidden] { display: none; }
</style>
<script>
${LEAFLET_JS}
</script>
</head><body>
<div id="map"></div>
<button id="recenter" type="button" hidden></button>
<script>
(function() {
  const data = ${payload};
  const labels = data.labels;
  // touchZoom/scrollWheelZoom 'center': pinching keeps the bus in the middle instead of drifting away.
  const map = L.map('map', { zoomControl: true, touchZoom: 'center', scrollWheelZoom: 'center' });
  map.attributionControl.setPrefix(false);
  L.tileLayer(data.route.tile_url || 'https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png?key=cb1_500h_1_2faaa5c6c3a1e1bb863b25cb', {
    maxZoom: 19,
    subdomains: 'abcd',
    attribution: '&copy; OpenStreetMap &copy; CARTO'
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

  function stopIcon(isNext) {
    return L.divIcon({
      className: '',
      html: '<div class="stop-marker-badge ' + (isNext ? 'stop-marker-next' : '') + '" style="--c:' + routeColor + '"></div>',
      iconSize: isNext ? [32, 32] : [22, 22],
      iconAnchor: isNext ? [16, 16] : [11, 11]
    });
  }

  // Draw stop markers
  const stopMarkers = {};
  stops.forEach(function (stop, idx) {
    const marker = L.marker([stop.lat, stop.lon], { icon: stopIcon(stop.id === data.nextStopId) }).addTo(map);
    const title = document.createElement('b');
    title.textContent = labels.stop + ' ' + (idx + 1) + ': ';
    const box = document.createElement('div');
    box.appendChild(title);
    box.appendChild(document.createTextNode(stop.name));
    marker.bindPopup(box);
    stopMarkers[stop.id] = marker;
    bounds.push([stop.lat, stop.lon]);
  });

  const busIcon = L.divIcon({
    className: '',
    html: '<div class="bus-marker-dot"><i></i></div>',
    iconSize: [36, 36],
    iconAnchor: [18, 18]
  });
  let busMarker = null;
  let nextStopId = data.nextStopId;
  // The map follows the bus until the driver drags it; the zoom the driver chose is never touched.
  let following = true;
  const button = document.getElementById('recenter');
  button.textContent = labels.recenter;

  function setFollowing(on) {
    following = on;
    button.hidden = on || !busMarker;
  }

  function update(state) {
    if (state.nextStopId !== nextStopId) {
      if (stopMarkers[nextStopId]) { stopMarkers[nextStopId].setIcon(stopIcon(false)); }
      if (stopMarkers[state.nextStopId]) { stopMarkers[state.nextStopId].setIcon(stopIcon(true)); }
      nextStopId = state.nextStopId;
    }
    if (!state.bus) { return; }
    const here = [state.bus.lat, state.bus.lon];
    if (!busMarker) {
      busMarker = L.marker(here, { icon: busIcon, zIndexOffset: 1000 }).addTo(map).bindPopup('<b>' + labels.you + '</b>');
      // First fix: close in on the bus instead of showing the whole line.
      map.setView(here, data.zoom, { animate: false });
      setFollowing(true);
      return;
    }
    busMarker.setLatLng(here);
    if (following) { map.panTo(here, { animate: true, duration: 1, easeLinearity: 1 }); }
  }

  map.on('dragstart', function () { setFollowing(false); });
  button.addEventListener('click', function () {
    setFollowing(true);
    if (busMarker) { map.setView(busMarker.getLatLng(), Math.max(map.getZoom(), data.zoom - 1)); }
  });

  window.busMap = { update: update };

  if (data.bus) {
    update({ bus: data.bus, nextStopId: data.nextStopId });
  } else if (bounds.length > 1) {
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
