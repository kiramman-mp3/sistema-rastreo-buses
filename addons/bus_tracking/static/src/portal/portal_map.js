(function () {
    "use strict";

    var el = document.getElementById("bus-map");
    if (!el || !window.L) {
        return;
    }
    var code = el.dataset.code;
    var color = el.dataset.color || "#8B1D24";
    var stops = JSON.parse(el.dataset.stops || "[]");
    var t = JSON.parse(el.dataset.i18n || "{}");
    var REFRESH_MS = 10000;

    var center = JSON.parse(el.dataset.center || "[-1.2417, -78.6167]");
    var map = window.L.map(el).setView(center, 13);
    window.L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap</a> contributors',
    }).addTo(map);

    var points = stops.map(function (s) { return [s.lat, s.lon]; });
    var paths = JSON.parse(el.dataset.paths || "[]");
    var pathLayers = [];
    var picker = document.getElementById("path-picker");
    var pathSelect = document.getElementById("path-select");
    function showPath(index) {
        pathLayers.forEach(function (layer, i) {
            var on = index < 0 || i === index;
            layer.setStyle({ opacity: on ? (index < 0 ? 0.7 : 0.95) : 0, weight: on ? (index < 0 ? 5 : 6) : 0 });
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
        paths.forEach(function (path, i) {
            var layer = window.L.polyline(path.points, { color: color, weight: 5, opacity: 0.7, lineJoin: "round" })
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
        window.L.polyline(points, { color: color, weight: 5, opacity: 0.75, lineJoin: "round" }).addTo(map);
    }
    stops.forEach(function (s, index) {
        var stopIcon = window.L.divIcon({
            className: "stop-marker-container",
            iconSize: [24, 24],
            iconAnchor: [12, 12],
            html: '<div class="stop-badge-marker" style="background:' + color + '"><span>' + (index + 1) + '</span></div>',
        });
        window.L.marker([s.lat, s.lon], { icon: stopIcon })
            .bindTooltip((index + 1) + ". " + s.name, { direction: "top", offset: [0, -10] })
            .addTo(map);
    });
    var touched = false;
    function fit() {
        if (points.length) {
            map.fitBounds(window.L.latLngBounds(points), { padding: [40, 40], maxZoom: 16 });
        }
    }
    fit();
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
    var busMarkers = {};
    var statusEl = document.getElementById("bus-status");
    var listEl = document.getElementById("bus-list");
    var emptyEl = document.getElementById("bus-empty");
    var lastOk = null;

    function busIcon(bus) {
        var ring = bus.status === "moving" ? "#0D684D" : bus.status === "stopped" ? "#D97706" : "#DC2626";
        return window.L.divIcon({
            className: "bus-marker-container",
            iconSize: [38, 38],
            iconAnchor: [19, 19],
            html: '<div class="bus-marker" style="background:' + color + ';border-color:' + ring + '">' +
                '<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">' +
                '<rect x="4" y="4" width="16" height="13" rx="2.5" fill="#fff"/>' +
                '<rect x="6" y="6" width="12" height="5" rx="1" fill="' + color + '"/>' +
                '<circle cx="8" cy="18.5" r="1.5" fill="#fff"/><circle cx="16" cy="18.5" r="1.5" fill="#fff"/></svg></div>',
        });
    }

    function animateMarker(marker, targetLat, targetLon, duration) {
        var current = marker.getLatLng();
        var startLat = current.lat;
        var startLon = current.lng;
        if (Math.abs(startLat - targetLat) < 0.000001 && Math.abs(startLon - targetLon) < 0.000001) {
            return;
        }
        var startTime = window.performance ? window.performance.now() : Date.now();
        function frame(now) {
            var timeNow = now || (window.performance ? window.performance.now() : Date.now());
            var progress = Math.min((timeNow - startTime) / duration, 1);
            var ease = 1 - Math.pow(1 - progress, 2);
            var curLat = startLat + (targetLat - startLat) * ease;
            var curLon = startLon + (targetLon - startLon) * ease;
            marker.setLatLng([curLat, curLon]);
            if (progress < 1) {
                requestAnimationFrame(frame);
            }
        }
        requestAnimationFrame(frame);
    }

    function render(buses) {
        var seen = {};
        listEl.textContent = "";

        buses.forEach(function (bus) {
            seen[bus.name] = true;
            var label = t["status_" + (bus.status === "moving" || bus.status === "stopped" ? bus.status : "offline")];
            var tooltipText = bus.name + ": " + label;

            if (busMarkers[bus.name]) {
                var m = busMarkers[bus.name];
                animateMarker(m, bus.lat, bus.lon, 1200);
                if (m._lastStatus !== bus.status) {
                    m.setIcon(busIcon(bus));
                    m._lastStatus = bus.status;
                }
                m.setTooltipContent(tooltipText);
            } else {
                var marker = window.L.marker([bus.lat, bus.lon], { icon: busIcon(bus), title: bus.name });
                marker.bindTooltip(tooltipText, { direction: "top", offset: [0, -12] }).addTo(busLayer);
                marker._lastStatus = bus.status;
                busMarkers[bus.name] = marker;
            }

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

        // Clean up buses that are no longer active
        Object.keys(busMarkers).forEach(function (busName) {
            if (!seen[busName]) {
                busLayer.removeLayer(busMarkers[busName]);
                delete busMarkers[busName];
            }
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
