/** @odoo-module **/

import { registry } from "@web/core/registry";
import { loadCSS, loadJS } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onMounted, onWillUnmount, useRef } from "@odoo/owl";

const LEAFLET_CSS = "/bus_tracking/static/lib/leaflet/leaflet.css";
const LEAFLET_JS = "/bus_tracking/static/lib/leaflet/leaflet.js";
const CHART_JS = "/web/static/lib/Chart/Chart.js";
const TILES = "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png?key=cb1_500h_1_2faaa5c6c3a1e1bb863b25cb";
const TILE_OPTIONS = {
    maxZoom: 19,
    subdomains: "abcd",
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
};
// The palette of the panel: the route in blue-teal, what the bus did in ink, the infraction in garnet.
const ROUTE = "#1E5560";
const TRACK = "#3E4C51";
const INFRACTION = "#B3261E";
const LIMIT = "#C98A00";
const STOP_COLORS = { skipped: "#B3261E", late: "#C98A00", on_time: "#1D6B44", early: "#1D6B44", pending: "#8A9499" };

export function escapeHtml(text) {
    return String(text ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/** Parse the evidence of a fine; anything that is not an object is no evidence. */
export function parseEvidence(text) {
    try {
        const value = JSON.parse(text || "{}");
        return value && typeof value === "object" && !Array.isArray(value) ? value : {};
    } catch {
        return {};
    }
}

/** Runs of consecutive flagged points of the track: the stretches of the infraction. */
export function flaggedRuns(track) {
    const runs = [];
    let current = [];
    for (const point of track || []) {
        if (point[4]) {
            current.push(point);
        } else if (current.length) {
            runs.push(current);
            current = [];
        }
    }
    if (current.length) {
        runs.push(current);
    }
    return runs;
}

/** Metres per screen pixel at a latitude and zoom (Web Mercator tiles of 256 px). */
export function metersPerPixel(lat, zoom) {
    return (40075016.686 * Math.cos((lat * Math.PI) / 180)) / Math.pow(2, zoom + 8);
}

function localTime(iso) {
    const when = new Date(iso);
    return Number.isNaN(when.getTime()) ? "" : when.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

export class FineEvidence extends Component {
    static template = "bus_tracking.FineEvidence";
    static props = { ...standardFieldProps };
    static supportedTypes = ["text"];

    setup() {
        this.mapRef = useRef("map");
        this.chartRef = useRef("chart");
        onMounted(async () => {
            await loadCSS(LEAFLET_CSS);
            await loadJS(LEAFLET_JS);
            if (this.showChart) {
                await loadJS(CHART_JS);
            }
            this.draw();
        });
        onWillUnmount(() => {
            if (this.map) {
                this.map.remove();
            }
            if (this.chart) {
                this.chart.destroy();
            }
        });
    }

    get evidence() {
        return parseEvidence(this.props.value);
    }

    get rule() {
        return this.props.record.data.rule;
    }

    get hasMap() {
        const e = this.evidence;
        return Boolean((e.track && e.track.length) || (e.route && e.route.length) || e.focus);
    }

    get showChart() {
        const e = this.evidence;
        return ["speeding", "long_stop"].includes(this.rule) && e.track && e.track.length > 1;
    }

    get legend() {
        const items = [
            { color: ROUTE, label: _t("Route") },
            { color: TRACK, label: _t("What the bus did") },
            { color: INFRACTION, label: _t("The infraction") },
        ];
        if (this.evidence.corridor_m) {
            items.splice(1, 0, { color: "rgba(30, 85, 96, 0.18)", label: _t("Allowed corridor (%s m)").replace("%s", this.evidence.corridor_m) });
        }
        return items;
    }

    draw() {
        if (this.hasMap && this.mapRef.el && window.L) {
            this.drawMap();
        }
        if (this.showChart && this.chartRef.el && window.Chart) {
            this.drawChart();
        }
    }

    drawMap() {
        const L = window.L;
        const e = this.evidence;
        const map = L.map(this.mapRef.el, { zoomControl: true, scrollWheelZoom: false });
        this.map = map;
        L.tileLayer(this.props.record.data.map_tile_url || TILES, TILE_OPTIONS).addTo(map);
        const bounds = [];
        const focusBounds = [];

        if (e.route && e.route.length > 1) {
            if (e.corridor_m) {
                // the corridor is drawn as a wide line whose width follows the zoom, so it stays in metres
                const corridor = L.polyline(e.route, { color: ROUTE, opacity: 0.18, weight: 10, lineCap: "round", lineJoin: "round" }).addTo(map);
                const resize = () => {
                    const pixels = (2 * e.corridor_m) / metersPerPixel(map.getCenter().lat, map.getZoom());
                    corridor.setStyle({ weight: Math.max(2, Math.min(pixels, 400)) });
                };
                map.on("zoomend", resize);
                this.resizeCorridor = resize;
            }
            L.polyline(e.route, { color: ROUTE, weight: 4, opacity: 0.85 }).addTo(map);
            bounds.push(...e.route);
        }
        for (const stop of e.stops || []) {
            const color = STOP_COLORS[stop.status] || STOP_COLORS.pending;
            L.circle([stop.lat, stop.lon], { radius: stop.radius || 50, color, weight: 2, fillOpacity: 0.15 })
                .bindTooltip(escapeHtml(stop.name))
                .addTo(map);
        }
        const track = e.track || [];
        if (track.length > 1) {
            L.polyline(track.map((p) => [p[1], p[2]]), { color: TRACK, weight: 3, opacity: 0.7, dashArray: "4 4" }).addTo(map);
            bounds.push(...track.map((p) => [p[1], p[2]]));
        }
        for (const run of flaggedRuns(track)) {
            const line = run.map((p) => [p[1], p[2]]);
            if (line.length > 1) {
                L.polyline(line, { color: INFRACTION, weight: 6, opacity: 0.9 }).addTo(map);
            }
            for (const point of run) {
                L.circleMarker([point[1], point[2]], { radius: 4, color: INFRACTION, fillColor: INFRACTION, fillOpacity: 1, weight: 1 })
                    .bindTooltip(`${escapeHtml(localTime(point[0]))} · ${escapeHtml(Math.round(point[3]))} km/h`)
                    .addTo(map);
            }
            const first = run[0];
            const last = run[run.length - 1];
            L.marker([first[1], first[2]], { title: _t("Start"), alt: _t("Start") })
                .bindTooltip(`${escapeHtml(_t("Start"))} · ${escapeHtml(localTime(first[0]))}`)
                .addTo(map);
            if (last !== first) {
                L.marker([last[1], last[2]], { title: _t("End"), alt: _t("End"), opacity: 0.75 })
                    .bindTooltip(`${escapeHtml(_t("End"))} · ${escapeHtml(localTime(last[0]))}`)
                    .addTo(map);
            }
            focusBounds.push(...line);
        }
        if (e.focus && e.focus.lat !== undefined) {
            L.circle([e.focus.lat, e.focus.lon], { radius: e.focus.radius || 40, color: INFRACTION, weight: 3, fillOpacity: 0.1 }).addTo(map);
            focusBounds.push([e.focus.lat, e.focus.lon]);
        }
        const target = focusBounds.length ? focusBounds : bounds;
        if (target.length) {
            map.fitBounds(L.latLngBounds(target).pad(target === focusBounds ? 0.6 : 0.05), { maxZoom: 17 });
        } else {
            map.setView([-1.2417, -78.6167], 13);
        }
        if (this.resizeCorridor) {
            this.resizeCorridor();
        }
        // The form may lay out after the map: measure again once the browser painted it.
        setTimeout(() => map.invalidateSize(), 50);
    }

    drawChart() {
        const e = this.evidence;
        const track = e.track || [];
        const labels = track.map((p) => localTime(p[0]));
        const datasets = [{
            label: _t("Speed (km/h)"),
            data: track.map((p) => p[3]),
            borderColor: TRACK,
            backgroundColor: "rgba(62, 76, 81, 0.08)",
            pointBackgroundColor: track.map((p) => (p[4] ? INFRACTION : TRACK)),
            pointRadius: track.map((p) => (p[4] ? 4 : 2)),
            lineTension: 0.15,
        }];
        const chart = e.chart || {};
        if (chart.limit) {
            datasets.push({ label: _t("Limit %s km/h").replace("%s", chart.limit), data: track.map(() => chart.limit), borderColor: LIMIT, borderDash: [6, 4], pointRadius: 0, fill: false });
        }
        if (chart.threshold) {
            datasets.push({ label: _t("Fined above %s km/h").replace("%s", chart.threshold), data: track.map(() => chart.threshold), borderColor: INFRACTION, borderDash: [2, 3], pointRadius: 0, fill: false });
        }
        this.chart = new window.Chart(this.chartRef.el.getContext("2d"), {
            type: "line",
            data: { labels, datasets },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: { duration: 0 },
                legend: { display: true, position: "bottom" },
                scales: {
                    xAxes: [{ gridLines: { display: false }, ticks: { maxTicksLimit: 8 } }],
                    yAxes: [{ ticks: { beginAtZero: true }, scaleLabel: { display: true, labelString: "km/h" } }],
                },
            },
        });
    }
}

registry.category("fields").add("bus_fine_evidence", FineEvidence);
