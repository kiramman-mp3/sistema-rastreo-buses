import { installErrorReporting, setCurrentScreen, type ErrorUtilsLike } from './install';
import { ErrorQueue, memoryKv } from './queue';

function fakeErrorUtils() {
  const previous = jest.fn();
  let current: (error: unknown, isFatal?: boolean) => void = previous;
  const utils: ErrorUtilsLike = {
    getGlobalHandler: () => current,
    setGlobalHandler: (handler) => {
      current = handler;
    },
  };
  return { utils, previous, fire: (error: unknown, fatal = false) => current(error, fatal) };
}

const settle = () => new Promise((resolve) => setTimeout(resolve, 0));

describe('global error reporting', () => {
  afterEach(() => setCurrentScreen(undefined));

  test('records the error and still hands it to the original handler', async () => {
    const { utils, previous, fire } = fakeErrorUtils();
    const queue = new ErrorQueue(memoryKv());
    installErrorReporting(utils, queue, '1.0.0');
    setCurrentScreen('/shift');
    const error = new Error('boom');
    fire(error, true);
    await settle();
    expect(previous).toHaveBeenCalledWith(error, true);
    const [saved] = await queue.load();
    expect(saved).toMatchObject({ message: 'Error: boom', app: '1.0.0', screen: '/shift' });
  });

  test('a queue that fails never stops the original handler', () => {
    const { utils, previous, fire } = fakeErrorUtils();
    const broken = {
      push: () => {
        throw new Error('disk full');
      },
    } as unknown as ErrorQueue;
    installErrorReporting(utils, broken, '1.0.0');
    expect(() => fire(new Error('x'))).not.toThrow();
    expect(previous).toHaveBeenCalledTimes(1);
  });

  test('a rejected save is swallowed', async () => {
    const { utils, previous, fire } = fakeErrorUtils();
    const rejecting = { push: () => Promise.reject(new Error('nope')) } as unknown as ErrorQueue;
    installErrorReporting(utils, rejecting, '1.0.0');
    fire(new Error('x'));
    await settle();
    expect(previous).toHaveBeenCalledTimes(1);
  });

  test('installing twice (fast refresh) records each error once', async () => {
    const { utils, fire } = fakeErrorUtils();
    const queue = new ErrorQueue(memoryKv());
    installErrorReporting(utils, queue, '1.0.0');
    installErrorReporting(utils, queue, '1.0.0');
    fire(new Error('once'));
    await settle();
    expect(await queue.size()).toBe(1);
  });

  test('where there is no ErrorUtils (web, tests) nothing happens', () => {
    expect(() => installErrorReporting(undefined, new ErrorQueue(memoryKv()), '1.0.0')).not.toThrow();
  });
});
