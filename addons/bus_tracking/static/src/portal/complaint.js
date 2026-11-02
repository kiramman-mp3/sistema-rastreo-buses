(function () {
    "use strict";

    // Progressive enhancement for bus filtering by route
    var routeSelect = document.getElementById("complaint-route");
    var busSelect = document.getElementById("complaint-bus");
    if (!routeSelect || !busSelect) {
        return;
    }
    var options = Array.prototype.slice.call(busSelect.options).filter(function (o) { return o.value; });
    var emptyOption = busSelect.options[0];
    var chosen = busSelect.value;

    function refill() {
        var route = routeSelect.value;
        busSelect.textContent = "";
        busSelect.appendChild(emptyOption);
        options.forEach(function (option) {
            if (route && option.dataset.route === route) {
                option.textContent = option.dataset.name;
                busSelect.appendChild(option);
            }
        });
        busSelect.value = options.some(function (o) { return o.value === chosen && o.dataset.route === route; }) ? chosen : "";
        busSelect.disabled = !route;
    }

    busSelect.addEventListener("change", function () { chosen = busSelect.value; });
    routeSelect.addEventListener("change", refill);
    refill();
}());
