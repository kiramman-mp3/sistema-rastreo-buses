/**
 * One message box for the whole app: the SOS answer, an alert, an error. The state is told by a word
 * and a shape, never by colour alone: a diamond for danger, a square for a warning, a dot for good news
 * (the same shapes as the GPS badge). The border is thin and even; no thick side stripe.
 */
import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

import { tp } from '../i18n';
import { pickNotices, type NoticeItem, type NoticeTone } from '../shift/notices';
import { Txt } from './cabin';
import { useLayout } from './layout';
import { useTheme } from './ThemeProvider';
import { border, shape, space } from './theme';

const MARK = 16;

function NoticeMark({ tone, color }: { tone: NoticeTone; color: string }) {
  return (
    <View
      style={[
        styles.mark,
        { backgroundColor: color },
        tone === 'ok' && styles.markDot,
        tone === 'warn' && styles.markSquare,
        tone === 'danger' && styles.markDiamond,
      ]}
    />
  );
}

type NoticeProps = {
  item: NoticeItem;
  /** Lines of the detail before it is cut; the full text stays in the screen reader label. */
  detailLines?: number;
  style?: StyleProp<ViewStyle>;
};

export function Notice({ item, detailLines = 2, style }: NoticeProps) {
  const { palette } = useTheme();
  const { sizes } = useLayout();
  const color = item.tone === 'ok' ? palette.ok : item.tone === 'warn' ? palette.warn : palette.danger;
  // The mark sits on the middle of the first line of the title.
  const firstLine = Math.round(sizes.body * 1.3);
  return (
    <View
      accessible
      accessibilityLabel={item.detail ? `${item.title}. ${item.detail}` : item.title}
      accessibilityLiveRegion={item.live}
      style={[styles.box, { borderColor: color }, style]}
    >
      <View style={[styles.markSlot, { height: firstLine }]}>
        <NoticeMark tone={item.tone} color={color} />
      </View>
      <View style={styles.text}>
        <Txt bold size="body" color={color}>
          {item.title}
        </Txt>
        {item.detail ? (
          <Txt size="small" lines={detailLines}>
            {item.detail}
          </Txt>
        ) : null}
      </View>
    </View>
  );
}

type NoticeListProps = {
  items: NoticeItem[];
  max: number;
  detailLines?: number;
  style?: StyleProp<ViewStyle>;
};

/** The notices that fit, then a line saying how many more there are. */
export function NoticeList({ items, max, detailLines, style }: NoticeListProps) {
  if (items.length === 0) return null;
  const { shown, hidden } = pickNotices(items, max);
  return (
    <View style={[{ gap: space[2] }, style]}>
      {shown.map((item) => (
        <Notice key={item.key} item={item} detailLines={detailLines} />
      ))}
      {hidden > 0 ? (
        <Txt size="small" dim>
          {tp('moreNotice', hidden)}
        </Txt>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  box: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: space[3],
    paddingHorizontal: space[4],
    paddingVertical: space[3],
    ...shape.control,
    borderWidth: border.thin,
  },
  markSlot: {
    justifyContent: 'center',
  },
  mark: {
    width: MARK,
    height: MARK,
  },
  markDot: {
    borderRadius: MARK / 2,
  },
  markSquare: {
    borderRadius: 2,
  },
  markDiamond: {
    width: MARK - 2,
    height: MARK - 2,
    borderRadius: 2,
    transform: [{ rotate: '45deg' }],
  },
  text: {
    flex: 1,
    gap: space[1],
  },
});
