/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, onWillUnmount, useState } from "@odoo/owl";

// Odoo gives the page a token of the length it has set (see bus.grafana); the page asks for a new one a bit before
// the old one runs out, so a screen left open all day keeps working.
const RENEW_AT = 0.9;
const MIN_RENEW_MS = 60 * 1000;

export class BusGrafana extends Component {
    static template = "bus_tracking.Grafana";

    setup() {
        this.rpc = useService("rpc");
        this.state = useState({
            loading: true,
            error: false,
            configured: false,
            canManage: false,
            url: "",
            token: "",
            dashboards: [],
            current: "bus-resumen",
        });
        this.timer = null;
        onWillStart(() => this.load());
        onWillUnmount(() => clearTimeout(this.timer));
    }

    async load() {
        clearTimeout(this.timer);
        try {
            const access = await this.rpc("/bus_tracking/grafana/token");
            this.state.configured = access.configured;
            this.state.canManage = access.can_manage;
            if (access.configured) {
                this.state.url = access.url;
                this.state.token = access.token;
                this.state.dashboards = access.dashboards;
                if (!access.dashboards.some((d) => d.uid === this.state.current)) {
                    this.state.current = access.dashboards[0].uid;
                }
                this.timer = setTimeout(() => this.load(), Math.max(access.expires_in * 1000 * RENEW_AT, MIN_RENEW_MS));
            }
            this.state.error = false;
        } catch {
            this.state.error = true;
            this.timer = setTimeout(() => this.load(), MIN_RENEW_MS);
        } finally {
            this.state.loading = false;
        }
    }

    get src() {
        const { url, current, token } = this.state;
        return `${url}/d/${current}?kiosk&theme=light&auth_token=${encodeURIComponent(token)}`;
    }

    select(uid) {
        this.state.current = uid;
    }
}

registry.category("actions").add("bus_tracking.grafana", BusGrafana);
