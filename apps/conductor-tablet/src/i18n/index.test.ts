import { alertLabel, getLang, LANGS, messages, setLang, t, tp } from './index';

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

  test('plurals pick the singular for exactly one and the plural otherwise', () => {
    setLang('es');
    expect(tp('moreNotice', 1)).toBe('1 aviso más');
    expect(tp('moreNotice', 0)).toBe('0 avisos más');
    expect(tp('moreNotice', 3)).toBe('3 avisos más');
    setLang('en');
    expect(tp('moreNotice', 1)).toBe('1 more notice');
    expect(tp('moreNotice', 2)).toBe('2 more notices');
    setLang('qu');
    expect(tp('moreNotice', 2)).toBe('2 avisos más');
  });

  test('every singular form has its plural form in every language', () => {
    const singular = Object.keys(messages.es).filter((key) => key.endsWith('_one'));
    for (const code of LANGS) {
      for (const key of singular) {
        expect(Object.keys(messages[code])).toContain(key.replace(/_one$/, '_other'));
      }
    }
  });
});
