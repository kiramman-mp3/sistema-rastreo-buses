/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadCSS, loadJS } from "@web/core/assets";
import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";

const LEAFLET_CSS = "/bus_tracking/static/lib/leaflet/leaflet.css";
const LEAFLET_JS = "/bus_tracking/static/lib/leaflet/leaflet.js";
const TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";

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
        L.tileLayer(TILES, { maxZoom: 19, attribution: "&copy; OpenStreetMap contributors" }).addTo(this.map);
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
            this.marker = L.marker([lat, lon], { draggable: true }).addTo(this.map);
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
            this.state.error = "Haz clic en el mapa para elegir el punto de la parada.";
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
            this.state.error = error?.data?.message || "No se pudo guardar la parada.";
            this.state.saving = false;
        }
    }

    cancel() {
        this.env.services.action.doAction({ type: "ir.actions.act_window_close" });
    }
}

registry.category("actions").add("bus_tracking.stop_picker", BusStopPicker);
