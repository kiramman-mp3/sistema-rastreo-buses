/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadCSS, loadJS } from "@web/core/assets";
import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";

const LEAFLET_CSS = "/bus_tracking/static/lib/leaflet/leaflet.css";
const LEAFLET_JS = "/bus_tracking/static/lib/leaflet/leaflet.js";
const TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const REFRESH_MS = 10000;
const DEFAULT_CENTER = [-1.2417, -78.6167];   // Ambato; replaced by the Settings value once loaded
const STATUS_COLORS = { moving: "#28a745", stopped: "#ffc107", offline: "#6c757d" };

export class BusLiveMap extends Component {
    static template = "bus_tracking.LiveMap";

    setup() {
        this.rpc = useService("rpc");
        this.mapRef = useRef("map");
        this.state = useState({
            vehicles: [],
            routes: [],
            alertLabels: {},
            mapCenter: DEFAULT_CENTER,
            routeId: "",
            pathKey: "",
            selectedId: this.props.action?.params?.vehicle_id || null,
            error: null,
        });
        this.markers = {};
        this.fitted = false;

        onMounted(async () => {
            await Promise.all([loadCSS(LEAFLET_CSS), loadJS(LEAFLET_JS)]);
            this.initMap();
            await this.refresh();
            this.timer = setInterval(() => this.refresh(), REFRESH_MS);
        });
        onWillUnmount(() => {
            clearInterval(this.timer);
            if (this.map) {
                this.map.remove();
            }
        });
    }

    get filteredVehicles() {
        const rid = this.state.routeId;
        return this.state.vehicles.filter((v) => !rid || String(v.route_id) === rid);
    }

    initMap() {
        const L = window.L;
        this.map = L.map(this.mapRef.el).setView(DEFAULT_CENTER, 13);
        L.tileLayer(TILES, {
            maxZoom: 19,
            attribution: "&copy; OpenStreetMap contributors",
        }).addTo(this.map);
        this.routeLayer = L.layerGroup().addTo(this.map);
        this.busLayer = L.layerGroup().addTo(this.map);
        this.trackLayer = L.layerGroup().addTo(this.map);
    }

    async refresh() {
        try {
            const data = await this.rpc("/bus_tracking/live", {});
            this.state.vehicles = data.vehicles;
            this.state.routes = data.routes;
            this.state.alertLabels = data.alert_labels;
            this.state.mapCenter = data.map_center;
            this.state.error = null;
        } catch (e) {
            this.state.error = "Cannot load positions";
            return;
        }
        this.draw();
        if (!this.fitted) {
            this.fitted = true;
            const sel = this.state.vehicles.find((v) => v.id === this.state.selectedId);
            if (sel) {
                this.selectVehicle(sel);
            } else {
                this.fitAll();
            }
        }
    }

    draw() {
        const L = window.L;
        const rid = this.state.routeId;

        this.routeLayer.clearLayers();
        for (const route of this.state.routes) {
            if (rid && String(route.id) !== rid) {
                continue;
            }
            const pts = route.stops.map((s) => [s.lat, s.lon]);
            if (route.paths && route.paths.length) {
                route.paths.forEach((path, index) => {
                    const hidden = this.state.pathKey && this.state.pathKey !== `${route.id}:${index}`;
                    if (hidden) {
                        return;
                    }
                    L.polyline(path.points, { color: route.color, weight: this.state.pathKey ? 6 : 4, opacity: this.state.pathKey ? 0.95 : 0.6 })
                        .bindTooltip(`${path.name} · ${path.km} km`)
                        .on("click", () => this.selectPath(route.id, index))
                        .addTo(this.routeLayer);
                });
            } else if (pts.length > 1) {
                L.polyline(pts, { color: route.color, weight: 3, opacity: 0.6, dashArray: "6 6" })
                    .addTo(this.routeLayer);
            }
            for (const s of route.stops) {
                L.circle([s.lat, s.lon], { radius: s.radius, color: route.color, weight: 1, fillOpacity: 0.1 })
                    .addTo(this.routeLayer);
                L.circleMarker([s.lat, s.lon], { radius: 5, color: "#fff", weight: 2, fillColor: route.color, fillOpacity: 1 })
                    .bindTooltip(`${route.code} · ${s.name}`)
                    .addTo(this.routeLayer);
            }
        }

        this.busLayer.clearLayers();
        this.markers = {};
        for (const v of this.filteredVehicles) {
            const icon = L.divIcon({
                className: "",
                iconSize: [30, 30],
                iconAnchor: [15, 15],
                html: `<div class="o_bus_marker" style="background:${v.color};border-color:${STATUS_COLORS[v.status]}">
                           <i class="fa fa-bus"></i></div>`,
            });
            const marker = L.marker([v.lat, v.lon], { icon })
                .bindTooltip(
                    `<b>${this.escape(v.name)}</b> ${this.escape(v.plate)}<br/>
                     ${v.speed} km/h · ${v.status}<br/>${this.escape(v.fix_time)} UTC`
                )
                .on("click", () => this.selectVehicle(v))
                .addTo(this.busLayer);
            this.markers[v.id] = marker;
        }
    }

    escape(text) {
        const el = document.createElement("div");
        el.textContent = text || "";
        return el.innerHTML;
    }

    fitAll() {
        const L = window.L;
        const pts = this.filteredVehicles.map((v) => [v.lat, v.lon]);
        for (const route of this.state.routes) {
            if (!this.state.routeId || String(route.id) === this.state.routeId) {
                route.stops.forEach((s) => pts.push([s.lat, s.lon]));
                (route.paths || []).forEach((path) => path.points.forEach((p) => pts.push(p)));
            }
        }
        if (pts.length) {
            this.map.fitBounds(L.latLngBounds(pts), { padding: [40, 40], maxZoom: 16 });
        } else {
            this.map.setView(this.state.mapCenter, 13);
        }
    }

    selectPath(routeId, index) {
        this.state.pathKey = `${routeId}:${index}`;
        this.draw();
        const route = this.state.routes.find((r) => r.id === routeId);
        this.map.fitBounds(window.L.latLngBounds(route.paths[index].points), { padding: [40, 40] });
    }

    resetPaths() {
        this.state.pathKey = "";
        this.draw();
        this.fitAll();
    }

    onRouteChange(ev) {
        this.state.pathKey = "";
        this.state.routeId = ev.target.value;
        this.trackLayer.clearLayers();
        this.state.selectedId = null;
        this.draw();
        this.fitAll();
    }

    async selectVehicle(v) {
        const L = window.L;
        this.state.selectedId = v.id;
        this.map.setView([v.lat, v.lon], Math.max(this.map.getZoom(), 15));
        this.trackLayer.clearLayers();
        try {
            const pts = await this.rpc("/bus_tracking/track", { vehicle_id: v.id, hours: 4 });
            if (pts.length > 1) {
                L.polyline(pts, { color: v.color, weight: 4, opacity: 0.9 }).addTo(this.trackLayer);
            }
        } catch (e) {
            // track is optional
        }
        const marker = this.markers[v.id];
        if (marker) {
            marker.openTooltip();
        }
    }
}

registry.category("actions").add("bus_tracking.live_map", BusLiveMap);
