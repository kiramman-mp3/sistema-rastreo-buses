# Centro de Documentación: Buses UTA

Portal central de documentación técnica, operativa, de diseño y de aseguramiento de calidad del **Sistema de Rastreo de Buses en Tiempo Real** (Odoo 16 + Traccar + App Móvil Expo).

---

## Estructura de la Documentación

```
docs/
├── README.md                      # Este portal de documentación y mapa de navegación
│
├── arquitectura/                  # Planes maestros, especificaciones y diseño técnico
│   ├── PLAN.md                    # Plan maestro del sistema (fases 0 a 15: backend, mapa y portal)
│   ├── PLAN-APP-CHOFER.md         # Plan de implementación de la app móvil (fases 16 a 22, 25 e iOS)
│   ├── PLAN-UX.md                 # Plan de rediseño de experiencia de usuario y cabina
│   ├── PLAN-UI-MOVIL.md           # Plan de adaptabilidad responsiva y ergonomía móvil
│   ├── PLAN-AUDITORIA.md          # Plan de remediación de auditoría integral ISO/IEC 25010
│   ├── PLAN-RUBRICA.md            # Plan para cubrir la rúbrica del proyecto final (fases R1 a R12) y su estado final
│   ├── REQUISITOS.md              # Análisis del problema y requisitos funcionales y no funcionales con criterio de aceptación
│   ├── ARQUITECTURA-Y-DATOS.md    # Arquitectura, flujo de un dato y modelo de datos
│   └── FLEET.md                   # Integración con Odoo Fleet: decisión, reglas y migración
│
├── guias/                         # Manuales operativos y guías de puesta en marcha
│   ├── GUIA-CHOFER.md             # Manual de usuario para choferes en tableta o teléfono (Android/iOS)
│   ├── OPERACION.md               # Guía diaria de operación y despacho en consola de Odoo
│   ├── PRODUCCION.md              # Guía de despliegue en servidor Azure VM, Caddy HTTPS y backups
│   ├── GRAFANA.md                 # Grafana incrustado en Odoo: rol de solo lectura, token, despliegue y operación
│   ├── DEMO-TRACCAR-CLIENT.md     # Demostración con un celular y Traccar Client, evidencias y Azure frente a Cloudflare
│   └── PERSONALIZACION.md         # Parámetros institucionales UTA, mapa en Ambato y límites
│
├── diseno/                        # Identidad visual, tokens y marco normativo
│   ├── DISENO.md                  # Sistema de diseño, tokens de color, contrastes AAA y tipografía
│   └── PRIVACIDAD.md              # Política de protección de datos personales y retención (LOPDP)
│
├── calidad/                       # Sistema de Aseguramiento de la Calidad (SQA)
│   ├── README.md                  # Índice y política de mantenimiento del área de calidad
│   ├── 01-politica-y-alcance.md   # Política de calidad, objetivos y alcance del sistema
│   ├── 02-estandares-y-reglas.md  # Estándares de codificación, convenciones y buenas prácticas
│   ├── 03-plan-y-casos-de-prueba.md # Plan maestro de pruebas y matriz de casos de verificación
│   ├── 04-resultados-y-metricas.md # Resultados de ejecución, cobertura y métricas de complejidad
│   ├── 05-registro-de-defectos.md # Catálogo histórico de defectos encontrados y cerrados (DEF-001 a DEF-038)
│   ├── 06-lluvia-de-ideas.md      # Lluvia de ideas estructurada y matriz de priorización
│   ├── 07-pareto.md               # Diagramas y análisis de Pareto (80/20) para defectos y fallos
│   ├── 08-ishikawa.md             # Diagramas de causa y efecto (espina de pescado)
│   ├── 09-cumplimiento-iso.md     # Evaluación de cumplimiento ISO/IEC 25010 y CMMI Nivel 2/3
│   ├── 10-evidencias-y-reproduccion.md # Instrucciones para reproducir pruebas y verificar evidencias
│   ├── 11-elementos-acs.md        # Administración de la Configuración del Software (SCM/ACS)
│   ├── 12-validacion-ux.md        # Protocolo de evaluación heurística y usabilidad con usuarios
│   ├── 13-recorridos-de-prueba.md # 12 recorridos simulados y la comparación entre lo esperado y lo detectado
│   ├── 14-metricas-de-transporte.md # Los 12 indicadores con fórmula, fuente, umbrales, SQL y resultado (generado del código)
│   ├── 15-tablero-grafana.md      # Tablero de Odoo y Grafana incrustado: contenido, pruebas y hallazgos
│   ├── 16-sonarqube.md            # Análisis estático con SonarQube: antes y después, interpretación y evidencia
│   ├── 17-rendimiento-por-volumen.md # Tiempos de cada pantalla hasta 1 000 000 de posiciones
│   ├── 18-mejora-continua-pdca.md # Ishikawa, Pareto y cuatro ciclos PDCA de la etapa de la rúbrica
│   ├── 19-matriz-de-trazabilidad.md # Cada actividad, entregable y criterio con su evidencia
│   ├── Informe_calidad_rastreo_buses.pdf # Informe formal compilado para auditoría externa
│   ├── evidencias/                # Registros crudos en JSON y logs de pruebas y auditorías
│   └── figuras/                   # Gráficos de cobertura, Pareto e Ishikawa generados
│
└── academico/                     # Registro de sesiones de trabajo y material de titulación
    ├── BITACORA.md                # Bitácora cronológica exhaustiva de desarrollo e incidencias
    └── GUION_DEFENSA.md           # Estructura temática y guion para sustentación del proyecto
```

---

## Rutas de Lectura por Rol

Para optimizar la consulta según el perfil del lector, se recomiendan los siguientes itinerarios de lectura:

### 1. Desarrollador Backend (Odoo / Traccar / Infraestructura)
1. [`arquitectura/PLAN.md`](arquitectura/PLAN.md): Arquitectura base, modelos relacionales y crons.
2. [`arquitectura/PLAN-APP-CHOFER.md`](arquitectura/PLAN-APP-CHOFER.md): API REST y autenticación de choferes.
3. [`guias/PRODUCCION.md`](guias/PRODUCCION.md): Configuración de contenedores Docker, proxy Caddy y pooler PostgreSQL.
4. [`calidad/02-estandares-y-reglas.md`](calidad/02-estandares-y-reglas.md): Estándares de código PEP 8, Linters y SQL Seguro.

### 2. Desarrollador Móvil (Expo / React Native / TypeScript)
1. [`arquitectura/PLAN-APP-CHOFER.md`](arquitectura/PLAN-APP-CHOFER.md): Requisitos de geolocalización, sincronización y cola local.
2. [`arquitectura/PLAN-UI-MOVIL.md`](arquitectura/PLAN-UI-MOVIL.md): Layouts adaptables a diferentes pantallas y factores de forma.
3. [`diseno/DISENO.md`](diseno/DISENO.md): Tokens de color, espaciados y temas claro/oscuro.
4. [`guias/GUIA-CHOFER.md`](guias/GUIA-CHOFER.md): Casos de uso de los conductores en cabina.

### 3. Operador de Transporte y Chofer
1. [`guias/GUIA-CHOFER.md`](guias/GUIA-CHOFER.md): Guía rápida ilustrada para iniciar turnos, escaneo QR y emergencias SOS.
2. [`guias/OPERACION.md`](guias/OPERACION.md): Procedimiento de monitoreo, atención de incidentes y control de despachos.
3. [`diseno/PRIVACIDAD.md`](diseno/PRIVACIDAD.md): Alcance del rastreo y derechos sobre la privacidad de la ubicación.

### 4. Administrador de Sistemas / DevOps
1. [`guias/PRODUCCION.md`](guias/PRODUCCION.md): Puesta en marcha en Azure, certificados SSL Let's Encrypt y crons de respaldo.
2. [`guias/PERSONALIZACION.md`](guias/PERSONALIZACION.md): Configuración de dominios, teselas de mapa y parámetros institucionales.
3. [`../scripts/README.md`](../scripts/README.md): Catálogo de scripts de mantenimiento, restauración y semillas.

### 5. Auditor de Calidad / Evaluador Académico
1. [`academico/GUION_DEFENSA.md`](academico/GUION_DEFENSA.md): Guion resumen de la solución, justificación y valor técnico.
2. [`calidad/01-politica-y-alcance.md`](calidad/01-politica-y-alcance.md) y [`calidad/09-cumplimiento-iso.md`](calidad/09-cumplimiento-iso.md): Cumplimiento de estándares de calidad de software.
3. [`calidad/05-registro-de-defectos.md`](calidad/05-registro-de-defectos.md): Trazabilidad de defectos encontrados y solucionados.
4. [`academico/BITACORA.md`](academico/BITACORA.md): Registro histórico de evolución del proyecto día a día.

---

## Matriz de Áreas y Documentos

| Área | Documento | Propósito Principal | Audiencia Clave |
|---|---|---|---|
| **Arquitectura** | [`PLAN.md`](arquitectura/PLAN.md) | Roadmap general de fases 0 a 15 | Desarrolladores, Arquitectos |
| **Arquitectura** | [`PLAN-APP-CHOFER.md`](arquitectura/PLAN-APP-CHOFER.md) | Diseño de la app del conductor | Desarrolladores móviles |
| **Arquitectura** | [`PLAN-UX.md`](arquitectura/PLAN-UX.md) | Decisiones de interacción y flujo | Diseñadores, Frontend |
| **Arquitectura** | [`PLAN-RUBRICA.md`](arquitectura/PLAN-RUBRICA.md) | Plan de implementación para cubrir la rúbrica del proyecto final | Equipo, docente |
| **Arquitectura** | [`PLAN-UI-MOVIL.md`](arquitectura/PLAN-UI-MOVIL.md) | Accesibilidad y ergonomía táctil | Desarrolladores móviles |
| **Arquitectura** | [`PLAN-AUDITORIA.md`](arquitectura/PLAN-AUDITORIA.md) | Plan de contingencia y hardening | Líderes técnicos, Seguridad |
| **Guías** | [`GUIA-CHOFER.md`](guias/GUIA-CHOFER.md) | Manual operativo de cabina | Choferes de autobús |
| **Guías** | [`OPERACION.md`](guias/OPERACION.md) | Gestión de tráfico y alertas | Supervisores de flota |
| **Guías** | [`PRODUCCION.md`](guias/PRODUCCION.md) | Manual de administración de servidores | Administradores de sistemas |
| **Guías** | [`PERSONALIZACION.md`](guias/PERSONALIZACION.md) | Parámetros específicos de la UTA | Administradores de Odoo |
| **Guías** | [`GRAFANA.md`](guias/GRAFANA.md) | Tableros de Grafana dentro de Odoo | Administradores de sistemas |
| **Guías** | [`DEMO-TRACCAR-CLIENT.md`](guias/DEMO-TRACCAR-CLIENT.md) | Demostración con celular y Traccar Client | Equipo del proyecto, defensa |
| **Diseño** | [`DISENO.md`](diseno/DISENO.md) | Tokens, colores y componentes UI | Diseñadores, Frontend |
| **Diseño** | [`PRIVACIDAD.md`](diseno/PRIVACIDAD.md) | Tratamiento de datos y retención | Oficial de privacidad, Jurídico |
| **Calidad** | [`calidad/`](calidad/) | Carpeta completa de calidad ISO 25010 | Auditores, QA Engineers |
| **Académico** | [`BITACORA.md`](academico/BITACORA.md) | Bitácora de trabajo de ingeniería | Docentes, Evaluadores, Equipo |
| **Académico** | [`GUION_DEFENSA.md`](academico/GUION_DEFENSA.md) | Guion para tribunal de grado | Estudiantes, Evaluadores |
