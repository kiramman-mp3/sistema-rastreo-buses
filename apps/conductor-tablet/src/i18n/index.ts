/** Overlapping keys match addons/bus_tracking/models/portal_i18n.py. qu is a draft. */
export type Lang = 'es' | 'en' | 'qu';

const es = {
  offlineRetry: 'Sin señal. Tu sesión sigue abierta y el GPS sigue guardando; reintentamos solos.',
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
  lang_name: 'Español',
  stops: 'Paradas',
  nextStop: 'Siguiente',
  alerts: 'Alertas',
  noAlerts: 'Sin alertas.',
  incident: 'Reportar incidente',
  endShift: 'Terminar turno',
  confirmEnd: '¿Terminar el turno?',
  confirmEndBody: 'Se deja de enviar el GPS de este bus.',
  cancel: 'Cancelar',
  note: 'Nota (opcional)',
  queued: 'Sin red. El incidente se enviará al volver.',
  sent: 'Incidente enviado.',
  field_kind: 'Qué pasó',
  field_description: 'Descripción',
  submit: 'Enviar reporte',
  kind_other: 'Otro',
  kind_breakdown: 'Avería',
  kind_traffic: 'Tráfico',
  kind_accident: 'Accidente',
  alert_speeding: 'Exceso de velocidad',
  alert_offline: 'sin señal',
  alert_long_stop: 'Parada larga',
  alert_off_route: 'Fuera de ruta',
  update_error: 'No pudimos actualizar. Reintentando…',
  map_label: 'Mapa con los buses de la ruta',
  scanQr: 'Leer código QR',
  scanDriverBadge: 'Escanear credencial QR',
  badgeLoggingIn: 'Identificando chofer…',
  badgeError: 'Credencial no válida o revocada.',
  orManualLogin: 'O ingresar manualmente',
  odooUrl: 'Servidor Odoo',
  qrBad: 'Ese código no es válido. Escanea tu credencial de chofer o el QR de Odoo.',
  cameraNeed: 'Hay que permitir la cámara para leer el QR.',
  confirmStartShift: '¿Iniciar turno?',
  confirmStartBody: 'Se comenzará a registrar el recorrido y transmitir la ubicación GPS del bus en tiempo real.',
  confirmSignOut: '¿Cerrar sesión?',
  confirmSignOutBody: 'Se cerrará la sesión del conductor en esta tableta.',
  confirmSignOutShiftBody: 'Se finalizará el turno activo y se cerrará la sesión en esta tableta.',
  nextStopHero: 'PRÓXIMA PARADA',
  noNextStop: 'Fin del recorrido',
  loadingMap: 'Cargando mapa de la ruta…',
  driverLabel: 'Conductor',
  availableBuses: '1. Elige el bus',
  availableRoutes: '2. Elige la ruta',
  noStopsAvailable: 'No hay paradas registradas para esta ruta.',
  backToShift: 'Volver al turno',
  cabinNext: 'Próxima parada',
  cabinAfter: 'Después',
  cabinStopsLeft: 'Quedan {n} paradas',
  cabinLastStop: 'Última parada',
  gpsSending: 'GPS enviando',
  gpsSaving: 'Sin red: {n} puntos guardados',
  gpsWaiting: 'Esperando señal del GPS',
  gpsOff: 'GPS sin permiso',
  lockedMoving: 'En marcha. Detén el bus para usar la pantalla.',
  actionProblem: 'Avisar un problema',
  actionProblemSub: 'Tráfico, avería, accidente',
  actionSos: 'SOS',
  actionSosSub: 'Mantén presionado',
  sosHolding: 'Sigue presionando…',
  sosSending: 'Enviando SOS…',
  sosSent: 'SOS enviado. Esperando a la central.',
  sosSeen: 'La central vio tu SOS · {by} · {time}',
  sosQueued: 'SOS guardado. Sale apenas haya señal.',
  modeDay: 'Día',
  modeNight: 'Noche',
  incidentWhat: '¿Qué pasa?',
  incidentNote: 'Nota (opcional)',
  incidentNoteHint: 'Por ejemplo: dónde está el trancón',
  incidentSend: 'Enviar aviso',
  loginTitle: 'Ingreso del chofer',
  loginHelp: 'Escanea tu credencial o escribe tu usuario y tu clave.',
  serverHint: 'Servidor (solo soporte técnico)',
  selectTitle: 'Elige tu bus y tu línea',
  selectHello: 'Hola, {name}',
  busTaken: 'En uso',
  clockLabel: 'Hora',
  gpsDevice: 'Dispositivo en Traccar',
  gpsRefresh: 'Actualizar',
  gpsOpen: 'Ver el estado del GPS',
};

const en: typeof es = {
  offlineRetry: 'No signal. You are still signed in and the GPS keeps saving; we retry on our own.',
  login: 'Sign in',
  user: 'User',
  password: 'Password',
  badCredentials: 'Wrong user or password.',
  network: 'No connection. Try again.',
  chooseBus: 'Choose the bus',
  chooseRoute: 'Choose the route',
  startShift: 'Start shift',
  taken: 'In use',
  onShift: 'Shift in progress',
  bus: 'Bus',
  route: 'Route',
  signOut: 'Sign out',
  loading: 'Loading…',
  conflict: 'That bus or your user already has a shift.',
  noGps: 'That bus has no GPS registered.',
  gpsPermission: 'Allow location all the time for the bus GPS.',
  gpsStatus: 'GPS status',
  gpsForeground: 'Location while in use',
  gpsBackground: 'Background location',
  gpsQueue: 'Queued points',
  gpsLast: 'Last send',
  gpsNone: 'No position has been sent yet.',
  granted: 'Granted',
  denied: 'Denied',
  lang_name: 'English',
  stops: 'Stops',
  nextStop: 'Next',
  alerts: 'Alerts',
  noAlerts: 'No alerts.',
  incident: 'Report incident',
  endShift: 'End shift',
  confirmEnd: 'End the shift?',
  confirmEndBody: 'This bus will stop sending GPS.',
  cancel: 'Cancel',
  note: 'Note (optional)',
  queued: 'Offline. The incident will send when the network returns.',
  sent: 'Incident sent.',
  field_kind: 'What happened',
  field_description: 'Description',
  submit: 'Send report',
  kind_other: 'Other',
  kind_breakdown: 'Breakdown',
  kind_traffic: 'Traffic',
  kind_accident: 'Accident',
  alert_speeding: 'Speeding',
  alert_offline: 'no signal',
  alert_long_stop: 'Long stop',
  alert_off_route: 'Off route',
  update_error: "We couldn't update. Retrying…",
  map_label: 'Map with the buses of the route',
  scanQr: 'Scan QR code',
  scanDriverBadge: 'Scan driver badge',
  badgeLoggingIn: 'Identifying driver…',
  badgeError: 'Driver badge invalid or revoked.',
  orManualLogin: 'Or sign in manually',
  odooUrl: 'Odoo server',
  qrBad: 'Invalid QR code. Scan your driver badge or Odoo setup QR.',
  cameraNeed: 'Allow the camera to scan the QR.',
  confirmStartShift: 'Start shift?',
  confirmStartBody: 'Trip tracking and live GPS transmission will begin for this bus.',
  confirmSignOut: 'Sign out?',
  confirmSignOutBody: 'This driver session will be closed on this tablet.',
  confirmSignOutShiftBody: 'The active shift will end and your session will close on this tablet.',
  nextStopHero: 'NEXT STOP',
  noNextStop: 'End of route',
  loadingMap: 'Loading route map…',
  driverLabel: 'Driver',
  availableBuses: '1. Choose bus',
  availableRoutes: '2. Choose route',
  noStopsAvailable: 'No stops registered for this route.',
  backToShift: 'Back to shift',
  cabinNext: 'Next stop',
  cabinAfter: 'Then',
  cabinStopsLeft: '{n} stops left',
  cabinLastStop: 'Last stop',
  gpsSending: 'GPS sending',
  gpsSaving: 'No network: {n} points saved',
  gpsWaiting: 'Waiting for the GPS',
  gpsOff: 'GPS not allowed',
  lockedMoving: 'Moving. Stop the bus to use the screen.',
  actionProblem: 'Report a problem',
  actionProblemSub: 'Traffic, breakdown, accident',
  actionSos: 'SOS',
  actionSosSub: 'Press and hold',
  sosHolding: 'Keep pressing…',
  sosSending: 'Sending SOS…',
  sosSent: 'SOS sent. Waiting for the office.',
  sosSeen: 'The office saw your SOS · {by} · {time}',
  sosQueued: 'SOS saved. It goes out as soon as there is signal.',
  modeDay: 'Day',
  modeNight: 'Night',
  incidentWhat: 'What is happening?',
  incidentNote: 'Note (optional)',
  incidentNoteHint: 'For example: where the traffic jam is',
  incidentSend: 'Send',
  loginTitle: 'Driver sign-in',
  loginHelp: 'Scan your badge or type your user and password.',
  serverHint: 'Server (technical support only)',
  selectTitle: 'Pick your bus and your line',
  selectHello: 'Hello, {name}',
  busTaken: 'In use',
  clockLabel: 'Time',
  gpsDevice: 'Traccar device',
  gpsRefresh: 'Refresh',
  gpsOpen: 'Show the GPS state',
};

const qu: typeof es = {
  ...es,
  lang_name: 'Kichwa (borrador)',
  login: 'Yaykuy',
  stops: 'Sayana kuna',
  alert_offline: 'mana rikurin',
  update_error: 'Mana kutin rikuchi ushashkachu. Kutin ruranchik…',
};

export const messages: Record<Lang, typeof es> = { es, en, qu };

export type Message = keyof typeof es;

let lang: Lang = 'es';
const listeners = new Set<(next: Lang) => void>();

export function getLang(): Lang {
  return lang;
}

export function setLang(next: Lang) {
  lang = next;
  listeners.forEach((listener) => listener(next));
}

export function onLang(listener: (next: Lang) => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function t(key: Message): string {
  return messages[lang][key] ?? messages.es[key];
}

/** A message with values: tf('cabinStopsLeft', { n: 3 }). */
export function tf(key: Message, values: Record<string, string | number>): string {
  return t(key).replace(/\{(\w+)\}/g, (all, name: string) => (name in values ? String(values[name]) : all));
}

function capitalize(text: string): string {
  return text ? text.charAt(0).toUpperCase() + text.slice(1) : text;
}

/** As a title: some labels are shared with the portal, where they read in the middle of a sentence. */
export function alertLabel(kind: string): string {
  if (kind === 'speeding') return capitalize(t('alert_speeding'));
  if (kind === 'offline') return capitalize(t('alert_offline'));
  if (kind === 'long_stop') return capitalize(t('alert_long_stop'));
  if (kind === 'off_route') return capitalize(t('alert_off_route'));
  return kind;
}

export const LANGS: Lang[] = ['es', 'en', 'qu'];
