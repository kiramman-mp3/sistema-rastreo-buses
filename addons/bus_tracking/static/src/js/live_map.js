/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadCSS, loadJS } from "@web/core/assets";
import { Component, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";

const LEAFLET_CSS = "/bus_tracking/static/lib/leaflet/leaflet.css";
const LEAFLET_JS = "/bus_tracking/static/lib/leaflet/leaflet.js";

// Carto Positron: clean, unobtrusive tiles with high map-contrast
const CARTO_TILES = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png";
const TILE_OPTIONS = {
    maxZoom: 19,
    subdomains: "abcd",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
};

const REFRESH_MS = 10000;
const DEFAULT_CENTER = [-1.2417, -78.6167]; // Ambato baseline
const MOVEMENT_LABELS = { moving: "En movimiento", stopped: "Detenido" };

/**
 * Calculates the shortest angular difference (-180 to 180 degrees)
 * to prevent unsightly 360-degree spins during heading adjustments.
 */
function normalizeAngleDiff(target, current) {
    let diff = (target - current) % 360;
    if (diff > 180) diff -= 360;
    if (diff < -180) diff += 360;
    return diff;
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
            alertLabels: {},
            mapCenter: DEFAULT_CENTER,
            routeId: "",
            statusFilter: "all", // "all" | "moving" | "stopped" | "delayed" | "offline"
            searchQuery: "",
            pathKey: "",
            selectedId: this.props.action?.params?.vehicle_id || null,
            sidebarOpen: true,
            error: null,
            lastSyncFormatted: "Sincronizando...",
            secondsSinceSync: 0,
        });

        // Vehicle kinematics tracker: vehicleId -> state & marker record
        this.trackedBuses = new Map();
        this.fitted = false;
        this.animationFrame = null;
        this.routesRenderedKey = null;

        onMounted(async () => {
            await Promise.all([loadCSS(LEAFLET_CSS), loadJS(LEAFLET_JS)]);
            this.initMap();
            await this.refresh();

            // Polling timer
            this.pollTimer = setInterval(() => this.refresh(), REFRESH_MS);

            // Sync counter timer (every second for humanized time display)
            this.clockTimer = setInterval(() => {
                this.state.secondsSinceSync += 1;
                if (this.state.secondsSinceSync < 3) {
                    this.state.lastSyncFormatted = "En vivo";
                } else {
                    this.state.lastSyncFormatted = `Hace ${this.state.secondsSinceSync}s`;
                }
            }, 1000);

            // Start continuous kinematic render loop
            this.startKinematics();
        });

        onWillUnmount(() => {
            clearInterval(this.pollTimer);
            clearInterval(this.clockTimer);
            if (this.animationFrame) {
                cancelAnimationFrame(this.animationFrame);
            }
            if (this.map) {
                this.map.remove();
            }
        });
    }

    movementLabel(status) {
        return MOVEMENT_LABELS[status] || status;
    }

    get filteredVehicles() {
        let list = this.state.vehicles;
        if (this.state.routeId) {
            list = list.filter((v) => String(v.route_id) === String(this.state.routeId));
        }
        if (this.state.statusFilter === "moving") {
            list = list.filter((v) => v.connected && v.status === "moving");
        } else if (this.state.statusFilter === "stopped") {
            list = list.filter((v) => v.connected && v.status === "stopped");
        } else if (this.state.statusFilter === "delayed") {
            list = list.filter((v) => (v.alerts && v.alerts.length > 0) || (v.connected && v.status === "stopped"));
        } else if (this.state.statusFilter === "offline") {
            list = list.filter((v) => !v.connected);
        }

        if (this.state.searchQuery.trim()) {
            const q = this.state.searchQuery.toLowerCase().trim();
            list = list.filter((v) =>
                (v.name && v.name.toLowerCase().includes(q)) ||
                (v.plate && v.plate.toLowerCase().includes(q)) ||
                (v.driver && v.driver.toLowerCase().includes(q)) ||
                (v.route_name && v.route_name.toLowerCase().includes(q))
            );
        }
        return list;
    }

    get selectedVehicle() {
        return this.state.vehicles.find((v) => v.id === this.state.selectedId) || null;
    }

    get onlineCount() {
        return this.state.vehicles.filter((v) => v.connected).length;
    }

    get movingCount() {
        return this.state.vehicles.filter((v) => v.connected && v.status === "moving").length;
    }

    get delayedCount() {
        return this.state.vehicles.filter((v) => (v.alerts && v.alerts.length > 0)).length;
    }

    initMap() {
        const L = window.L;
        this.map = L.map(this.mapRef.el, {
            zoomControl: false,
            attributionControl: true,
        }).setView(DEFAULT_CENTER, 13);

        // Reposition zoom control to bottom right to avoid interfering with HUD
        L.control.zoom({ position: "bottomright" }).addTo(this.map);

        // Carto Positron Light Tiles
        L.tileLayer(CARTO_TILES, TILE_OPTIONS).addTo(this.map);

        this.routeLayer = L.layerGroup().addTo(this.map);
        this.trackLayer = L.layerGroup().addTo(this.map);
        this.busLayer = L.layerGroup().addTo(this.map);
    }

    startKinematics() {
        const step = (now) => {
            this.updateKinematics(now);
            this.animationFrame = requestAnimationFrame(step);
        };
        this.animationFrame = requestAnimationFrame(step);
    }

    /**
     * Kinematic interpolation engine:
     * Evaluates LERP for lat/lon and shortest-angle wrap for heading course.
     */
    updateKinematics(now) {
        for (const [id, bus] of this.trackedBuses) {
            if (!bus.marker) continue;

            const elapsed = now - bus.startTime;
            const progress = Math.min(Math.max(elapsed / bus.duration, 0), 1);
            // Ease-out quadratic curve for smooth natural deceleration
            const ease = 1 - (1 - progress) * (1 - progress);

            bus.currentLat = bus.startLat + (bus.targetLat - bus.startLat) * ease;
            bus.currentLon = bus.startLon + (bus.targetLon - bus.startLon) * ease;
            bus.currentCourse = bus.startCourse + (bus.targetCourse - bus.startCourse) * ease;

            bus.marker.setLatLng([bus.currentLat, bus.currentLon]);

            const el = bus.marker.getElement();
            if (el) {
                const arrowEl = el.querySelector(".o_bus_arrow");
                if (arrowEl) {
                    arrowEl.style.transform = `rotate(${bus.currentCourse}deg)`;
                }
            }
        }
    }

    async refresh() {
        try {
            const data = await this.rpc("/bus_tracking/live", {});
            this.state.vehicles = data.vehicles || [];
            this.state.routes = data.routes || [];
            this.state.alertLabels = data.alert_labels || {};
            this.state.mapCenter = data.map_center || DEFAULT_CENTER;
            this.state.error = null;
            this.state.secondsSinceSync = 0;
            this.state.lastSyncFormatted = "En vivo";

            this.syncVehicles(this.state.vehicles);
            this.drawRoutes();

            if (!this.fitted) {
                this.fitted = true;
                const sel = this.state.vehicles.find((v) => v.id === this.state.selectedId);
                if (sel) {
                    this.selectVehicle(sel);
                } else {
                    this.fitAll();
                }
            }
        } catch (e) {
            this.state.error = "No se pudieron sincronizar las posiciones con el servidor.";
        }
    }

    /**
     * Reconciles incoming vehicle positions without destroying DOM elements.
     */
    syncVehicles(vehicles) {
        const L = window.L;
        const currentIds = new Set(vehicles.map((v) => v.id));
        const now = performance.now();

        // 1. Remove vehicles that are no longer reported
        for (const [id, bus] of this.trackedBuses) {
            if (!currentIds.has(id)) {
                this.busLayer.removeLayer(bus.marker);
                this.trackedBuses.delete(id);
            }
        }

        // 2. Add or update vehicles
        for (const v of vehicles) {
            if (this.trackedBuses.has(v.id)) {
                const bus = this.trackedBuses.get(v.id);
                bus.startLat = bus.currentLat;
                bus.startLon = bus.currentLon;
                bus.targetLat = v.lat;
                bus.targetLon = v.lon;

                bus.startCourse = bus.currentCourse;
                const angleDelta = normalizeAngleDiff(v.course || 0, bus.currentCourse);
                bus.targetCourse = bus.currentCourse + angleDelta;

                bus.startTime = now;
                bus.duration = REFRESH_MS;
                bus.data = v;

                // Update visual badges on the existing marker
                const el = bus.marker.getElement();
                if (el) {
                    const pulse = el.querySelector(".o_bus_pulse");
                    if (pulse) {
                        pulse.className = `o_bus_pulse ${v.status === 'moving' && v.connected ? 'is-moving' : ''}`;
                    }
                    const pin = el.querySelector(".o_bus_pin");
                    if (pin) {
                        pin.className = `o_bus_pin ${v.connected ? 'is-connected' : 'is-disconnected'}`;
                    }
                }
            } else {
                // Create new marker instance
                const initialCourse = v.course || 0;
                const icon = this.createBusIcon(v, initialCourse);
                const marker = L.marker([v.lat, v.lon], { icon, zIndexOffset: 100 })
                    .on("click", () => this.selectVehicle(v));

                this.busLayer.addLayer(marker);

                this.trackedBuses.set(v.id, {
                    id: v.id,
                    marker,
                    startLat: v.lat,
                    startLon: v.lon,
                    currentLat: v.lat,
                    currentLon: v.lon,
                    targetLat: v.lat,
                    targetLon: v.lon,
                    startCourse: initialCourse,
                    currentCourse: initialCourse,
                    targetCourse: initialCourse,
                    startTime: now,
                    duration: REFRESH_MS,
                    data: v,
                });
            }
        }

        this.updateMarkerVisibility();
    }

    createBusIcon(v, course) {
        const L = window.L;
        const color = v.color || "#8B1D24";
        const movingClass = (v.status === 'moving' && v.connected) ? 'is-moving' : '';
        const connClass = v.connected ? 'is-connected' : 'is-disconnected';

        return L.divIcon({
            className: "o_bus_marker_container",
            iconSize: [42, 54],
            iconAnchor: [21, 27],
            html: `
                <div class="o_bus_marker_wrap" style="--unit-color: ${color};">
                    <div class="o_bus_pulse ${movingClass}"></div>
                    <div class="o_bus_pin ${connClass}">
                        <div class="o_bus_arrow" style="transform: rotate(${course}deg);">
                            <svg viewBox="0 0 24 24" class="o_bus_arrow_svg">
                                <polygon points="12,2 19,13 12,9 5,13"/>
                            </svg>
                        </div>
                        <div class="o_bus_core">
                            <i class="fa fa-bus"></i>
                        </div>
                    </div>
                    <div class="o_bus_badge_label">${this.escape(v.name)}</div>
                </div>
            `,
        });
    }

    updateMarkerVisibility() {
        const visibleIds = new Set(this.filteredVehicles.map((v) => v.id));
        for (const [id, bus] of this.trackedBuses) {
            const isVisible = visibleIds.has(id);
            const onMap = this.busLayer.hasLayer(bus.marker);
            if (isVisible && !onMap) {
                this.busLayer.addLayer(bus.marker);
            } else if (!isVisible && onMap) {
                this.busLayer.removeLayer(bus.marker);
            }
        }
    }

    drawRoutes() {
        const L = window.L;
        const currentKey = `${this.state.routeId}:${this.state.pathKey}:${this.state.routes.length}`;
        if (this.routesRenderedKey === currentKey) {
            return;
        }
        this.routesRenderedKey = currentKey;

        this.routeLayer.clearLayers();
        const rid = this.state.routeId;

        for (const route of this.state.routes) {
            if (rid && String(route.id) !== rid) {
                continue;
            }
            const color = route.color || "#8B1D24";
            const pts = (route.stops || []).map((s) => [s.lat, s.lon]);

            if (route.paths && route.paths.length) {
                route.paths.forEach((path, index) => {
                    const hidden = this.state.pathKey && this.state.pathKey !== `${route.id}:${index}`;
                    if (hidden) return;
                    const isSelected = this.state.pathKey === `${route.id}:${index}`;

                    L.polyline(path.points, {
                        color: color,
                        weight: isSelected ? 6 : 4,
                        opacity: isSelected ? 0.95 : 0.65,
                        lineJoin: "round",
                        lineCap: "round",
                    })
                    .bindTooltip(`<div class="o_bus_tip"><strong>${this.escape(path.name)}</strong> · ${path.km} km</div>`)
                    .on("click", () => this.selectPath(route.id, index))
                    .addTo(this.routeLayer);
                });
            } else if (pts.length > 1) {
                L.polyline(pts, {
                    color: color,
                    weight: 3,
                    opacity: 0.55,
                    dashArray: "6 6",
                }).addTo(this.routeLayer);
            }

            for (const s of (route.stops || [])) {
                if (s.radius && s.radius > 0) {
                    L.circle([s.lat, s.lon], {
                        radius: s.radius,
                        color: color,
                        weight: 1,
                        fillColor: color,
                        fillOpacity: 0.08,
                    }).addTo(this.routeLayer);
                }
                L.circleMarker([s.lat, s.lon], {
                    radius: 5,
                    color: "#ffffff",
                    weight: 2,
                    fillColor: color,
                    fillOpacity: 1,
                })
                .bindTooltip(`<div class="o_bus_tip"><strong>${this.escape(route.code)}</strong> · ${this.escape(s.name)}</div>`)
                .addTo(this.routeLayer);
            }
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
                (route.stops || []).forEach((s) => pts.push([s.lat, s.lon]));
                (route.paths || []).forEach((path) => path.points.forEach((p) => pts.push(p)));
            }
        }
        if (pts.length) {
            this.map.fitBounds(L.latLngBounds(pts), { padding: [60, 60], maxZoom: 16 });
        } else {
            this.map.setView(this.state.mapCenter, 13);
        }
    }

    selectPath(routeId, index) {
        this.state.pathKey = `${routeId}:${index}`;
        this.routesRenderedKey = null;
        this.drawRoutes();
        const route = this.state.routes.find((r) => r.id === routeId);
        if (route && route.paths[index]) {
            this.map.fitBounds(window.L.latLngBounds(route.paths[index].points), { padding: [50, 50] });
        }
    }

    resetPaths() {
        this.state.pathKey = "";
        this.routesRenderedKey = null;
        this.drawRoutes();
        this.fitAll();
    }

    onRouteChange(ev) {
        this.state.pathKey = "";
        this.state.routeId = ev.target.value;
        this.trackLayer.clearLayers();
        this.state.selectedId = null;
        this.routesRenderedKey = null;
        this.drawRoutes();
        this.updateMarkerVisibility();
        this.fitAll();
    }

    setStatusFilter(filter) {
        this.state.statusFilter = filter;
        this.updateMarkerVisibility();
    }

    toggleSidebar() {
        this.state.sidebarOpen = !this.state.sidebarOpen;
        setTimeout(() => {
            if (this.map) {
                this.map.invalidateSize();
            }
        }, 300);
    }

    async selectVehicle(v) {
        const L = window.L;
        this.state.selectedId = v.id;

        // Smooth pan with animation
        this.map.panTo([v.lat, v.lon], {
            animate: true,
            duration: 0.8,
        });

        this.trackLayer.clearLayers();
        try {
            const pts = await this.rpc("/bus_tracking/track", { vehicle_id: v.id, hours: 4 });
            if (pts.length > 1) {
                L.polyline(pts, {
                    color: v.color || "#8B1D24",
                    weight: 4,
                    opacity: 0.85,
                    dashArray: "4 4",
                }).addTo(this.trackLayer);
            }
        } catch (e) {
            // Track playback is optional
        }
    }

    openVehicleForm(vehicleId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "bus.vehicle",
            res_id: vehicleId,
            views: [[false, "form"]],
            target: "current",
        });
    }

    closeSelectedCard() {
        this.state.selectedId = null;
        this.trackLayer.clearLayers();
    }
}

registry.category("actions").add("bus_tracking.live_map", BusLiveMap);
