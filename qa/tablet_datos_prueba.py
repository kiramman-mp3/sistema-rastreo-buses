"""Datos de prueba para las pruebas de la app del chofer en el Odoo de DESARROLLO (nunca en producción).

No se ejecuta con Python: se pasa a `odoo shell`.

    # preparar: dirección GPS de prueba y dos alertas abiertas para Bus 01
    docker compose run --rm -T odoo odoo shell -d buses --db_host=db --db_user=odoo --db_password=odoo \
        --no-http < qa/tablet_datos_prueba.py                         (con MODO = "preparar")

    # limpiar: cierra turnos, borra las alertas y los avisos de prueba, quita la dirección GPS
    (con MODO = "limpiar")
"""
env = globals()["env"]   # lo pone `odoo shell`
MODO = "preparar"   # cambia a "limpiar" para dejar la base como estaba

if MODO == "preparar":
    from odoo import fields
    env['ir.config_parameter'].sudo().set_param('bus_tracking.gps_url','https://gps.localtest.me')
    bus=env['bus.vehicle'].search([('name','=','Bus 01')])
    env['bus.alert'].sudo().search([('vehicle_id','=',bus.id)]).unlink()
    now=fields.Datetime.now()
    env['bus.alert'].sudo().create({'vehicle_id':bus.id,'route_id':bus.route_id.id,'kind':'off_route','start_time':now,'distance_m':320.0,'threshold':150.0})
    env['bus.alert'].sudo().create({'vehicle_id':bus.id,'route_id':bus.route_id.id,'kind':'long_stop','start_time':now,'threshold':5.0})
    env.cr.commit()
    print('alertas abiertas:',env['bus.alert'].search_count([('vehicle_id','=',bus.id),('state','=','open')]))
else:
    for s in env['bus.shift'].sudo().search([('state','=','active')]):
        s._end()
    env['bus.alert'].sudo().search([('vehicle_id.name','=','Bus 01')]).unlink()
    inc=env['bus.incident'].sudo().search([('user_id.login','=','chofer1')])
    print('incidentes de prueba borrados:',len(inc)); inc.unlink()
    env['ir.config_parameter'].sudo().set_param('bus_tracking.gps_url', False)
    env.cr.commit()
    print('turnos activos:',env['bus.shift'].search_count([('state','=','active')]))
