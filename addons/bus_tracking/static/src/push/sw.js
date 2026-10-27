/* Service worker for the staff push notifications. It only reacts to push messages. */

self.addEventListener("install", function () {
    self.skipWaiting();
});

self.addEventListener("activate", function (event) {
    event.waitUntil(self.clients.claim());
});

self.addEventListener("push", function (event) {
    var data = {};
    try {
        data = event.data ? event.data.json() : {};
    } catch (error) {
        data = { body: event.data ? event.data.text() : "" };
    }
    event.waitUntil(self.registration.showNotification(data.title || "Buses", {
        body: data.body || "",
        tag: data.tag || "bus-tracking",
        renotify: true,
        data: { url: data.url || "/" },
    }));
});

self.addEventListener("notificationclick", function (event) {
    event.notification.close();
    var target = "/";
    try {
        var url = new URL((event.notification.data && event.notification.data.url) || "/", self.location.origin);
        if (url.origin === self.location.origin) {     // never navigate to another site
            target = url.href;
        }
    } catch (error) {
        target = "/";
    }
    event.waitUntil(self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(function (windows) {
        for (var i = 0; i < windows.length; i++) {
            if (windows[i].url === target && "focus" in windows[i]) {
                return windows[i].focus();
            }
        }
        return self.clients.openWindow(target);
    }));
});
