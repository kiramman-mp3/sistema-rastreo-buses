/**
 * One message box for the whole app: the SOS answer, an alert, an error. The state is told by a word
 * and a shape, never by colour alone: a diamond for danger, a square for a warning, a dot for good news
 * (the same shapes as the GPS badge). The border is thin and even; no thick side stripe.
 * A notice that can be closed has a button for it at the end, big enough for a finger: an alert read once
 * should not sit on the screen for the whole shift.
 */
import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

import { t, tp } from '../i18n';
import { pickNotices, type NoticeItem, type NoticeTone } from '../shift/notices';
import { Press, Txt } from './cabin';
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
  /** A phone on its side: one tight row, the title and its detail on the same line. */
  compact?: boolean;
  /** Given when the notice can be closed. */
  onDismiss?: () => void;
  /** How many notices wait behind this one; a compact notice shows "+N" beside the title. */
  moreCount?: number;
  /** The same in words, for the screen reader ("1 aviso más"). */
  more?: string;
  style?: StyleProp<ViewStyle>;
};

export function Notice({ item, detailLines = 2, compact = false, onDismiss, more, moreCount = 0, style }: NoticeProps) {
  const { palette } = useTheme();
  const { sizes } = useLayout();
  const color = item.tone === 'ok' ? palette.ok : item.tone === 'warn' ? palette.warn : palette.danger;
  // The mark sits on the middle of the first line of the title.
  const firstLine = Math.round(sizes.body * 1.3);
  return (
    <View
      accessible={!onDismiss}
      accessibilityLabel={item.detail ? `${item.title}. ${item.detail}` : item.title}
      accessibilityLiveRegion={item.live}
      style={[styles.box, compact && styles.boxCompact, { borderColor: color }, style]}
    >
      <View style={[styles.markSlot, { height: firstLine }]}>
        <NoticeMark tone={item.tone} color={color} />
      </View>
      <View style={styles.text} accessible={!!onDismiss} accessibilityLabel={item.detail ? `${item.title}. ${item.detail}` : item.title}>
        {compact && more && moreCount > 0 ? (
          <View style={styles.titleRow}>
            <View style={styles.titleFlex}>
              <Txt bold size="body" color={color} lines={1}>
                {item.title}
              </Txt>
            </View>
            <View accessible accessibilityLabel={more}>
              <Txt size="small" dim lines={1}>
                {`+${moreCount}`}
              </Txt>
            </View>
          </View>
        ) : (
          <Txt bold size="body" color={color} lines={compact ? 1 : undefined}>
            {item.title}
          </Txt>
        )}
        {item.detail ? (
          <Txt size="small" lines={compact ? 1 : detailLines}>
            {item.detail}
          </Txt>
        ) : null}
      </View>
      {onDismiss ? (
        <Press
          onPress={onDismiss}
          accessibilityRole="button"
          accessibilityLabel={`${t('dismissNotice')}: ${item.title}`}
          style={[styles.close, { borderColor: palette.ink2 }]}
        >
          <Txt bold size="small">
            {t('dismiss')}
          </Txt>
        </Press>
      ) : null}
    </View>
  );
}

type NoticeListProps = {
  items: NoticeItem[];
  max: number;
  detailLines?: number;
  compact?: boolean;
  /** Closes the notice with this `dismissKey`. Only notices that say they can be closed get the button. */
  onDismiss?: (dismissKey: string) => void;
  style?: StyleProp<ViewStyle>;
};

/** The notices that fit, then a line saying how many more there are. */
export function NoticeList({ items, max, detailLines, compact, onDismiss, style }: NoticeListProps) {
  if (items.length === 0) return null;
  const { shown, hidden } = pickNotices(items, max);
  return (
    <View style={[{ gap: space[2] }, style]}>
      {shown.map((item, index) => {
        const key = item.dismissKey;
        return (
          <Notice
            key={item.key}
            item={item}
            detailLines={detailLines}
            compact={compact}
            more={compact && hidden > 0 && index === shown.length - 1 ? tp('moreNotice', hidden) : undefined}
            moreCount={hidden}
            onDismiss={onDismiss && item.dismissible && key ? () => onDismiss(key) : undefined}
          />
        );
      })}
      {hidden > 0 && !compact ? (
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
  boxCompact: {
    alignItems: 'center',
    paddingVertical: space[1],
    paddingHorizontal: space[3],
    gap: space[2],
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
  titleRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: space[2],
  },
  titleFlex: {
    flexShrink: 1,
  },
  close: {
    minWidth: 72,
    minHeight: 48,
    paddingHorizontal: space[3],
    ...shape.control,
    borderWidth: border.thin,
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'center',
  },
});
