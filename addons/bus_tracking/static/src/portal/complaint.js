(function () {
    "use strict";

    // 1. Interactive Visual Reason Cards (Paso 1)
    var kindInput = document.getElementById("complaint-kind-input");
    var reasonCards = document.querySelectorAll(".reason-card");

    if (reasonCards.length && kindInput) {
        var initialKind = kindInput.value || "other";
        reasonCards.forEach(function (card) {
            if (card.dataset.kind === initialKind) {
                card.classList.add("active");
            }
            card.addEventListener("click", function () {
                reasonCards.forEach(function (c) { c.classList.remove("active"); });
                card.classList.add("active");
                kindInput.value = card.dataset.kind;
            });
        });
    }

    // 2. Progressive enhancement for bus filtering by route
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
