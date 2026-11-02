import { buildMapHtml } from './html';
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
});
