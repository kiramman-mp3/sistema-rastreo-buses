const es = {
  login: 'Entrar',
  user: 'Usuario',
  password: 'Contraseña',
  badCredentials: 'Usuario o clave incorrectos.',
  network: 'Sin conexión. Inténtalo de nuevo.',
  chooseBus: 'Elige el bus',
  chooseRoute: 'Elige la ruta',
  startShift: 'Iniciar turno',
  taken: 'Ocupado',
  onShift: 'Turno en curso',
  bus: 'Bus',
  route: 'Ruta',
  signOut: 'Cerrar sesión',
  loading: 'Cargando…',
  conflict: 'Ese bus o tu usuario ya tienen un turno.',
  noGps: 'Ese bus no tiene GPS registrado.',
  gpsPermission: 'Hay que permitir la ubicación todo el tiempo para el GPS del bus.',
  gpsStatus: 'Estado del GPS',
  gpsForeground: 'Ubicación en uso',
  gpsBackground: 'Ubicación en segundo plano',
  gpsQueue: 'Puntos en cola',
  gpsLast: 'Último envío',
  gpsNone: 'Todavía no se ha enviado ninguna posición.',
  granted: 'Concedido',
  denied: 'Denegado',
};

export type Message = keyof typeof es;

export function t(key: Message): string {
  return es[key];
}
