import AsyncStorage from '@react-native-async-storage/async-storage';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { loadDismissed, saveDismissed } from './dismissedStore';

type Closed = { shiftId: number | undefined; keys: string[] };

/** The notices the driver closed on this shift, and a way to close one more. */
export function useDismissed(shiftId: number | undefined) {
  // Tagged with its shift: a list read for another shift is never used for this one.
  const [closed, setClosed] = useState<Closed>({ shiftId, keys: [] });

  useEffect(() => {
    if (shiftId === undefined) return undefined;
    let live = true;
    loadDismissed(shiftId, AsyncStorage)
      .then((stored) => {
        if (!live) return;
        setClosed((current) => ({
          shiftId,
          keys: Array.from(new Set([...stored, ...(current.shiftId === shiftId ? current.keys : [])])),
        }));
      })
      .catch(() => undefined); // nothing stored: the notices simply show again
    return () => {
      live = false;
    };
  }, [shiftId]);

  const dismiss = useCallback(
    (noticeKey: string) => {
      setClosed((current) => {
        const keys = current.shiftId === shiftId ? current.keys : [];
        if (keys.includes(noticeKey)) return current;
        const next = [...keys, noticeKey];
        if (shiftId !== undefined) void saveDismissed(shiftId, next, AsyncStorage);
        return { shiftId, keys: next };
      });
    },
    [shiftId],
  );

  const dismissed = useMemo(() => new Set(closed.shiftId === shiftId ? closed.keys : []), [closed, shiftId]);
  return { dismissed, dismiss };
}
