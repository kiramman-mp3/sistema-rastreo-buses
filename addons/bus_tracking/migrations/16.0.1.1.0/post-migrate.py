"""Managers used to imply the Driver group. Take it away from managers who never drove a shift,
so they can no longer sign in on a tablet and see every shift again."""


def migrate(cr, version):
    cr.execute("""
        DELETE FROM res_groups_users_rel rel
         USING ir_model_data drv, ir_model_data mgr
         WHERE drv.module = 'bus_tracking' AND drv.name = 'group_bus_driver'
           AND mgr.module = 'bus_tracking' AND mgr.name = 'group_bus_manager'
           AND rel.gid = drv.res_id
           AND rel.uid IN (SELECT uid FROM res_groups_users_rel WHERE gid = mgr.res_id)
           AND NOT EXISTS (SELECT 1 FROM bus_shift s WHERE s.user_id = rel.uid)
    """)
