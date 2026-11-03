/**
 * When the next stop changes the name of the stop moves in for a moment, so a driver who glances at the
 * screen notices it advanced. It is one small cue, not a transition: it must not play when the screen
 * opens, when the data merely arrives late, or for people who asked the system to reduce motion.
 */
export function shouldCueStopChange(
  previous: number | null | undefined,
  next: number | null,
  reduceMotion: boolean,
): boolean {
  if (reduceMotion) return false;
  if (next === null) return false; // no stop to announce
  if (previous === undefined || previous === null) return false; // the first stop shown was already there
  return previous !== next;
}
