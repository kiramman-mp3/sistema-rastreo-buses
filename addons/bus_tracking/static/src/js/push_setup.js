/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onMounted, useState } from "@odoo/owl";

const SW_URL = "/bus_tracking/sw.js";
const SW_SCOPE = "/bus_tracking/";

function keyToBytes(base64Url) {
    const padded = base64Url + "=".repeat((4 - (base64Url.length % 4)) % 4);
    const raw = atob(padded.replace(/-/g, "+").replace(/_/g, "/"));
    return Uint8Array.from(raw, (char) => char.charCodeAt(0));
}

export class PushSetup extends Component {
    static template = "bus_tracking.PushSetup";

    setup() {
        this.rpc = useService("rpc");
        this.state = useState({ status: "loading", devices: 0, message: "", busy: false });
        onMounted(() => this.refresh());
    }

    get supported() {
        return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window;
    }

    async currentSubscription() {
        const registration = await navigator.serviceWorker.getRegistration(SW_SCOPE);
        return registration ? registration.pushManager.getSubscription() : null;
    }

    async refresh() {
        if (!this.supported) {
            this.state.status = "unsupported";
            return;
        }
        if (Notification.permission === "denied") {
            this.state.status = "denied";
            return;
        }
        const subscription = await this.currentSubscription();
        const info = await this.rpc("/bus_tracking/push/state", { endpoint: subscription && subscription.endpoint });
        this.state.devices = info.devices;
        this.state.status = !info.available ? "unavailable" : info.subscribed ? "subscribed" : "idle";
    }

    async enable() {
        this.state.busy = true;
        this.state.message = "";
        try {
            const permission = await Notification.requestPermission();
            if (permission !== "granted") {
                this.state.status = permission === "denied" ? "denied" : "idle";
                return;
            }
            const info = await this.rpc("/bus_tracking/push/state", {});
            const registration = await navigator.serviceWorker.register(SW_URL, { scope: SW_SCOPE });
            await navigator.serviceWorker.ready;
            const subscription = await registration.pushManager.subscribe({
                userVisibleOnly: true,
                applicationServerKey: keyToBytes(info.key),
            });
            const json = subscription.toJSON();
            const result = await this.rpc("/bus_tracking/push/subscribe", {
                endpoint: json.endpoint,
                keys: json.keys,
                user_agent: navigator.userAgent,
            });
            if (!result.ok) {
                await subscription.unsubscribe();
                this.state.message = "error";
            }
        } catch (error) {
            this.state.message = "error";
        } finally {
            this.state.busy = false;
            await this.refresh();
        }
    }

    async disable() {
        this.state.busy = true;
        try {
            const subscription = await this.currentSubscription();
            if (subscription) {
                await this.rpc("/bus_tracking/push/unsubscribe", { endpoint: subscription.endpoint });
                await subscription.unsubscribe();
            }
        } finally {
            this.state.busy = false;
            await this.refresh();
        }
    }

    async sendTest() {
        this.state.busy = true;
        try {
            const result = await this.rpc("/bus_tracking/push/test", {});
            this.state.message = result.sent ? "sent" : "none";
        } finally {
            this.state.busy = false;
        }
    }
}

registry.category("actions").add("bus_tracking.push_setup", PushSetup);
