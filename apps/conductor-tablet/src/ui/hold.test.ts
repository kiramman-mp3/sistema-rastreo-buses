import { createHold } from './hold';

describe('press and hold', () => {
  beforeEach(() => jest.useFakeTimers());
  afterEach(() => jest.useRealTimers());

  test('fires once after the whole time', () => {
    const fire = jest.fn();
    const hold = createHold(1500, fire);
    hold.start();
    jest.advanceTimersByTime(1499);
    expect(fire).not.toHaveBeenCalled();
    jest.advanceTimersByTime(1);
    expect(fire).toHaveBeenCalledTimes(1);
    expect(hold.active).toBe(false);
  });

  test('lifting the finger early never fires', () => {
    const fire = jest.fn();
    const hold = createHold(1500, fire);
    hold.start();
    jest.advanceTimersByTime(1000);
    hold.cancel();
    jest.advanceTimersByTime(5000);
    expect(fire).not.toHaveBeenCalled();
    expect(hold.active).toBe(false);
  });

  test('pressing in twice does not schedule two shots', () => {
    const fire = jest.fn();
    const hold = createHold(1500, fire);
    hold.start();
    jest.advanceTimersByTime(700);
    hold.start();
    jest.advanceTimersByTime(5000);
    expect(fire).toHaveBeenCalledTimes(1);
  });

  test('cancelling when nothing is running is harmless, and the hold can be used again', () => {
    const fire = jest.fn();
    const hold = createHold(1500, fire);
    hold.cancel();
    hold.start();
    jest.advanceTimersByTime(1500);
    hold.cancel();
    hold.start();
    jest.advanceTimersByTime(1500);
    expect(fire).toHaveBeenCalledTimes(2);
  });

  test('a cancel after the shot does not undo it', () => {
    const fire = jest.fn();
    const hold = createHold(1000, fire);
    hold.start();
    jest.advanceTimersByTime(1000);
    hold.cancel();
    expect(fire).toHaveBeenCalledTimes(1);
  });
});
