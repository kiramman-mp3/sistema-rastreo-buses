{
    'name': 'Bus Tracking (Traccar)',
    'version': '16.0.1.5.0',
    'category': 'Operations',
    'summary': 'Track bus routes in real time with Traccar',
    'description': """
Live bus tracking and route monitoring backed by a Traccar server.

* Buses linked to Traccar devices
* Routes with ordered stops and stop-arrival detection
* Live map (Leaflet) with route filter and recent track
* Positions pushed by Traccar (webhook) or pulled by cron
""",
    'author': 'Sistema Rastreo Buses',
    'license': 'LGPL-3',
    'application': True,
    'depends': ['base', 'web', 'mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'data/languages.xml',
        'views/bus_vehicle_views.xml',
        'views/bus_route_views.xml',
        'views/bus_trip_views.xml',
        'views/bus_position_views.xml',
        'views/bus_alert_views.xml',
        'views/bus_run_views.xml',
        'views/bus_shift_views.xml',
        'views/bus_driver_views.xml',
        'views/bus_incident_views.xml',
        'views/bus_complaint_views.xml',
        'views/notification_views.xml',
        'views/res_config_settings_views.xml',
        'views/menus.xml',
        'views/landing_templates.xml',
        'views/portal_templates.xml',
        'views/login_templates.xml',
        'data/ir_cron.xml',
    ],
    'assets': {
        'web._assets_primary_variables': [
            ('before', 'web/static/src/scss/primary_variables.scss',
             'bus_tracking/static/src/scss/primary_variables.scss'),
        ],
        'web.assets_frontend': [
            'bus_tracking/static/src/css/brand.css',
            'bus_tracking/static/src/css/login.css',
        ],
        'web.assets_backend': [
            'bus_tracking/static/src/css/brand.css',
            'bus_tracking/static/src/css/backend.css',
            'bus_tracking/static/src/css/live_map.css',
            'bus_tracking/static/src/js/live_map.js',
            'bus_tracking/static/src/js/push_setup.js',
            'bus_tracking/static/src/js/stop_picker.js',
            'bus_tracking/static/src/xml/stop_picker.xml',
            'bus_tracking/static/src/xml/live_map.xml',
            'bus_tracking/static/src/xml/push_setup.xml',
        ],
    },
}
