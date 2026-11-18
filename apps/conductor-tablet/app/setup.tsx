import { Redirect } from 'expo-router';

import { useSession } from '../src/state/SessionContext';

/**
 * uta-buses://setup?odoo=… opened by the system camera lands here. It changes nothing: a server address from a
 * link any page could open is not trusted. Signed out, the login screen asks to scan the code from the app.
 */
export default function SetupLink() {
  const { snapshot } = useSession();
  if (!snapshot.ready) return null;
  if (snapshot.token) return <Redirect href="/" />;
  return <Redirect href={{ pathname: '/login', params: { link: '1' } }} />;
}
