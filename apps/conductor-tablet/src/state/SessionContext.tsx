import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { createClient, defaultBaseUrl } from '../api/client';
import { errorQueue } from '../diagnostics';
import { gpsKv, gpsStore } from '../gps/store';
import { liveGps } from '../gps/tracker';
import { IncidentQueue } from '../incidents/queue';
import { odooUrlStore, pendingEndStore, secureStore } from './secureStore';
import { Session, type SessionSnapshot } from './session';

const SessionContext = createContext<Session | null>(null);
const SnapshotContext = createContext<SessionSnapshot | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const session = useMemo(
    () =>
      new Session(
        secureStore,
        createClient({ baseUrl: defaultBaseUrl(), store: secureStore }),
        liveGps,
        gpsStore,
        new IncidentQueue(gpsKv),
        odooUrlStore,
        pendingEndStore,
        errorQueue,
      ),
    [],
  );

  const [snapshot, setSnapshot] = useState(session.snapshot);

  useEffect(() => {
    return session.subscribe(() => {
      setSnapshot({ ...session.snapshot });
    });
  }, [session]);

  useEffect(() => {
    session.boot().catch(() => undefined);
  }, [session]);

  return (
    <SessionContext.Provider value={session}>
      <SnapshotContext.Provider value={snapshot}>
        {children}
      </SnapshotContext.Provider>
    </SessionContext.Provider>
  );
}

export function useSession(): Session {
  const session = useContext(SessionContext);
  const snapshot = useContext(SnapshotContext);
  if (!session || !snapshot) throw new Error('SessionProvider is missing');

  return useMemo(() => {
    return new Proxy(session, {
      get(target, prop, receiver) {
        if (prop === 'snapshot') return snapshot;
        return Reflect.get(target, prop, receiver);
      },
    });
  }, [session, snapshot]);
}

/**
 * The session itself, stable for the whole life of the app. Use it in effects and timers: the object
 * from useSession() changes on every state update, so an effect that depends on it restarts each time
 * (and a refresh that updates the state would restart its own timer forever).
 */
export function useSessionActions(): Session {
  const session = useContext(SessionContext);
  if (!session) throw new Error('SessionProvider is missing');
  return session;
}
