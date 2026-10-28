(function () {
    "use strict";

    var el = document.getElementById("bus-map");
    if (!el || !window.L) {
        return;
    }
    var code = el.dataset.code;
    var color = el.dataset.color;
    var stops = JSON.parse(el.dataset.stops);
    var t = JSON.parse(el.dataset.i18n);
    var REFRESH_MS = 10000;

    var center = JSON.parse(el.dataset.center || "[-1.2417, -78.6167]");
    var map = window.L.map(el).setView(center, 13);
    window.L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: "&copy; OpenStreetMap contributors",
    }).addTo(map);

    var points = stops.map(function (s) { return [s.lat, s.lon]; });
    var paths = JSON.parse(el.dataset.paths || "[]");
    var pathLayers = [];
    var picker = document.getElementById("path-picker");
    var pathSelect = document.getElementById("path-select");
    function showPath(index) {
        // index -1 shows every variant; otherwise only that one, strongly drawn.
        pathLayers.forEach(function (layer, i) {
            var on = index < 0 || i === index;
            layer.setStyle({ opacity: on ? (index < 0 ? 0.6 : 0.95) : 0, weight: on ? (index < 0 ? 5 : 6) : 0 });
            layer.options.interactive = on;
        });
        pathSelect.value = String(index);
        if (index >= 0) {
            map.fitBounds(pathLayers[index].getBounds(), { padding: [40, 40] });
        } else {
            fit();
        }
    }
    if (paths.length) {
        // The real roads of the line; the points of the stops alone would draw a straight line.
        paths.forEach(function (path, i) {
            var layer = window.L.polyline(path.points, { color: color, weight: 5, opacity: 0.6, lineJoin: "round" })
                .bindTooltip(path.name + " · " + path.km + " km").addTo(map);
            layer.on("click", function () { showPath(i); });
            pathLayers.push(layer);
            var option = document.createElement("option");
            option.value = String(i);
            option.textContent = path.name + " · " + path.km + " km";
            pathSelect.appendChild(option);
            points = points.concat(path.points);
        });
        var all = document.createElement("option");
        all.value = "-1";
        all.textContent = t.path_all;
        pathSelect.insertBefore(all, pathSelect.firstChild);
        pathSelect.value = "-1";
        pathSelect.addEventListener("change", function () { showPath(parseInt(pathSelect.value, 10)); });
        document.getElementById("path-reset").addEventListener("click", function () { showPath(-1); });
        picker.hidden = false;
    } else if (points.length > 1) {
        window.L.polyline(points, { color: color, weight: 4, opacity: 0.55, dashArray: "6 8" }).addTo(map);
    }
    stops.forEach(function (s) {
        window.L.circleMarker([s.lat, s.lon], {
            radius: 6, color: "#ffffff", weight: 2, fillColor: color, fillOpacity: 1,
        }).bindTooltip(s.name).addTo(map);
    });
    var touched = false;
    function fit() {
        if (points.length) {
            map.fitBounds(window.L.latLngBounds(points), { padding: [40, 40], maxZoom: 16 });
        }
    }
    fit();
    // The container can still change size after this script runs (fonts, layout): refit until the
    // person moves the map themselves.
    ["mousedown", "touchstart", "wheel", "keydown"].forEach(function (name) {
        el.addEventListener(name, function () { touched = true; }, { passive: true });
    });
    if (window.ResizeObserver) {
        new ResizeObserver(function () {
            map.invalidateSize();
            if (!touched) { fit(); }
        }).observe(el);
    }
    window.addEventListener("load", function () {
        map.invalidateSize();
        if (!touched) { fit(); }
    });

    var busLayer = window.L.layerGroup().addTo(map);
    var statusEl = document.getElementById("bus-status");
    var listEl = document.getElementById("bus-list");
    var emptyEl = document.getElementById("bus-empty");
    var lastOk = null;

    function busIcon(bus) {
        var ring = bus.status === "moving" ? "#2a9d4b" : bus.status === "stopped" ? "#e0a800" : "#6c757d";
        return window.L.divIcon({
            className: "",
            iconSize: [34, 34],
            iconAnchor: [17, 17],
            html: '<div class="bus-marker" style="background:' + color + ";border-color:" + ring + '">' +
                '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">' +
                '<rect x="3" y="4" width="18" height="13" rx="3" fill="#fff"/>' +
                '<rect x="5" y="6" width="14" height="5" rx="1" fill="' + color + '"/>' +
                '<circle cx="8" cy="19" r="2" fill="#fff"/><circle cx="16" cy="19" r="2" fill="#fff"/></svg></div>',
        });
    }

    function render(buses) {
        busLayer.clearLayers();
        listEl.textContent = "";
        buses.forEach(function (bus) {
            var label = t["status_" + (bus.status === "moving" || bus.status === "stopped" ? bus.status : "offline")];
            window.L.marker([bus.lat, bus.lon], { icon: busIcon(bus), title: bus.name })
                .bindTooltip(bus.name + ": " + label).addTo(busLayer);
            var li = document.createElement("li");
            li.className = "bus-" + (bus.status === "moving" || bus.status === "stopped" ? bus.status : "offline");
            var name = document.createElement("strong");
            name.textContent = bus.name;
            var state = document.createElement("span");
            state.textContent = label;
            li.appendChild(name);
            li.appendChild(state);
            listEl.appendChild(li);
        });
        emptyEl.hidden = buses.length > 0;
    }

    function showAge() {
        if (lastOk === null) {
            return;
        }
        statusEl.textContent = t.updated.replace("{s}", Math.round((Date.now() - lastOk) / 1000));
    }

    function refresh() {
        fetch("/rutas/" + encodeURIComponent(code) + "/buses.json", { headers: { Accept: "application/json" } })
            .then(function (r) {
                if (!r.ok) { throw new Error(r.status); }
                return r.json();
            })
            .then(function (data) {
                render(data.buses);
                lastOk = Date.now();
                showAge();
            })
            .catch(function () {
                statusEl.textContent = t.update_error;
            });
    }

    refresh();
    setInterval(function () { if (!document.hidden) { refresh(); } }, REFRESH_MS);
    setInterval(showAge, 1000);
    document.addEventListener("visibilitychange", function () { if (!document.hidden) { refresh(); } });
}());
