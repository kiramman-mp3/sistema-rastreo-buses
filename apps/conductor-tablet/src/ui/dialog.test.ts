import { Alert, Platform } from 'react-native';

import { showDialog } from './dialog';

describe('showDialog', () => {
  const original = Platform.OS;
  afterEach(() => {
    Platform.OS = original;
    jest.restoreAllMocks();
    delete (globalThis as { window?: unknown }).window;
  });

  test('on the phone it is the system alert, with the same buttons', () => {
    Platform.OS = 'android';
    const alert = jest.spyOn(Alert, 'alert').mockImplementation(() => undefined);
    const buttons = [{ text: 'No', style: 'cancel' as const }, { text: 'Yes' }];
    showDialog('Title', 'Body', buttons);
    expect(alert).toHaveBeenCalledWith('Title', 'Body', buttons);
  });

  test('on the web a confirmed question runs the action and a refused one the cancel', () => {
    Platform.OS = 'web';
    const yes = jest.fn();
    const no = jest.fn();
    const confirm = jest.fn().mockReturnValueOnce(true).mockReturnValueOnce(false);
    (globalThis as { window?: unknown }).window = { confirm, alert: jest.fn() };
    const buttons = [{ text: 'No', style: 'cancel' as const, onPress: no }, { text: 'Yes', onPress: yes }];
    showDialog('Sure?', 'It ends', buttons);
    expect(confirm).toHaveBeenCalledWith('Sure?\n\nIt ends');
    expect(yes).toHaveBeenCalledTimes(1);
    expect(no).not.toHaveBeenCalled();
    showDialog('Sure?', 'It ends', buttons);
    expect(no).toHaveBeenCalledTimes(1);
    expect(yes).toHaveBeenCalledTimes(1);
  });

  test('on the web a notice is a plain alert', () => {
    Platform.OS = 'web';
    const alert = jest.fn();
    (globalThis as { window?: unknown }).window = { confirm: jest.fn(), alert };
    showDialog('Saved');
    expect(alert).toHaveBeenCalledWith('Saved');
  });
});
