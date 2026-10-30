import { alertLabel, getLang, LANGS, messages, setLang, t } from './index';

describe('driver i18n', () => {
  afterEach(() => setLang('es'));

  test('every language has the same keys', () => {
    const keys = Object.keys(messages.es);
    for (const code of LANGS) {
      expect(Object.keys(messages[code]).sort()).toEqual(keys.sort());
    }
  });

  test('reuses portal strings for stops, other, and no-signal', () => {
    setLang('es');
    expect(t('stops')).toBe('Paradas');
    expect(t('kind_other')).toBe('Otro');
    expect(t('alert_offline')).toBe('sin señal');
    setLang('en');
    expect(t('stops')).toBe('Stops');
    expect(t('kind_other')).toBe('Other');
    expect(t('alert_offline')).toBe('no signal');
    expect(t('update_error')).toBe("We couldn't update. Retrying…");
    setLang('qu');
    expect(t('stops')).toBe('Sayana kuna');
    expect(t('lang_name')).toBe('Kichwa (borrador)');
    expect(t('alert_offline')).toBe('mana rikurin');
    expect(t('kind_other')).toBe('Otro');
  });

  test('alert kinds map in the active language', () => {
    setLang('en');
    expect(alertLabel('speeding')).toBe('Speeding');
    expect(getLang()).toBe('en');
  });
});
