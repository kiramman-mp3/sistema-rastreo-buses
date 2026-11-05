/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";
import { _t } from "@web/core/l10n/translation";
import { Component, onMounted, onPatched, onWillUnmount, useRef, useState } from "@odoo/owl";

const CHART_JS = "/web/static/lib/Chart/Chart.js";
const REFRESH_MS = 30000;
// The palette of the brand: the garnet of the action, the yellow of a stop sign, the ink, and three line colours.
const INK = "#172025";
const GARNET = "#7A1A22";
const SIGNAL = "#FFC62B";
const OK = "#1D6B44";
const SERIES = ["#7A1A22", "#1E5560", "#9A4A12", "#3D4F8A", "#FFC62B", "#5A6F2E", "#6B4E7A", "#3E4C51"];
const GRID = "rgba(23, 32, 37, 0.08)";
// Lower is better for these: a rise is bad news.
const LOWER_IS_BETTER = new Set(["T3", "T5", "T8", "S3"]);
const CHART_REFS = [
    "chart_days", "chart_kinds", "chart_route_punctuality", "chart_route_compliance", "chart_route_delay",
    "chart_route_km", "chart_punctuality_days", "chart_buckets", "chart_stops", "chart_pareto", "chart_alert_days",
    "chart_route_alerts", "chart_perf",
];

function today() {
    const d = new Date();
    return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

function daysAgo(n) {
    const d = new Date();
    d.setDate(d.getDate() - n);
    return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 10);
}

export class BusDashboard extends Component {
    static template = "bus_tracking.Dashboard";

    setup() {
        this.rpc = useService("rpc");
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.refs = {};
        for (const name of CHART_REFS) {
            this.refs[name] = useRef(name);
        }
        this.charts = {};
        this.state = useState({
            tab: "summary",
            range: "30",
            from: daysAgo(29),
            to: today(),
            routeId: "",
            scope: "all",
            data: null,
            error: null,
            lastSync: null,
            now: Date.now(),
        });

        onMounted(async () => {
            await loadJS(CHART_JS);
            await this.load();
            this.poll = setInterval(() => {
                if (!document.hidden) {
                    this.load().catch(() => {});
                }
            }, REFRESH_MS);
            this.clock = setInterval(() => {
                this.state.now = Date.now();
            }, 1000);
        });
        onPatched(() => this.drawCharts());
        onWillUnmount(() => {
            clearInterval(this.poll);
            clearInterval(this.clock);
            this.destroyCharts();
        });
    }

    // ------------------------------------------------------------------ data
    async load() {
        const params = {
            scope: this.state.scope,
            route_ids: this.state.routeId ? [Number.parseInt(this.state.routeId, 10)] : null,
            compare: true,
        };
        if (this.state.range === "custom") {
            params.date_from = this.state.from;
            params.date_to = this.state.to;
        } else {
            params.days = Number.parseInt(this.state.range, 10);
        }
        try {
            this.state.data = await this.rpc("/bus_tracking/dashboard", params);
            this.state.error = null;
            this.state.lastSync = Date.now();
        } catch {
            this.state.error = _t("Could not update the indicators. Retrying every 30 seconds.");
        }
    }

    // ------------------------------------------------------------------ texts
    get tabs() {
        return [
            { key: "summary", label: _t("Summary") },
            { key: "routes", label: _t("Lines") },
            { key: "punctuality", label: _t("Punctuality") },
            { key: "trips", label: _t("Trips") },
            { key: "incidents", label: _t("Incidents") },
            { key: "quality", label: _t("System quality") },
            { key: "formulas", label: _t("Formulas") },
        ];
    }

    get canMeasure() {
        return this.state.data && this.state.data.can_manage;
    }

    get periodText() {
        const period = this.state.data && this.state.data.period;
        return period ? `${period.from} → ${period.to}` : "";
    }

    get scopeText() {
        return { all: _t("Real and simulated data"), real: _t("Real data only"), simulated: _t("Simulated data only") }[this.state.scope];
    }

    get syncText() {
        if (!this.state.lastSync) {
            return _t("Loading…");
        }
        const seconds = Math.round((this.state.now - this.state.lastSync) / 1000);
        return seconds < 3 ? _t("Live") : _t("Updated %s s ago").replace("%s", seconds);
    }

    routeSelected(route) {
        return `${route.id}` === `${this.state.routeId}`;
    }

    group(name) {
        return this.state.data.metrics.filter((m) => m.group === name);
    }

    statusText(metric) {
        return { good: _t("On target"), warn: _t("Watch"), bad: _t("Off target"), na: _t("No data"), info: _t("Count") }[metric.status];
    }

    flagsText(flags) {
        const names = {
            late: _t("Late"), early: _t("Early"), skipped: _t("Skipped stop"), incomplete: _t("Incomplete"),
            not_started: _t("Not started"), off_route: _t("Off route"), speeding: _t("Speeding"),
        };
        return flags ? flags.split(",").map((f) => names[f] || f).join(", ") : "—";
    }

    num(value, digits = 1) {
        if (value === null || value === undefined) {
            return "—";
        }
        return Number(value).toLocaleString(undefined, { maximumFractionDigits: digits });
    }

    valueText(metric) {
        return this.num(metric.value, metric.unit === "n" ? 0 : 1);
    }

    previousOf(metric) {
        const previous = this.state.data.previous;
        return previous ? previous[metric.code] : null;
    }

    deltaText(metric) {
        const before = this.previousOf(metric);
        if (metric.value === null || before === null || before === undefined) {
            return "";
        }
        const diff = metric.value - before;
        if (Math.abs(diff) < 0.05) {
            return "= 0";
        }
        return `${diff > 0 ? "▲" : "▼"} ${this.num(Math.abs(diff))}`;
    }

    deltaClass(metric) {
        const before = this.previousOf(metric);
        if (metric.value === null || before === null || before === undefined || Math.abs(metric.value - before) < 0.05) {
            return "same";
        }
        if (metric.code === "T6" || metric.code === "T7") {
            return "same";                      // closeness to the plan, not a direction
        }
        const better = LOWER_IS_BETTER.has(metric.code) ? metric.value < before : metric.value > before;
        return better ? "better" : "worse";
    }

    // ------------------------------------------------------------------ events
    setTab(key) {
        this.state.tab = key;
    }

    async onRange(ev) {
        this.state.range = ev.target.value;
        if (this.state.range !== "custom") {
            await this.load();
        }
    }

    async onFrom(ev) {
        this.state.from = ev.target.value;
        await this.load();
    }

    async onTo(ev) {
        this.state.to = ev.target.value;
        await this.load();
    }

    async onRoute(ev) {
        this.state.routeId = ev.target.value;
        await this.load();
    }

    async onScope(ev) {
        this.state.scope = ev.target.value;
        await this.load();
    }

    openTrip(id) {
        this.action.doAction({ type: "ir.actions.act_window", res_model: "bus.trip", res_id: id, views: [[false, "form"]] });
    }

    async measure() {
        const samples = await this.orm.call("bus.perf.sample", "action_measure", []);
        this.notification.add(_t("%s measurements taken.").replace("%s", samples), { type: "success" });
        await this.load();
    }

    async auditSync() {
        try {
            const audits = await this.orm.call("bus.sync.audit", "action_run", []);
            this.notification.add(_t("%s buses compared with Traccar.").replace("%s", audits), { type: "success" });
        } catch (error) {
            const message = (error && error.data && error.data.message) || _t("The audit could not run.");
            this.notification.add(message, { type: "warning" });
        }
        await this.load();
    }

    // ------------------------------------------------------------------ charts
    destroyCharts() {
        for (const chart of Object.values(this.charts)) {
            chart.destroy();
        }
        this.charts = {};
    }

    drawCharts() {
        if (!window.Chart || !this.state.data) {
            return;
        }
        this.destroyCharts();
        const specs = this.chartSpecs();
        for (const [name, config] of Object.entries(specs)) {
            const canvas = this.refs[name] && this.refs[name].el;
            if (canvas) {
                this.charts[name] = new window.Chart(canvas.getContext("2d"), config);
            }
        }
    }

    kindLabel(kind) {
        return (this.state.data.kind_labels || {})[kind] || kind;
    }

    baseOptions(extra = {}) {
        return Object.assign({
            responsive: true,
            maintainAspectRatio: false,
            legend: { display: false },
            animation: { duration: 250 },
            layout: { padding: { top: 4, right: 8 } },
            scales: {
                xAxes: [{ gridLines: { display: false }, ticks: { fontColor: INK, fontFamily: "Atkinson Hyperlegible, sans-serif" } }],
                yAxes: [{ gridLines: { color: GRID }, ticks: { beginAtZero: true, fontColor: INK, precision: 0 } }],
            },
        }, extra);
    }

    chartSpecs() {
        const data = this.state.data;
        const tab = this.state.tab;
        const specs = {};
        const routes = data.by_route;
        const days = data.by_day;
        const dayLabels = days.map((d) => d.date.slice(5));
        const kinds = data.incident_kinds;
        const kindColors = kinds.map((_k, i) => SERIES[i % SERIES.length]);

        if (tab === "summary") {
            specs.chart_days = {
                type: "bar",
                data: {
                    labels: dayLabels,
                    datasets: [
                        { label: _t("Done"), data: days.map((d) => d.done), backgroundColor: OK },
                        { label: _t("Incomplete"), data: days.map((d) => d.incomplete), backgroundColor: GARNET },
                    ],
                },
                options: this.baseOptions({
                    legend: { display: true, position: "bottom" },
                    scales: {
                        xAxes: [{ stacked: true, gridLines: { display: false } }],
                        yAxes: [{ stacked: true, gridLines: { color: GRID }, ticks: { beginAtZero: true, precision: 0 } }],
                    },
                }),
            };
        }
        if (tab === "summary" || tab === "incidents") {
            specs.chart_kinds = {
                type: "doughnut",
                data: { labels: kinds.map((k) => this.kindLabel(k.kind)), datasets: [{ data: kinds.map((k) => k.count), backgroundColor: kindColors, borderColor: "#FFFFFF" }] },
                options: { responsive: true, maintainAspectRatio: false, cutoutPercentage: 62, legend: { position: "right" } },
            };
        }
        if (tab === "routes") {
            const colors = routes.map((r) => r.color);
            const bar = (key, max) => ({
                type: "bar",
                data: { labels: routes.map((r) => r.code), datasets: [{ data: routes.map((r) => r[key]), backgroundColor: colors }] },
                options: this.baseOptions(max ? { scales: { xAxes: [{ gridLines: { display: false } }], yAxes: [{ gridLines: { color: GRID }, ticks: { beginAtZero: true, max } }] } } : {}),
            });
            specs.chart_route_punctuality = bar("punctuality", 100);
            specs.chart_route_compliance = bar("compliance", 100);
            specs.chart_route_delay = bar("delay");
            specs.chart_route_km = {
                type: "bar",
                data: {
                    labels: routes.map((r) => r.code),
                    datasets: [
                        { label: _t("Estimated"), data: routes.map((r) => r.est_km), backgroundColor: SIGNAL },
                        { label: _t("Driven"), data: routes.map((r) => r.real_km), backgroundColor: INK },
                    ],
                },
                options: this.baseOptions({ legend: { display: true, position: "bottom" } }),
            };
        }
        if (tab === "punctuality") {
            specs.chart_punctuality_days = {
                type: "line",
                data: {
                    labels: dayLabels,
                    datasets: [{ data: days.map((d) => d.punctuality), borderColor: GARNET, backgroundColor: "rgba(122,26,34,0.10)", lineTension: 0.25, pointRadius: 3, spanGaps: true }],
                },
                options: this.baseOptions({ scales: { xAxes: [{ gridLines: { display: false } }], yAxes: [{ gridLines: { color: GRID }, ticks: { beginAtZero: true, max: 100 } }] } }),
            };
            const bucketColors = [SIGNAL, OK, "#C98A00", "#B4531A", GARNET, "#4A0E14"];
            specs.chart_buckets = {
                type: "bar",
                data: { labels: data.delay_buckets.map((b) => b.label), datasets: [{ data: data.delay_buckets.map((b) => b.count), backgroundColor: bucketColors }] },
                options: this.baseOptions(),
            };
            specs.chart_stops = {
                type: "horizontalBar",
                data: {
                    labels: data.stop_delays.map((s) => `${s.route} · ${s.stop}`),
                    datasets: [{ data: data.stop_delays.map((s) => s.delay), backgroundColor: GARNET }],
                },
                options: this.baseOptions({
                    scales: {
                        xAxes: [{ gridLines: { color: GRID }, ticks: { beginAtZero: true } }],
                        yAxes: [{ gridLines: { display: false } }],
                    },
                }),
            };
        }
        if (tab === "incidents") {
            specs.chart_pareto = {
                type: "bar",
                data: {
                    labels: kinds.map((k) => this.kindLabel(k.kind)),
                    datasets: [
                        { type: "line", label: _t("Cumulative %"), data: kinds.map((k) => k.cumulative), yAxisID: "pct", borderColor: INK, backgroundColor: "transparent", lineTension: 0, pointRadius: 3 },
                        { label: _t("Incidents"), data: kinds.map((k) => k.count), yAxisID: "n", backgroundColor: GARNET },
                    ],
                },
                options: this.baseOptions({
                    legend: { display: true, position: "bottom" },
                    scales: {
                        xAxes: [{ gridLines: { display: false } }],
                        yAxes: [
                            { id: "n", position: "left", gridLines: { color: GRID }, ticks: { beginAtZero: true, precision: 0 } },
                            { id: "pct", position: "right", gridLines: { display: false }, ticks: { beginAtZero: true, max: 100 } },
                        ],
                    },
                }),
            };
            specs.chart_alert_days = {
                type: "bar",
                data: { labels: dayLabels, datasets: [{ data: days.map((d) => d.alerts), backgroundColor: SIGNAL }] },
                options: this.baseOptions(),
            };
            specs.chart_route_alerts = {
                type: "bar",
                data: { labels: routes.map((r) => r.code), datasets: [{ data: routes.map((r) => r.alerts), backgroundColor: routes.map((r) => r.color) }] },
                options: this.baseOptions(),
            };
        }
        if (tab === "quality") {
            const perf = data.perf_days;
            specs.chart_perf = {
                type: "line",
                data: {
                    labels: perf.map((p) => p.date.slice(5)),
                    datasets: [
                        { label: "p95", data: perf.map((p) => p.p95), borderColor: GARNET, backgroundColor: "transparent", lineTension: 0.25, pointRadius: 3 },
                        { label: _t("Median"), data: perf.map((p) => p.p50), borderColor: INK, backgroundColor: "transparent", lineTension: 0.25, pointRadius: 3 },
                    ],
                },
                options: this.baseOptions({ legend: { display: true, position: "bottom" } }),
            };
        }
        return specs;
    }
}

registry.category("actions").add("bus_tracking.dashboard", BusDashboard);
