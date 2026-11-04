import { buildMapHtml, FOLLOW_ZOOM, mapUpdateScript } from './html';
import type { RouteMap } from '../api/types';

describe('buildMapHtml', () => {
  const sampleRoute: RouteMap = {
    id: 1,
    code: 'TRONCAL',
    name: 'Ruta Troncal',
    color: '#0D684D',
    stops: [
      { id: 10, name: 'Parada 1', lat: -1.24, lon: -78.62, sequence: 1, radius: 50 },
      { id: 11, name: 'Parada 2', lat: -1.25, lon: -78.63, sequence: 2, radius: 50 },
    ],
    lines: [
      {
        name: 'Ida',
        km: 4.5,
        points: [
          [-1.24, -78.62],
          [-1.25, -78.63],
        ],
      },
    ],
  };

  it('embeds local leaflet bundle and does not reference unpkg.com', () => {
    const html = buildMapHtml(sampleRoute, { lat: -1.245, lon: -78.625 }, 11);
    expect(html).not.toContain('unpkg.com');
    expect(html).toContain('Leaflet 1.9.4');
    expect(html).toContain('<div id="map"></div>');
    expect(html).toContain('Ruta Troncal');
    expect(html).toContain('Parada 1');
    expect(html).toContain('"bus":{"lat":-1.245,"lon":-78.625}');
    expect(html).toContain('"nextStopId":11');
  });

  it('handles null bus and null nextStopId without errors', () => {
    const html = buildMapHtml(sampleRoute, null, null);
    expect(html).toContain('Ruta Troncal');
    expect(html).toContain('"bus":null');
    expect(html).toContain('"nextStopId":null');
  });

  it('opens close to the bus and follows it, never resetting the zoom the driver chose', () => {
    const html = buildMapHtml(sampleRoute, { lat: -1.245, lon: -78.625 }, 11);
    expect(FOLLOW_ZOOM).toBeGreaterThanOrEqual(16);
    expect(html).toContain(`"zoom":${FOLLOW_ZOOM}`);
    expect(html).toContain('window.busMap = { update: update }');
    // follow with panTo (keeps the zoom), and stop following when the driver drags the map
    expect(html).toContain('map.panTo(here');
    expect(html).toContain("map.on('dragstart'");
  });

  it('writes the labels it is given, not fixed Spanish text', () => {
    const html = buildMapHtml(sampleRoute, null, null, { stop: 'Stop', you: 'Your current location', recenter: 'Follow my location' });
    expect(html).toContain('"labels":{"stop":"Stop","you":"Your current location","recenter":"Follow my location"}');
    expect(html).not.toContain('Tu ubicación actual');
  });
});

describe('mapUpdateScript', () => {
  it('moves the bus and the next stop on the open page', () => {
    expect(mapUpdateScript({ lat: -1.2, lon: -78.6 }, 4)).toBe(
      'window.busMap && window.busMap.update({"bus":{"lat":-1.2,"lon":-78.6},"nextStopId":4}); true;',
    );
    expect(mapUpdateScript(null, null)).toContain('"bus":null');
  });
});
