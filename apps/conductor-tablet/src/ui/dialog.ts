import { Alert, Platform } from 'react-native';

export type DialogButton = {
  text: string;
  style?: 'default' | 'cancel' | 'destructive';
  onPress?: () => void;
};

/**
 * A question or a notice. On the phone and the tablet it is the system alert. React Native's Alert does
 * nothing on the web build (previews, screenshots, browser tests), so there it falls back to the browser's
 * own confirm and alert: the same choices, the same callbacks.
 */
export function showDialog(title: string, message?: string, buttons: DialogButton[] = [{ text: 'OK' }]) {
  if (Platform.OS !== 'web') {
    Alert.alert(title, message, buttons);
    return;
  }
  const text = message ? `${title}\n\n${message}` : title;
  const cancel = buttons.find((button) => button.style === 'cancel');
  const action = buttons.find((button) => button.style !== 'cancel');
  if (buttons.length < 2) {
    window.alert(text);
    buttons[0]?.onPress?.();
    return;
  }
  if (window.confirm(text)) action?.onPress?.();
  else cancel?.onPress?.();
}
