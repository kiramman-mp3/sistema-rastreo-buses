def migrate(cr, version):
    """The fines are no longer presented as a demonstration: the switch that said so is gone. Drop the value it
    left in the system parameters."""
    cr.execute("DELETE FROM ir_config_parameter WHERE key = 'bus_tracking.fines_real'")
