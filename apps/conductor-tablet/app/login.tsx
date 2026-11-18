import { useCallback, useState } from 'react';
import { router, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { Image, Pressable, StyleSheet, View } from 'react-native';

import { ApiError, AuthError, NetworkError } from '../src/api/client';
import { t } from '../src/i18n';
import { useLang } from '../src/i18n/LangProvider';
import { useSession } from '../src/state/SessionContext';
import { Action, Field, Press, Screen, Txt } from '../src/ui/cabin';
import { useLayout } from '../src/ui/layout';
import { LangSwitch } from '../src/ui/LangSwitch';
import { LineMark } from '../src/ui/LineMark';
import { Notice } from '../src/ui/Notice';
import { lift, shape, space } from '../src/ui/theme';
import { useTheme } from '../src/ui/ThemeProvider';

export default function Login() {
  useLang();
  const { palette } = useTheme();
  const layout = useLayout();
  const session = useSession();
  // Opened from a badge or setup QR read by the system camera (uta-buses://login?… or setup?…). The link is not
  // acted on: any web page could open it, so the code is read again from inside the app.
  const link = useLocalSearchParams<{ token?: string; odoo?: string; link?: string }>();
  const fromLink = Boolean(link.token || link.odoo || link.link);
  const [login, setLogin] = useState('');
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [reveal, setReveal] = useState(false);
  const [error, setError] = useState('');
  const [odooUrl, setOdooUrl] = useState(session.snapshot.odooUrl);
  // The server address is for technical support only: it opens with a long press on the mark.
  const [showServer, setShowServer] = useState(false);

  useFocusEffect(
    useCallback(() => {
      setOdooUrl(session.snapshot.odooUrl);
    }, [session.snapshot.odooUrl]),
  );

  async function submit() {
    // Enter on the keyboard and a double tap both land here: one attempt at a time, and never an empty one.
    if (busy || !login.trim() || !password) return;
    setBusy(true);
    setError('');
    try {
      await session.setOdooUrl(odooUrl);
      await session.login(login.trim(), password);
      // `session.snapshot` here is the one of the last render: let the index route decide with the new one.
      router.replace('/');
    } catch (err) {
      if (err instanceof Error && err.message === 'bad_odoo_url') setError(t('qrBad'));
      else if (err instanceof NetworkError) setError(t('network'));
      else if (err instanceof AuthError || (err instanceof ApiError && err.status === 401)) setError(t('badCredentials'));
      else if (err instanceof ApiError && err.status === 429) setError(t('tooMany'));
      else setError(t('serverError'));
    } finally {
      setBusy(false);
    }
  }

  // Side by side when there is width; stacked (and centred) on a phone in portrait.
  const side = layout.wide;

  return (
    <Screen scroll style={[styles.page, side ? styles.pageSide : styles.pageStack, { gap: side ? space[8] : layout.gap * 2 }]}>
      {/* A real person at the wheel: the app is theirs. Hidden when height is short (keyboard up on a phone). */}
      {side || !layout.short ? (
        <View style={[styles.photo, side ? styles.photoSide : styles.photoStack, { backgroundColor: palette.tint }]}>
          <Pressable
            onLongPress={() => setShowServer((v) => !v)}
            accessibilityLabel="Buses UTA"
            style={[styles.brand, { backgroundColor: palette.panel }]}
          >
            <LineMark scale={0.7} />
            <Txt bold size="body" color={palette.ink}>
              Buses UTA
            </Txt>
          </Pressable>
          {/* A real person at the wheel in a round frame, with a small drawing of the route beside it. */}
          <View style={[styles.portrait, side ? styles.portraitSide : styles.portraitStack]}>
            <View style={[styles.portraitRing, { backgroundColor: palette.panel }]}>
              <View style={styles.portraitClip}>
                <Image
                  source={require('../assets/img/chofer.jpg')}
                  style={styles.portraitImage}
                  resizeMode="cover"
                  accessibilityElementsHidden
                />
              </View>
            </View>
            <View style={[styles.portraitBadge, { backgroundColor: palette.panel }]}>
              <Image source={require('../assets/img/ruta-pin.png')} style={styles.badgeArt} resizeMode="contain" accessibilityElementsHidden />
            </View>
          </View>
          <Txt bold size="title" color={palette.ink} style={styles.welcome}>
            {t('loginTitle')}
          </Txt>
        </View>
      ) : null}

      <View style={[styles.side, side ? styles.sideWide : styles.cardStack]}>
        <View style={styles.intro}>
          <Txt size="body">{t('loginHelp')}</Txt>
          <Txt size="small" dim>
            {t('trackingNoticeLogin')}
          </Txt>
        </View>
      <View
        style={[
          styles.card,
          { backgroundColor: palette.panel, borderColor: palette.edge, padding: layout.phone ? space[4] : space[6] },
          palette.mode === 'day' && lift,
        ]}
      >
        {fromLink ? <Notice item={{ key: 'link', tone: 'warn', title: t('scanFromApp'), live: 'polite' }} /> : null}
        <Action label={t('scanDriverBadge')} onPress={() => router.push('/scan')} kind="accent" />
        <Txt size="small" dim style={styles.or}>
          {t('orManualLogin')}
        </Txt>
        <Field
          value={login}
          onChangeText={setLogin}
          autoCapitalize="none"
          autoCorrect={false}
          placeholder={t('user')}
          accessibilityLabel={t('user')}
          returnKeyType="next"
        />
        {/* The "show" button sits inside the field: a row of its own pushed the sign-in button off a small phone. */}
        <View>
          <Field
            value={password}
            onChangeText={setPassword}
            secureTextEntry={!reveal}
            autoCapitalize="none"
            autoCorrect={false}
            placeholder={t('password')}
            accessibilityLabel={t('password')}
            returnKeyType="go"
            onSubmitEditing={submit}
            style={styles.passwordInput}
          />
          <Press
            onPress={() => setReveal((on) => !on)}
            accessibilityRole="switch"
            accessibilityLabel={`${t('password')}: ${reveal ? t('hidePassword') : t('showPassword')}`}
            accessibilityState={{ checked: reveal }}
            style={styles.reveal}
          >
            <Txt size="small" bold>
              {reveal ? t('hidePassword') : t('showPassword')}
            </Txt>
          </Press>
        </View>
        {showServer ? (
          <View style={styles.server}>
            <Txt size="small" dim>
              {t('serverHint')}
            </Txt>
            <Field
              value={odooUrl}
              onChangeText={setOdooUrl}
              autoCapitalize="none"
              autoCorrect={false}
              placeholder={t('odooUrl')}
                  accessibilityLabel={t('odooUrl')}
                />
          </View>
        ) : null}
        {error ? (
          <Notice item={{ key: 'error', tone: 'danger', title: error, live: 'polite' }} />
        ) : null}
        <Action
          label={busy ? t('loading') : t('login')}
          onPress={submit}
          kind="quiet"
          disabled={busy || !login || !password}
        />
      </View>
        <LangSwitch />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  page: {
    justifyContent: 'center',
  },
  pageSide: {
    flexDirection: 'row',
    alignItems: 'stretch',
  },
  pageStack: {
    flexDirection: 'column',
  },
  photo: {
    ...shape.card,
    alignItems: 'center',
    justifyContent: 'center',
    gap: space[5],
    padding: space[6],
  },
  photoSide: {
    flex: 1,
    minHeight: 420,
  },
  photoStack: {
    width: '100%',
    maxWidth: 560,
    alignSelf: 'center',
    paddingVertical: space[5],
  },
  brand: {
    position: 'absolute',
    top: space[4],
    left: space[4],
    flexDirection: 'row',
    alignItems: 'center',
    gap: space[2],
    paddingVertical: space[1],
    paddingLeft: space[2],
    paddingRight: space[4],
    borderRadius: 999,
  },
  portrait: {
    marginTop: space[8],
  },
  portraitSide: {
    width: 280,
    height: 280,
  },
  portraitStack: {
    width: 150,
    height: 150,
  },
  portraitRing: {
    width: '100%',
    height: '100%',
    padding: 8,
    borderRadius: 999,
  },
  // the clip lives on a wrapper: an Image alone does not round its corners on the web
  portraitClip: {
    flex: 1,
    borderRadius: 999,
    overflow: 'hidden',
  },
  portraitImage: {
    width: '100%',
    height: '100%',
  },
  // the route drawing overlaps the frame at the bottom left, like a sticker
  portraitBadge: {
    position: 'absolute',
    left: -12,
    bottom: 0,
    width: '36%',
    aspectRatio: 1,
    borderRadius: 999,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeArt: {
    width: '125%',
    height: '125%',
  },
  welcome: {
    textAlign: 'center',
  },
  side: {
    gap: space[5],
    justifyContent: 'center',
  },
  sideWide: {
    flex: 1,
    maxWidth: 560,
  },
  intro: {
    gap: space[2],
  },
  card: {
    ...shape.card,
    borderWidth: 1,
    gap: space[3],
  },
  cardStack: {
    width: '100%',
    maxWidth: 560,
    alignSelf: 'center',
  },
  passwordInput: {
    // room for the Show/Hide button that sits inside the field
    paddingRight: space[12] * 2 + space[4],
  },
  reveal: {
    position: 'absolute',
    right: 4,
    top: 0,
    bottom: 0,
    minWidth: 48,
    paddingHorizontal: space[3],
    justifyContent: 'center',
    alignItems: 'center',
  },
  or: {
    textAlign: 'center',
    marginVertical: space[1],
  },
  server: {
    gap: space[2],
  },
});
