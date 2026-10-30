import { Pressable, StyleSheet, Text, View } from 'react-native';

import { LANGS, messages } from '../i18n';
import { persistLang, useLang } from '../i18n/LangProvider';
import { colors, type } from './theme';

export function LangSwitch() {
  const lang = useLang();
  return (
    <View style={styles.row}>
      {LANGS.map((code) => (
        <Pressable
          key={code}
          onPress={() => persistLang(code)}
          style={[styles.chip, lang === code && styles.on]}
        >
          <Text style={styles.label}>{messages[code].lang_name}</Text>
        </Pressable>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 8 },
  chip: {
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: colors.line,
    backgroundColor: '#fff',
  },
  on: { borderColor: colors.route, backgroundColor: '#E7F2EE' },
  label: { fontSize: type.body - 4, color: colors.ink },
});
