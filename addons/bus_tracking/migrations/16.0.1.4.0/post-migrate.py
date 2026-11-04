"""English is the source language of the backend and a user can choose it: make sure it is active
(a database created in Spanish may have it switched off)."""


def migrate(cr, version):
    cr.execute("UPDATE res_lang SET active = TRUE WHERE code = 'en_US'")
