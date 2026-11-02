/* Public site of Buses UTA.
   - Entrances: content is visible without script; with it, each part rises once as it enters.
   - The stop line: places the live buses between stops, remembers "my stop" on this phone and says
     how many stops the nearest bus has left. It counts stops, never minutes: no time is promised.
   - "How it works": the stage follows the statement in view.
   The route map (portal_map.js) listens to the same data instead of asking the server again. */
(function () {
    "use strict";

    var REFRESH_MS = 10000;
    var STALE_AFTER_S = 90;
    var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    var BUS_SVG = '<svg viewBox="0 0 20 20" width="18" height="18" aria-hidden="true" focusable="false">' +
        '<rect x="3" y="2" width="14" height="14" rx="3" fill="currentColor"/>' +
        '<rect x="5" y="4.5" width="10" height="5" rx="1" fill="#172025" opacity="0.55"/>' +
        '<circle cx="7" cy="12.5" r="1.3" fill="#172025" opacity="0.55"/>' +
        '<circle cx="13" cy="12.5" r="1.3" fill="#172025" opacity="0.55"/>' +
        '<rect x="5" y="16" width="2.5" height="2.5" rx="1" fill="currentColor"/>' +
        '<rect x="12.5" y="16" width="2.5" height="2.5" rx="1" fill="currentColor"/></svg>';

    function fmt(text, values) {
        return String(text || "").replace(/\{(\w+)\}/g, function (all, key) {
            return values[key] !== undefined ? values[key] : all;
        });
    }

    function el(tag, className, text) {
        var node = document.createElement(tag);
        if (className) { node.className = className; }
        if (text !== undefined) { node.textContent = text; }
        return node;
    }

    function readJSON(value, fallback) {
        try { return JSON.parse(value || ""); } catch (e) { return fallback; }
    }

    // ---------------------------------------------------------------- entrances
    var entering = document.querySelectorAll(".entra");
    if (!reduce && "IntersectionObserver" in window) {
        var seen = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add("visto");
                    seen.unobserve(entry.target);
                }
            });
        }, { rootMargin: "0px 0px -6% 0px" });
        entering.forEach(function (node) { seen.observe(node); });
    } else {
        entering.forEach(function (node) { node.classList.add("visto"); });
    }

    // ---------------------------------------------------------- how it works
    var stage = document.querySelector(".como-escenario");
    var steps = document.querySelectorAll(".como-pasos li");
    if (stage && steps.length && "IntersectionObserver" in window) {
        var follow = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (!entry.isIntersecting) { return; }
                steps.forEach(function (step) { step.classList.toggle("activo", step === entry.target); });
                stage.setAttribute("data-estado", entry.target.getAttribute("data-paso"));
            });
        }, { rootMargin: "-45% 0px -45% 0px" });
        steps.forEach(function (step) { follow.observe(step); });
        steps[0].classList.add("activo");
    }

    // ------------------------------------------------------------ the stop line
    document.querySelectorAll("[data-linea]").forEach(function (list) {
        var code = list.getAttribute("data-linea");
        var stops = readJSON(list.getAttribute("data-stops"), []);
        var t = readJSON(list.getAttribute("data-i18n"), {});
        var box = list.closest(".fragmento, .ruta-linea") || document;
        var summary = box.querySelector("[data-resumen]");
        var live = (box.querySelector && box.querySelector("[data-vivo]")) || document.querySelector("[data-vivo]");
        var empty = document.getElementById("bus-empty");
        var hint = summary ? summary.textContent : "";
        var key = "buses-uta:mi-parada:" + code;
        var mine = null;
        var buses = [];
        var lastOk = null;
        var failing = null;

        try {
            var saved = window.localStorage.getItem(key);
            if (saved !== null && !isNaN(parseInt(saved, 10)) && parseInt(saved, 10) < stops.length) {
                mine = parseInt(saved, 10);
            }
        } catch (e) { /* private mode: the choice simply is not remembered */ }

        // Every stop becomes a button: "this is where I wait".
        list.textContent = "";
        var rows = stops.map(function (name, index) {
            var li = el("li");
            var button = el("button", "parada");
            button.type = "button";
            button.setAttribute("data-mia", t.mine_tag || "");
            button.append(el("span", "punto"), el("span", "nombre", name));
            button.addEventListener("click", function () { choose(mine === index ? null : index); });
            li.appendChild(button);
            list.appendChild(li);
            return { li: li, button: button };
        });

        function choose(index) {
            mine = index;
            try {
                if (index === null) { window.localStorage.removeItem(key); } else { window.localStorage.setItem(key, String(index)); }
            } catch (e) { /* ignore */ }
            render();
        }

        function where(bus) {
            if (bus.at !== null && bus.at !== undefined) { return bus.at; }
            if (bus.after !== null && bus.after !== undefined) { return bus.after; }
            return null;
        }

        function place(bus) {
            if (bus.at !== null && bus.at !== undefined) { return fmt(t.bus_at, { a: stops[bus.at] }); }
            if (bus.after < stops.length - 1) { return fmt(t.bus_between, { a: stops[bus.after], b: stops[bus.after + 1] }); }
            return fmt(t.bus_at, { a: stops[bus.after] });
        }

        function answer() {
            if (mine === null) { return { text: hint, chosen: false }; }
            if (!buses.length) { return { text: t.no_buses, chosen: true }; }
            var best = null;
            buses.forEach(function (bus) {
                var index = where(bus);
                if (index === null) { return; }
                var atStop = bus.at !== null && bus.at !== undefined;
                var left = mine - index;
                // a bus that already left my stop is not coming to it
                if (left < 0 || (left === 0 && !atStop)) { return; }
                if (!best || left < best.left) { best = { bus: bus, left: left }; }
            });
            if (!best) {
                var placed = buses.some(function (bus) { return where(bus) !== null; });
                return { text: placed ? t.none_coming : t.position_unknown, chosen: true };
            }
            if (best.left === 0) { return { text: fmt(t.bus_at_mine, { bus: best.bus.name }), chosen: true }; }
            if (best.left === 1) { return { text: fmt(t.bus_one_stop, { bus: best.bus.name }), chosen: true }; }
            return { text: fmt(t.bus_n_stops, { bus: best.bus.name, n: best.left }), chosen: true };
        }

        function render() {
            list.querySelectorAll(".bus-en-linea").forEach(function (node) { node.remove(); });
            rows.forEach(function (row, index) {
                row.button.setAttribute("aria-pressed", mine === index ? "true" : "false");
            });
            buses.forEach(function (bus) {
                var index = where(bus);
                if (index === null || !rows[index]) { return; }
                var kind = bus.status === "moving" ? "" : (bus.status === "stopped" ? " detenido" : " sin-senal");
                var line = el("div", "bus-en-linea" + kind);
                var chip = el("span", "ficha");
                chip.innerHTML = BUS_SVG;
                var status = t["status_" + (bus.status === "moving" || bus.status === "stopped" ? bus.status : "offline")] || "";
                line.append(chip, el("span", "", bus.name + " · " + place(bus) + " · " + status));
                rows[index].li.appendChild(line);
            });
            if (summary) {
                var said = answer();
                summary.textContent = said.text;
                summary.classList.toggle("con-parada", said.chosen);
            }
            if (empty) { empty.hidden = buses.length > 0 || lastOk === null; }
            document.dispatchEvent(new CustomEvent("buses-uta:linea", {
                detail: { code: code, mine: mine, buses: buses, color: list.style.getPropertyValue("--c") },
            }));
        }

        // the map can choose a stop too
        document.addEventListener("buses-uta:elegir", function (event) {
            if (event.detail && event.detail.code === code) { choose(event.detail.index); }
        });

        function showAge() {
            if (!live) { return; }
            live.classList.remove("fresco", "viejo", "error");
            if (failing && (lastOk === null || Date.now() - lastOk > REFRESH_MS * 2)) {
                live.textContent = failing;
                live.classList.add("error");
                return;
            }
            if (lastOk === null) { return; }
            var secs = Math.round((Date.now() - lastOk) / 1000);
            if (secs < 3) {
                live.textContent = t.live;
                live.classList.add("fresco");
            } else if (secs < 60) {
                live.textContent = fmt(t.updated, { s: secs });
                live.classList.add("fresco");
            } else if (secs < STALE_AFTER_S) {
                live.textContent = fmt(t.updated_min, { m: Math.round(secs / 60) });
            } else {
                live.textContent = fmt(t.stale, { m: Math.round(secs / 60) });
                live.classList.add("viejo");
            }
        }

        var timer = null;
        function refresh() {
            fetch("/rutas/" + encodeURIComponent(code) + "/buses.json", { headers: { Accept: "application/json" } })
                .then(function (response) {
                    if (response.status === 429) { throw new Error("rate"); }
                    if (!response.ok) { throw new Error(String(response.status)); }
                    return response.json();
                })
                .then(function (data) {
                    buses = (data && data.buses) || [];
                    lastOk = Date.now();
                    failing = null;
                    render();
                    showAge();
                })
                .catch(function (error) {
                    failing = error && error.message === "rate" ? t.rate : t.update_error;
                    showAge();
                });
        }

        function start() {
            if (timer) { return; }
            refresh();
            timer = setInterval(refresh, REFRESH_MS);
        }

        function stop() {
            clearInterval(timer);
            timer = null;
        }

        render();
        start();
        setInterval(showAge, 1000);
        document.addEventListener("visibilitychange", function () {
            if (document.hidden) { stop(); } else { start(); }
        });
    });
}());
