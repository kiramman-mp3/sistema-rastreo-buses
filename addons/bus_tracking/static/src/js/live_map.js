/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadCSS, loadJS } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";

const LEAFLET_CSS = "/bus_tracking/static/lib/leaflet/leaflet.css";
const LEAFLET_JS = "/bus_tracking/static/lib/leaflet/leaflet.js";
// Until the server says otherwise (Settings > Map tiles).
const TILES = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png?key=cb1_500h_1_2faaa5c6c3a1e1bb863b25cb";
const TILE_OPTIONS = {
    maxZoom: 19,
    subdomains: "abcd",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
};
// The GPS reports every 5 s. Asking and gliding over the same short span keeps the bus close to where it is.
const REFRESH_MS = 4000;
const DEFAULT_CENTER = [-1.2417, -78.6167];
const BUS_SVG = '<svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true" focusable="false">' +
    '<rect x="3" y="2" width="14" height="14" rx="3" fill="currentColor"/>' +
    '<rect x="5" y="4.5" width="10" height="5" rx="1" fill="#172025" opacity="0.55"/>' +
    '<rect x="5" y="16" width="2.5" height="2.5" rx="1" fill="currentColor"/>' +
    '<rect x="12.5" y="16" width="2.5" height="2.5" rx="1" fill="currentColor"/></svg>';

/** Shortest turn between two headings, so a bus crossing north never spins all the way round. */
export function angleDelta(target, current) {
    let diff = (target - current) % 360;
    if (diff > 180) diff -= 360;
    if (diff < -180) diff += 360;
    return diff;
}

/** "8 s ago", "4 min ago", "2 h ago" (translated). */
export function ago(seconds) {
    if (seconds === null || seconds === undefined) {
        return "";
    }
    if (seconds < 60) {
        return _t("%s s ago").replace("%s", Math.max(0, Math.round(seconds)));
    }
    if (seconds < 3600) {
        return _t("%s min ago").replace("%s", Math.round(seconds / 60));
    }
    return _t("%s h ago").replace("%s", Math.round(seconds / 3600));
}

function escapeHtml(text) {
    return String(text || "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function utcSeconds(text) {
    if (!text) {
        return null;
    }
    const when = Date.parse(text.replace(" ", "T") + "Z");
    return isNaN(when) ? null : (Date.now() - when) / 1000;
}

export class BusLiveMap extends Component {
    static template = "bus_tracking.LiveMap";

    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.notification = useService("notification");
        this.mapRef = useRef("map");
        this.state = useState({
            vehicles: [],
            routes: [],
            incidents: [],
            alertLabels: {},
            newComplaints: 0,
            routeId: "",
            filter: "all",
            search: "",
            tab: "atencion",
            selectedId: this.props.action?.params?.vehicle_id || null,
            panelOpen: true,
            error: null,
            lastSync: null,
            now: Date.now(),
        });
        this.tracked = new Map();
        this.frame = null;
        this.fitted = false;
        this.knownSos = new Set();
        this.labels = {
            moving: _t("On route"),
            stopped: _t("Stopped"),
            offline: _t("No signal"),
        };

        onMounted(async () => {
            await Promise.all([loadCSS(LEAFLET_CSS), loadJS(LEAFLET_JS)]);
            this.initMap();
            await this.refresh();
            this.poll = setInterval(() => {
                if (!document.hidden) {
                    this.refresh();
                }
            }, REFRESH_MS);
            this.clock = setInterval(() => {
                this.state.now = Date.now();
            }, 1000);
            this.onVisible = () => {
                if (!document.hidden) {
                    this.refresh();
                }
            };
            document.addEventListener("visibilitychange", this.onVisible);
        });

        onWillUnmount(() => {
            clearInterval(this.poll);
            clearInterval(this.clock);
            document.removeEventListener("visibilitychange", this.onVisible);
            if (this.frame) {
                cancelAnimationFrame(this.frame);
            }
            if (this.map) {
                this.map.remove();
            }
        });
    }

    // ------------------------------------------------------------------ data

    async refresh() {
        try {
            // The lines and stops rarely change and are the heavy part: the server only sends them when the key differs.
            const data = await this.rpc("/bus_tracking/live", { routes_key: this.routesVersion || "" });
            this.state.vehicles = data.vehicles || [];
            if (data.routes) {
                this.state.routes = data.routes;
                this.routesVersion = data.routes_key;
            }
            this.state.incidents = data.incidents || [];
            this.state.alertLabels = data.alert_labels || {};
            this.state.newComplaints = data.new_complaints || 0;
            this.state.error = null;
            this.state.lastSync = Date.now();
            if (data.tile_url && data.tile_url !== this.tiles._url) {
                this.tiles.setUrl(data.tile_url);
            }
            this.syncVehicles();
            this.drawRoutes(data.map_center);
            this.syncIncidents();
            this.warnAboutNewSos();
        } catch {
            this.state.error = _t("Could not update. Retrying in a few seconds.");
        }
    }

    statusOf(v) {
        if (!v.connected) {
            return "offline";
        }
        return v.status === "moving" ? "moving" : "stopped";
    }

    get counts() {
        const counts = { all: 0, moving: 0, stopped: 0, offline: 0, alert: 0 };
        for (const v of this.routeVehicles) {
            counts.all += 1;
            counts[this.statusOf(v)] += 1;
            if (v.alerts.length) {
                counts.alert += 1;
            }
        }
        return counts;
    }

    get routeVehicles() {
        const id = this.state.routeId;
        return id ? this.state.vehicles.filter((v) => String(v.route_id) === String(id)) : this.state.vehicles;
    }

    get filteredVehicles() {
        let list = this.routeVehicles;
        const f = this.state.filter;
        if (f === "alert") {
            list = list.filter((v) => v.alerts.length);
        } else if (f !== "all") {
            list = list.filter((v) => this.statusOf(v) === f);
        }
        const q = this.state.search.trim().toLowerCase();
        if (q) {
            list = list.filter((v) => [v.name, v.plate, v.driver, v.route_name].some((x) => (x || "").toLowerCase().includes(q)));
        }
        return list;
    }

    get selected() {
        return this.state.vehicles.find((v) => v.id === this.state.selectedId) || null;
    }

    get selectedRoute() {
        const v = this.selected;
        return v ? this.state.routes.find((r) => r.id === v.route_id) || null : null;
    }

    get sosOpen() {
        return this.state.incidents.filter((i) => i.kind === "sos");
    }

    /** What needs a person now, most serious first: SOS, incidents, open alerts, new complaints. */
    get attention() {
        const items = [];
        for (const i of this.state.incidents) {
            items.push({
                key: "i" + i.id,
                level: i.kind === "sos" ? 0 : 1,
                title: i.kind === "sos" ? _t("Emergency (SOS)") : i.label,
                bus: i.vehicle_name,
                vehicleId: i.vehicle_id,
                route: i.route_name,
                note: i.note,
                age: utcSeconds(i.time),
                incidentId: i.id,
            });
        }
        for (const v of this.state.vehicles) {
            for (const kind of v.alerts) {
                items.push({
                    key: "a" + v.id + kind,
                    level: 2,
                    title: this.state.alertLabels[kind] || kind,
                    bus: v.name,
                    vehicleId: v.id,
                    route: v.route_name,
                    note: "",
                    age: null,
                });
            }
        }
        items.sort((a, b) => a.level - b.level || (a.age ?? 0) - (b.age ?? 0));
        return items;
    }

    get attentionCount() {
        return this.attention.length + (this.state.newComplaints ? 1 : 0);
    }

    get syncText() {
        if (this.state.error) {
            return this.state.error;
        }
        if (!this.state.lastSync) {
            return _t("Loading…");
        }
        const s = (this.state.now - this.state.lastSync) / 1000;
        return s < 3 ? _t("Live") : _t("Updated %s").replace("%s", ago(s));
    }

    sosAge(incident) {
        // state.now changes every second, so this re-renders as the minutes pass
        return this.state.now && ago(utcSeconds(incident.time));
    }

    /** Accessible names that say which bus: several buttons share the same visible words. */
    showLabel(busName) {
        return _t("Show %s on the map").replace("%s", busName || "");
    }

    seenLabel(title, busName) {
        return `${_t("Mark as seen")}: ${title || ""} · ${busName || ""}`;
    }

    fixAge(v) {
        return ago(utcSeconds(v.fix_time));
    }

    incidentAge(item) {
        return ago(item.age === null ? null : item.age + (this.state.now - this.state.lastSync) / 1000);
    }

    stopsOf(route) {
        return route ? route.stops : [];
    }

    // ------------------------------------------------------------------ map

    initMap() {
        const L = window.L;
        this.map = L.map(this.mapRef.el, { zoomControl: false }).setView(DEFAULT_CENTER, 13);
        L.control.zoom({ position: "bottomright" }).addTo(this.map);
        this.tiles = L.tileLayer(TILES, TILE_OPTIONS).addTo(this.map);
        this.routeLayer = L.layerGroup().addTo(this.map);
        this.trackLayer = L.layerGroup().addTo(this.map);
        this.incidentLayer = L.layerGroup().addTo(this.map);
        this.busLayer = L.layerGroup().addTo(this.map);
    }

    drawRoutes(center) {
        const L = window.L;
        // Stops and recorded tracks change too, not only the list of routes: the server's key covers them.
        const key = this.state.routeId + "|" + this.routesVersion;
        if (key === this.routesKey) {
            return;
        }
        this.routesKey = key;
        this.routeLayer.clearLayers();
        const shown = this.state.routeId
            ? this.state.routes.filter((r) => String(r.id) === String(this.state.routeId))
            : this.state.routes;
        for (const r of shown) {
            for (const path of r.paths) {
                // not interactive: an unnamed line would be an empty stop for keyboard users
                L.polyline(path.points, { color: r.color, weight: 5, opacity: this.state.routeId ? 0.95 : 0.55, interactive: false })
                    .addTo(this.routeLayer);
            }
            for (const s of r.stops) {
                L.circleMarker([s.lat, s.lon], { radius: 5, color: r.color, weight: 3, fillColor: "#FFFFFF", fillOpacity: 1, interactive: false })
                    .addTo(this.routeLayer);
            }
        }
        if (!this.fitted) {
            this.fitted = true;
            const sel = this.selected;
            if (sel) {
                this.focus(sel);
            } else if (!this.fitAll() && center) {
                this.map.setView(center, 13);
            }
        }
    }

    busIcon(v) {
        const L = window.L;
        const status = this.statusOf(v);
        const alert = v.alerts.length ? " con-alerta" : "";
        const sos = this.state.incidents.some((i) => i.kind === "sos" && i.vehicle_id === v.id) ? " sos" : "";
        return L.divIcon({
            className: "",
            iconSize: [44, 44],
            iconAnchor: [22, 22],
            html: `<span class="o_bus_mk o_bus_mk_${status}${alert}${sos}" style="--c:${escapeHtml(v.color)}">` +
                `<span class="o_bus_mk_rumbo"></span><span class="o_bus_mk_cuerpo">${BUS_SVG}</span>` +
                `<span class="o_bus_mk_nombre">${escapeHtml(v.name)}</span></span>`,
        });
    }

    iconKey(v) {
        const sos = this.state.incidents.some((i) => i.kind === "sos" && i.vehicle_id === v.id);
        return [this.statusOf(v), v.alerts.length > 0, sos, v.color].join("|");
    }

    syncVehicles() {
        const L = window.L;
        const now = performance.now();
        const seen = new Set();
        for (const v of this.state.vehicles) {
            seen.add(v.id);
            let b = this.tracked.get(v.id);
            if (!b) {
                const marker = L.marker([v.lat, v.lon], { icon: this.busIcon(v), title: v.name, zIndexOffset: 400 })
                    .on("click", () => this.select(v.id));
                marker.addTo(this.busLayer);
                b = { marker, from: [v.lat, v.lon], to: [v.lat, v.lon], course: v.course || 0, start: now, key: this.iconKey(v) };
                this.tracked.set(v.id, b);
            } else {
                const here = b.marker.getLatLng();
                b.from = [here.lat, here.lng];
                b.to = [v.lat, v.lon];
                b.start = now;
                b.course += angleDelta(v.course || 0, b.course);
                const key = this.iconKey(v);
                if (key !== b.key) {
                    b.marker.setIcon(this.busIcon(v));
                    b.key = key;
                }
            }
            const el = b.marker.getElement();
            const arrow = el && el.querySelector(".o_bus_mk_rumbo");
            if (arrow) {
                arrow.style.transform = `rotate(${b.course}deg)`;
            }
        }
        for (const [id, b] of this.tracked) {
            if (!seen.has(id)) {
                this.busLayer.removeLayer(b.marker);
                this.tracked.delete(id);
            }
        }
        this.applyFilterToMarkers();
        if (!this.frame && !document.hidden) {
            this.frame = requestAnimationFrame((t) => this.glide(t));
        }
    }

    /** Linear motion over the refresh interval; the loop ends as soon as nothing moves. */
    glide(now) {
        let moving = false;
        for (const b of this.tracked.values()) {
            const p = Math.min((now - b.start) / REFRESH_MS, 1);
            if (b.from[0] !== b.to[0] || b.from[1] !== b.to[1]) {
                b.marker.setLatLng([b.from[0] + (b.to[0] - b.from[0]) * p, b.from[1] + (b.to[1] - b.from[1]) * p]);
                if (p < 1) {
                    moving = true;
                }
            }
        }
        this.frame = moving ? requestAnimationFrame((t) => this.glide(t)) : null;
    }

    applyFilterToMarkers() {
        const visible = new Set(this.filteredVehicles.map((v) => v.id));
        for (const [id, b] of this.tracked) {
            const el = b.marker.getElement();
            if (el) {
                const shown = visible.has(id);
                el.style.opacity = shown ? "1" : "0.18";
                // A faded bus is out of the filter: no clicks and no keyboard stop on it.
                el.style.pointerEvents = shown ? "" : "none";
                el.setAttribute("tabindex", shown ? "0" : "-1");
                el.setAttribute("aria-hidden", shown ? "false" : "true");
            }
        }
    }

    syncIncidents() {
        const L = window.L;
        this.incidentLayer.clearLayers();
        for (const i of this.state.incidents) {
            if (i.lat === null || i.lon === null) {
                continue;
            }
            L.marker([i.lat, i.lon], {
                icon: L.divIcon({
                    className: "",
                    iconSize: [28, 28],
                    iconAnchor: [14, 14],
                    html: `<span class="o_bus_inc ${i.kind === "sos" ? "sos" : ""}" aria-hidden="true">!</span>`,
                }),
                // the "!" is decoration: the marker is announced by its title
                title: `${i.label} · ${i.vehicle_name}`,
                zIndexOffset: 300,
            }).bindTooltip(`${escapeHtml(i.label)} · ${escapeHtml(i.vehicle_name)}`).addTo(this.incidentLayer);
        }
    }

    warnAboutNewSos() {
        for (const i of this.sosOpen) {
            if (this.knownSos.has(i.id)) {
                continue;
            }
            this.knownSos.add(i.id);
            if (!this.firstSosCheckDone) {
                continue;
            }
            this.notification.add(`${i.vehicle_name} · ${i.route_name || ""}`, {
                title: _t("Emergency (SOS)"),
                type: "danger",
                sticky: true,
            });
            if (window.Notification && Notification.permission === "granted" && document.hidden) {
                new Notification(_t("Emergency (SOS)"), { body: i.vehicle_name, tag: "sos-" + i.id });
            }
        }
        this.firstSosCheckDone = true;
    }

    fitAll() {
        const pts = this.filteredVehicles.map((v) => [v.lat, v.lon]);
        if (!pts.length) {
            return false;
        }
        this.map.fitBounds(window.L.latLngBounds(pts), { padding: [80, 80], maxZoom: 15 });
        return true;
    }

    focus(v) {
        this.map.setView([v.lat, v.lon], Math.max(this.map.getZoom(), 15));
    }

    // ------------------------------------------------------------------ actions

    setFilter(filter) {
        this.state.filter = filter;
        this.applyFilterToMarkers();
    }

    onRouteChange(ev) {
        this.state.routeId = ev.target.value;
        this.drawRoutes();
        this.applyFilterToMarkers();
        this.fitAll();
    }

    onSearch() {
        this.applyFilterToMarkers();
    }

    select(id) {
        this.state.selectedId = id;
        const v = this.selected;
        if (v) {
            this.focus(v);
        }
    }

    closeCard() {
        this.state.selectedId = null;
        this.trackLayer.clearLayers();
    }

    async showTrack() {
        const v = this.selected;
        if (!v) {
            return;
        }
        this.trackLayer.clearLayers();
        let pts;
        try {
            pts = await this.rpc("/bus_tracking/track", { vehicle_id: v.id, hours: 4 });
        } catch {
            this.notification.add(_t("Could not load the track. Try again."), { type: "danger" });
            return;
        }
        if (pts && pts.length > 1) {
            const line = window.L.polyline(pts, { color: "#172025", weight: 3, dashArray: "6 6" }).addTo(this.trackLayer);
            this.map.fitBounds(line.getBounds(), { padding: [60, 60] });
        }
    }

    openVehicle(id) {
        this.action.doAction({ type: "ir.actions.act_window", res_model: "bus.vehicle", res_id: id, views: [[false, "form"]] });
    }

    openComplaints() {
        this.action.doAction("bus_tracking.action_bus_complaint");
    }

    async acknowledge(incidentId) {
        try {
            await this.rpc("/bus_tracking/incident/ack", { incident_id: incidentId });
        } catch {
            this.notification.add(_t("Could not mark it as seen. Try again."), { type: "danger" });
            return;
        }
        this.state.incidents = this.state.incidents.filter((i) => i.id !== incidentId);
        this.syncIncidents();
        this.syncVehicles();
    }

    goTo(item) {
        const v = this.state.vehicles.find((x) => x.id === item.vehicleId);
        if (v) {
            this.select(v.id);
        }
    }

    async askNotifications() {
        if (window.Notification && Notification.permission === "default") {
            await Notification.requestPermission();
        }
    }

    lineStatus(v, index) {
        if (v.at === index) {
            return "aqui";
        }
        if (v.after !== null && v.after !== undefined && index <= v.after) {
            return "pasada";
        }
        return "";
    }
}

registry.category("actions").add("bus_tracking.live_map", BusLiveMap);
