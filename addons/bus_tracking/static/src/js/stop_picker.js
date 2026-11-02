/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadCSS, loadJS } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";

const LEAFLET_CSS = "/bus_tracking/static/lib/leaflet/leaflet.css";
const LEAFLET_JS = "/bus_tracking/static/lib/leaflet/leaflet.js";
const TILES = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png?key=cb1_500h_1_2faaa5c6c3a1e1bb863b25cb";

export class BusStopPicker extends Component {
    static template = "bus_tracking.StopPicker";

    setup() {
        this.rpc = useService("rpc");
        this.mapRef = useRef("map");
        const params = this.props.action?.params || {};
        this.routeId = params.route_id;
        this.stopId = params.stop_id || null;
        this.state = useState({ name: "", radius: 50, lat: null, lon: null, route: "", error: null, saving: false });
        this.marker = null;

        onMounted(async () => {
            await Promise.all([loadCSS(LEAFLET_CSS), loadJS(LEAFLET_JS)]);
            const data = await this.rpc("/bus_tracking/stop/load", { route_id: this.routeId, stop_id: this.stopId });
            if (data.error) {
                this.state.error = data.error;
                return;
            }
            this.state.route = data.route;
            this.initMap(data);
        });
        onWillUnmount(() => this.map && this.map.remove());
    }

    initMap(data) {
        const L = window.L;
        this.map = L.map(this.mapRef.el).setView(data.center, 14);
        L.tileLayer(TILES, {
            maxZoom: 19,
            subdomains: "abcd",
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
        }).addTo(this.map);
        const bounds = [];
        (data.lines || []).forEach((line) => {
            L.polyline(line.points, { color: data.color, weight: 4, opacity: 0.6 }).addTo(this.map);
            line.points.forEach((p) => bounds.push(p));
        });
        data.stops.forEach((stop) => {
            bounds.push([stop.lat, stop.lon]);
            if (data.stop && stop.id === data.stop.id) {
                return;
            }
            L.circleMarker([stop.lat, stop.lon], { radius: 6, color: "#555", fillColor: "#999", fillOpacity: 0.9 })
                .bindTooltip(stop.name).addTo(this.map);
        });
        if (data.stop) {
            this.state.name = data.stop.name;
            this.state.radius = data.stop.radius;
            this.place(data.stop.lat, data.stop.lon);
            this.map.setView([data.stop.lat, data.stop.lon], 17);
        } else if (bounds.length) {
            this.map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
        }
        this.map.on("click", (event) => this.place(event.latlng.lat, event.latlng.lng));
    }

    place(lat, lon) {
        const L = window.L;
        if (!this.marker) {
            // A drawn pin, so the page needs no marker image files.
            const icon = L.divIcon({
                className: "",
                html: '<div style="width:22px;height:22px;border-radius:50% 50% 50% 0;transform:rotate(-45deg);background:#d9534f;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.5)"></div>',
                iconSize: [22, 22],
                iconAnchor: [11, 22],
            });
            this.marker = L.marker([lat, lon], { icon, draggable: true }).addTo(this.map);
            this.marker.on("dragend", () => {
                const at = this.marker.getLatLng();
                this.state.lat = at.lat;
                this.state.lon = at.lng;
            });
        } else {
            this.marker.setLatLng([lat, lon]);
        }
        this.state.lat = lat;
        this.state.lon = lon;
    }

    get coordinates() {
        return this.state.lat === null ? "" : `${this.state.lat.toFixed(6)}, ${this.state.lon.toFixed(6)}`;
    }

    async save() {
        this.state.error = null;
        if (this.state.lat === null) {
            this.state.error = _t("Click on the map to place the stop.");
            return;
        }
        this.state.saving = true;
        try {
            await this.rpc("/bus_tracking/stop/save", {
                route_id: this.routeId,
                stop_id: this.stopId,
                name: this.state.name,
                latitude: this.state.lat,
                longitude: this.state.lon,
                radius: this.state.radius,
            });
            this.env.services.action.doAction({ type: "ir.actions.act_window_close" });
        } catch (error) {
            this.state.error = error?.data?.message || _t("The stop could not be saved.");
            this.state.saving = false;
        }
    }

    cancel() {
        this.env.services.action.doAction({ type: "ir.actions.act_window_close" });
    }
}

registry.category("actions").add("bus_tracking.stop_picker", BusStopPicker);
