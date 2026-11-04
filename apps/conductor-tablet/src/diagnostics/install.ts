import { buildReport } from './report';
import type { ErrorQueue } from './queue';

type Handler = (error: unknown, isFatal?: boolean) => void;

/** The slice of React Native's global `ErrorUtils` this needs. */
export type ErrorUtilsLike = {
  getGlobalHandler(): Handler;
  setGlobalHandler(handler: Handler): void;
};

let screen: string | undefined;

/** The route the driver is on; the layout keeps this current so a report says where it happened. */
export function setCurrentScreen(path: string | undefined) {
  screen = path;
}

/**
 * Records every uncaught error in the queue and then lets React Native do what it always did (the red box
 * in development, closing the app in a release build). On a fatal error the write may not finish before the
 * app dies: it is a best effort, which is why the report also goes out on the next launch.
 */
export function installErrorReporting(errorUtils: ErrorUtilsLike | undefined, queue: ErrorQueue, app: string) {
  if (!errorUtils) return;
  // Fast refresh runs this again in development: wrap the handler once, not once per reload.
  const marked = errorUtils as ErrorUtilsLike & { reportingInstalled?: boolean };
  if (marked.reportingInstalled) return;
  marked.reportingInstalled = true;
  const previous = errorUtils.getGlobalHandler();
  errorUtils.setGlobalHandler((error, isFatal) => {
    try {
      queue.push(buildReport(error, { app, screen })).catch(() => undefined);
    } catch {
      // reporting must never make a failure worse
    }
    previous(error, isFatal);
  });
}
