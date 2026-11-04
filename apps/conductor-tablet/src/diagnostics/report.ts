/**
 * What the tablet tells the office when the app itself fails. The limits are the ones of
 * `/bus_tracking/driver/client_error` in Odoo: a longer report would be refused.
 */
export const MESSAGE_MAX = 500;
export const STACK_MAX = 3000;
export const SHORT_MAX = 60;

export type ErrorReport = {
  message: string;
  stack?: string;
  /** App version, e.g. "1.0.0". */
  app: string;
  /** Route the driver was on, e.g. "/shift". */
  screen?: string;
  /** ISO time on the tablet. */
  at: string;
};

function clip(text: string, max: number): string {
  return text.length > max ? text.slice(0, max - 1) + '…' : text;
}

function describe(error: unknown): { message: string; stack?: string } {
  if (error instanceof Error) return { message: `${error.name}: ${error.message}`, stack: error.stack };
  if (typeof error === 'string') return { message: error };
  try {
    return { message: JSON.stringify(error) ?? String(error) };
  } catch {
    return { message: String(error) };
  }
}

/** Anything that can be thrown, as a report the server accepts. Never throws. */
export function buildReport(error: unknown, context: { app: string; screen?: string; now?: Date }): ErrorReport {
  const { message, stack } = describe(error);
  const report: ErrorReport = {
    message: clip(message.trim() || 'Unknown error', MESSAGE_MAX),
    app: clip(context.app, SHORT_MAX),
    at: (context.now ?? new Date()).toISOString(),
  };
  if (stack) report.stack = clip(stack, STACK_MAX);
  if (context.screen) report.screen = clip(context.screen, SHORT_MAX);
  return report;
}
