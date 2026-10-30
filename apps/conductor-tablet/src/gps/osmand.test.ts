import { buildOsmAndUrl, locationToFix, MS_TO_KNOTS } from './osmand';

const fix = {
  lat: -1.24123,
  lon: -78.61987,
  timestampMs: 1_000_000_000_000,
  speedMs: 10,
  bearing: 90,
  altitude: 2600.4,
  accuracy: 8.2,
  batt: 81.6,
};

describe('OsmAnd URL', () => {
  test('converts m/s to knots and timestamp to seconds', () => {
    const url = new URL(buildOsmAndUrl('http://gps.example:5055', 'bus-7', fix));
    expect(url.searchParams.get('id')).toBe('bus-7');
    expect(url.searchParams.get('lat')).toBe('-1.241230');
    expect(url.searchParams.get('lon')).toBe('-78.619870');
    expect(url.searchParams.get('timestamp')).toBe('1000000000');
    expect(Number(url.searchParams.get('speed'))).toBeCloseTo(10 * MS_TO_KNOTS, 2);
    expect(url.searchParams.get('bearing')).toBe('90.0');
    expect(url.searchParams.get('altitude')).toBe('2600.4');
    expect(url.searchParams.get('accuracy')).toBe('8.2');
    expect(url.searchParams.get('batt')).toBe('82');
  });

  test('omits invalid speed and bearing', () => {
    const url = new URL(
      buildOsmAndUrl('https://gps.uta.edu.ec/osmand', 'x', {
        ...fix,
        speedMs: -1,
        bearing: -1,
        batt: null,
      }),
    );
    expect(url.searchParams.get('speed')).toBeNull();
    expect(url.searchParams.get('bearing')).toBeNull();
    expect(url.searchParams.get('batt')).toBeNull();
    expect(url.pathname).toBe('/osmand');
  });

  test('maps an Expo location into a fix', () => {
    const mapped = locationToFix(
      {
        timestamp: 50,
        coords: {
          latitude: 1,
          longitude: 2,
          altitude: null,
          accuracy: 3,
          heading: -1,
          speed: 0,
        },
      },
      40,
    );
    expect(mapped.bearing).toBeNull();
    expect(mapped.speedMs).toBe(0);
    expect(mapped.batt).toBe(40);
  });
});
