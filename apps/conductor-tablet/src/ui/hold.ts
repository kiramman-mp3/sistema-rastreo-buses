/**
 * Press and hold: fires once when the finger has stayed down for the whole time, and never when it
 * lifted earlier. Kept apart from the button so "a bump of the road cannot send an SOS" is tested.
 */
export type Hold = {
  start(): void;
  cancel(): void;
  readonly active: boolean;
};

type Timers = {
  set: (callback: () => void, ms: number) => unknown;
  clear: (id: unknown) => void;
};

const real: Timers = {
  set: (callback, ms) => setTimeout(callback, ms),
  clear: (id) => clearTimeout(id as ReturnType<typeof setTimeout>),
};

export function createHold(durationMs: number, onFire: () => void, timers: Timers = real): Hold {
  let timer: unknown = null;
  return {
    start() {
      // A second press-in while one is running must not schedule a second shot.
      if (timer !== null) return;
      timer = timers.set(() => {
        timer = null;
        onFire();
      }, durationMs);
    },
    cancel() {
      if (timer === null) return;
      timers.clear(timer);
      timer = null;
    },
    get active() {
      return timer !== null;
    },
  };
}
