import { gpsHealth } from './health';

const now = 1_000_000;

describe('gps health', () => {
  test('without permission the GPS is off, whatever the server says', () => {
    expect(gpsHealth({ permission: 'denied', lastSampleAt: now, lastSentAt: now, queued: 0, now })).toBe('off');
  });

  test('no fix for a minute means waiting for the GPS', () => {
    expect(gpsHealth({ permission: 'granted', lastSampleAt: null, lastSentAt: null, queued: 0, now })).toBe('waiting');
    expect(gpsHealth({ permission: 'granted', lastSampleAt: now - 61_000, lastSentAt: now, queued: 0, now })).toBe('waiting');
  });

  test('fixes that cannot be sent are being saved', () => {
    expect(gpsHealth({ permission: 'granted', lastSampleAt: now - 5_000, lastSentAt: now - 120_000, queued: 12, now })).toBe('saving');
  });

  test('fresh fixes that go out are sending', () => {
    expect(gpsHealth({ permission: 'granted', lastSampleAt: now - 5_000, lastSentAt: now - 5_000, queued: 0, now })).toBe('sending');
  });
});
