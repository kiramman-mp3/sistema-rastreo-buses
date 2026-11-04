/* Route map of the public site. It does not ask the server: site.js owns the data of the line and
   sends it here ("buses-uta:linea"), so the map and the stop list always show the same moment.
   Buses glide linearly to their new position over the refresh interval, so they never stop and
   start with a jolt; with reduced motion they jump. Tapping a stop on the map chooses it as "my stop". */
(function () {
    "use strict";

    var el = document.getElementById("bus-map");
    if (!el || !window.L) {
        return;
    }
    var L = window.L;
    var code = el.dataset.code;
    var color = el.dataset.color || "#7A1A22";
    var stops = JSON.parse(el.dataset.stops || "[]");
    var paths = JSON.parse(el.dataset.paths || "[]");
    var t = JSON.parse(el.dataset.i18n || "{}");
    var center = JSON.parse(el.dataset.center || "[-1.2417, -78.6167]");
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var GLIDE_MS = 5000;   // as long as the refresh: the bus never waits for the next position

    var map = L.map(el, { zoomControl: false, scrollWheelZoom: false }).setView(center, 13);
    L.control.zoom({ position: "bottomright" }).addTo(map);
    L.tileLayer(el.dataset.tiles || "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png?key=cb1_500h_1_2faaa5c6c3a1e1bb863b25cb", {
        maxZoom: 19,
        subdomains: "abcd",
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" rel="noopener">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions" rel="noopener">CARTO</a>',
    }).addTo(map);

    var points = stops.map(function (s) { return [s.lat, s.lon]; });
    paths.forEach(function (path) {
        L.polyline(path.points, { color: color, weight: 6, opacity: 0.9, lineJoin: "round" }).addTo(map);
        points = points.concat(path.points);
    });
    if (!paths.length && points.length > 1) {
        L.polyline(points, { color: color, weight: 6, opacity: 0.9, lineJoin: "round" }).addTo(map);
    }

    function stopIcon(mine) {
        return L.divIcon({
            className: "",
            iconSize: mine ? [28, 28] : [22, 22],
            iconAnchor: mine ? [14, 14] : [11, 11],
            html: '<span class="marcador-parada' + (mine ? " mia" : "") + '" style="--c:' + color + '"></span>',
        });
    }

    var stopMarkers = stops.map(function (stop, index) {
        var marker = L.marker([stop.lat, stop.lon], { icon: stopIcon(false), title: stop.name, keyboard: true })
            .bindTooltip(stop.name, { direction: "top", offset: [0, -12] })
            .addTo(map);
        marker.on("click", function () {
            document.dispatchEvent(new CustomEvent("buses-uta:elegir", { detail: { code: code, index: index } }));
        });
        return marker;
    });

    function fit() {
        if (points.length) {
            map.fitBounds(L.latLngBounds(points), { padding: [32, 32], maxZoom: 16 });
        }
    }
    fit();
    var touched = false;
    ["mousedown", "touchstart", "keydown"].forEach(function (name) {
        el.addEventListener(name, function () { touched = true; }, { passive: true });
    });
    if (window.ResizeObserver) {
        new ResizeObserver(function () {
            map.invalidateSize();
            if (!touched) { fit(); }
        }).observe(el);
    }

    var BUS_SVG = '<svg viewBox="0 0 20 20" width="16" height="16" aria-hidden="true" focusable="false">' +
        '<rect x="3" y="2" width="14" height="14" rx="3" fill="currentColor"/>' +
        '<rect x="5" y="4.5" width="10" height="5" rx="1" fill="#172025" opacity="0.55"/>' +
        '<rect x="5" y="16" width="2.5" height="2.5" rx="1" fill="currentColor"/>' +
        '<rect x="12.5" y="16" width="2.5" height="2.5" rx="1" fill="currentColor"/></svg>';

    function kind(bus) {
        return bus.status === "moving" ? "" : (bus.status === "stopped" ? " detenido" : " sin-senal");
    }

    function busIcon(bus) {
        var name = String(bus.name || "").replace(/[&<>"]/g, function (c) {
            return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
        });
        return L.divIcon({
            className: "",
            iconSize: [40, 40],
            iconAnchor: [20, 20],
            html: '<span class="marcador-bus' + kind(bus) + '">' +
                '<span class="rumbo" style="transform: rotate(' + (bus.course || 0) + 'deg)"></span>' +
                '<span class="cuerpo">' + BUS_SVG + '</span>' +
                '<span class="rotulo">' + name + "</span></span>",
        });
    }

    var buses = {};
    var frame = null;

    function glide() {
        var now = performance.now();
        var moving = false;
        Object.keys(buses).forEach(function (name) {
            var b = buses[name];
            var p = Math.min((now - b.start) / GLIDE_MS, 1);
            b.marker.setLatLng([b.from[0] + (b.to[0] - b.from[0]) * p, b.from[1] + (b.to[1] - b.from[1]) * p]);
            if (p < 1) { moving = true; }
        });
        // the loop stops as soon as nothing is moving
        frame = moving ? requestAnimationFrame(glide) : null;
    }

    document.addEventListener("buses-uta:linea", function (event) {
        var detail = event.detail || {};
        if (detail.code !== code) { return; }
        stopMarkers.forEach(function (marker, index) { marker.setIcon(stopIcon(index === detail.mine)); });

        var seen = {};
        (detail.buses || []).forEach(function (bus) {
            seen[bus.name] = true;
            var target = [bus.lat, bus.lon];
            var label = bus.name + ": " + (t["status_" + (bus.status === "moving" || bus.status === "stopped" ? bus.status : "offline")] || "");
            var known = buses[bus.name];
            if (!known) {
                var marker = L.marker(target, { icon: busIcon(bus), title: label, keyboard: false, zIndexOffset: 500 }).addTo(map);
                buses[bus.name] = { marker: marker, from: target, to: target, start: 0, status: bus.status };
                return;
            }
            known.marker.options.title = label;
            // options.title is only read when the marker is created: the element keeps the old one.
            var element = known.marker.getElement();
            if (element) { element.setAttribute("title", label); }
            if (known.status !== bus.status) {
                known.marker.setIcon(busIcon(bus));
                known.status = bus.status;
            } else {
                var rumbo = known.marker.getElement() && known.marker.getElement().querySelector(".rumbo");
                if (rumbo) { rumbo.style.transform = "rotate(" + (bus.course || 0) + "deg)"; }
            }
            var here = known.marker.getLatLng();
            known.from = [here.lat, here.lng];
            known.to = target;
            known.start = performance.now();
            if (reduce || document.hidden) {
                known.marker.setLatLng(target);
                known.from = target;
            }
        });
        Object.keys(buses).forEach(function (name) {
            if (!seen[name]) {
                map.removeLayer(buses[name].marker);
                delete buses[name];
            }
        });
        if (!reduce && !frame) { frame = requestAnimationFrame(glide); }
    });
}());
