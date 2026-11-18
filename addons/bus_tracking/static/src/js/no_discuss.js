/** @odoo-module **/

import { registry } from "@web/core/registry";

// The system does not use the Discuss chat: once mail has put its chat and call buttons in the top bar, take them
// out. The activities button stays.
const HIDDEN = ["mail.MessagingMenuContainer", "mail.CallSystrayMenuContainer"];

registry.category("services").add("bus_tracking.no_discuss", {
    dependencies: ["systray_service"],
    start() {
        const systray = registry.category("systray");
        for (const key of HIDDEN) {
            if (systray.contains(key)) {
                systray.remove(key);
            }
        }
    },
});
