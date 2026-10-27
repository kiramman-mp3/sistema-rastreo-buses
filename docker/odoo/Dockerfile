ARG ODOO_IMAGE=odoo:16.0
FROM ${ODOO_IMAGE}

# pywebpush sends the browser push notifications (VAPID + RFC 8291 encryption).
# Odoo 16's image ships Python 3.9, cryptography 3.3.2 and pyOpenSSL 20.0.1; upgrading cryptography
# breaks pyOpenSSL and Odoo no longer starts. So cryptography is pinned to what the image has, and the
# pywebpush 1.x series (which does not need aiohttp) is used.
# The addon works without it: push is simply reported as unavailable.
USER root
RUN pip3 install --no-cache-dir "cryptography==3.3.2" "pywebpush==1.14.1" "py-vapid==1.9.0" "http-ece==1.2.0"
USER odoo
