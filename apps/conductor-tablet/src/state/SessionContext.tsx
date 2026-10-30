import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';

import { createClient, defaultBaseUrl } from '../api/client';
import { gpsKv, gpsStore } from '../gps/store';
import { liveGps } from '../gps/tracker';
import { IncidentQueue } from '../incidents/queue';
import { secureStore } from './secureStore';
import { Session } from './session';

const SessionContext = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const session = useMemo(
    () =>
      new Session(
        secureStore,
        createClient({ baseUrl: defaultBaseUrl(), store: secureStore }),
        liveGps,
        gpsStore,
        new IncidentQueue(gpsKv),
      ),
    [],
  );
  const [, bump] = useState(0);
  useEffect(() => session.subscribe(() => bump((n) => n + 1)), [session]);
  useEffect(() => {
    session.boot().catch(() => undefined);
  }, [session]);
  return <SessionContext.Provider value={session}>{children}</SessionContext.Provider>;
}

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) throw new Error('SessionProvider is missing');
  return session;
}
