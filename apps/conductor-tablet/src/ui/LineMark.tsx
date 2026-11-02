import { StyleSheet, View } from 'react-native';

/** The Buses UTA mark drawn with views: a stretch of line with three stops, the middle one "you are here". */
export function LineMark({ scale = 1 }: { scale?: number }) {
  const s = (n: number) => n * scale;
  return (
    <View style={{ width: s(66), height: s(36), justifyContent: 'center' }} accessibilityElementsHidden>
      <View style={[styles.bar, { left: s(6), right: s(6), height: s(9) }]} />
      <View style={[styles.row]}>
        <View style={[styles.stop, { width: s(15), height: s(15), borderRadius: s(8), borderWidth: s(4) }]} />
        <View
          style={[
            styles.stop,
            styles.here,
            { width: s(20), height: s(20), borderRadius: s(10), borderWidth: s(4) },
          ]}
        />
        <View style={[styles.stop, { width: s(15), height: s(15), borderRadius: s(8), borderWidth: s(4) }]} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    position: 'absolute',
    backgroundColor: '#7A1A22',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  stop: {
    backgroundColor: '#FFFFFF',
    borderColor: '#7A1A22',
  },
  here: {
    backgroundColor: '#FFC62B',
    borderColor: '#172025',
  },
});
