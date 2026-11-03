import { StyleSheet, View } from 'react-native';

import { LANGS, messages } from '../i18n';
import { persistLang, useLang } from '../i18n/LangProvider';
import { Press, Txt } from './cabin';
import { useTheme } from './ThemeProvider';

export function LangSwitch() {
  const lang = useLang();
  const { palette } = useTheme();
  return (
    <View style={styles.row} accessibilityRole="radiogroup">
      {LANGS.map((code) => {
        const on = lang === code;
        return (
          <Press
            key={code}
            onPress={() => persistLang(code)}
            accessibilityRole="radio"
            accessibilityState={{ checked: on }}
            style={[styles.chip, { backgroundColor: on ? palette.panel : 'transparent', borderColor: on ? palette.ink : palette.panel }]}
          >
            <Txt bold={on} size="small">
              {messages[code].lang_name}
            </Txt>
          </Press>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: {
    minHeight: 48,
    paddingHorizontal: 14,
    borderRadius: 8,
    borderWidth: 2,
    justifyContent: 'center',
  },
});
