/* Checks that a stop name with HTML shows as text in the public route map (DEF-051).

    node qa/xss_tooltips.js

Loads the vendored Leaflet and the real static/src/portal/portal_map.js in jsdom (the one of the
tablet app's node_modules), with a stop whose name is an <img onerror> payload, opens every tooltip
and fails when the payload became an element. Exits with 1 on failure.
*/
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const { JSDOM } = require(require.resolve('jsdom', { paths: [path.join(ROOT, 'apps', 'conductor-tablet')] }));

const STATIC = path.join(ROOT, 'addons', 'bus_tracking', 'static');
const PAYLOAD = '<img src=x onerror="window.__xss=1">Parada';
const stops = [
    { lat: -1.24, lon: -78.62, name: PAYLOAD },
    { lat: -1.25, lon: -78.63, name: 'Huachi' },
];

const dom = new JSDOM(
    '<!doctype html><html><body><div id="bus-map" data-code="L1"></div></body></html>',
    { runScripts: 'outside-only', pretendToBeVisual: true },
);
const { window } = dom;
window.document.getElementById('bus-map').dataset.stops = JSON.stringify(stops);

window.eval(fs.readFileSync(path.join(STATIC, 'lib', 'leaflet', 'leaflet.js'), 'utf8'));
// Keep the map the script creates, to open its tooltips afterwards.
let map = null;
const createMap = window.L.map;
window.L.map = function () {
    map = createMap.apply(this, arguments);
    return map;
};
window.eval(fs.readFileSync(path.join(STATIC, 'src', 'portal', 'portal_map.js'), 'utf8'));

if (!map) {
    console.error('FAIL: portal_map.js did not create the map');
    process.exit(1);
}
let opened = 0;
map.eachLayer((layer) => {
    if (layer.getTooltip && layer.getTooltip()) {
        layer.openTooltip();
        opened += 1;
    }
});
const tooltips = [...window.document.querySelectorAll('.leaflet-tooltip')];
const texts = tooltips.map((t) => t.textContent);
const problems = [];
if (opened !== stops.length) problems.push(`opened ${opened} tooltips, expected ${stops.length}`);
if (window.document.querySelector('.leaflet-tooltip img')) problems.push('the stop name became an <img> element');
if (!texts.includes(PAYLOAD)) problems.push(`the stop name is not shown as text: ${JSON.stringify(texts)}`);

if (problems.length) {
    problems.forEach((p) => console.error('FAIL: ' + p));
    process.exit(1);
}
console.log(`OK: ${opened} stop tooltips show their name as text`);
