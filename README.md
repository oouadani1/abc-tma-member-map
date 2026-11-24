# ABC TMA Member Map

Lightweight static map of TMA member properties over MBTA transit and Bluebikes. No build step for viewing, no API keys.
It opens on locations only. Dues sit in a collapsed, password-protected section.

## View it

Double-click `index.html`, or serve the folder (`python3 -m http.server`). For hosting, upload `index.html` and the `data` folder
(`members.js`, `dues.enc.js`; the other `data` files are optional). The dues unlock needs the page to be on https or opened locally.

## What is on the map

| Layer | Source |
|---|---|
| Members (62), colored by sector (Airtable's sector colors) | `data/members.js` (public fields only) |
| Dues status / amounts (unlock with password) | `data/dues.enc.js` (encrypted) |
| MBTA rapid transit lines (Red, Orange, Blue, Green B-E, Mattapan, Silver SL1-SL5/SLW) | MBTA V3 API canonical route patterns and shapes (live, cached 24 h in the browser) |
| MBTA Commuter Rail ("Purple Line") lines and stations | MBTA V3 API (live) |
| MBTA Ferry (default off) | MBTA V3 API |
| MBTA Bus (default off; routes at zoom 11.5+, stops load on demand at zoom 15+) | MBTA V3 API |
| Station and bus stop popups: next two departures per line, grouped by direction | MBTA V3 `/predictions` (live) |
| Bluebikes stations (name, docks, live bikes and open docks on click) | Bluebikes GBFS (live) |
| Bike lanes (green), shared-use paths (teal), walking trails | MAPC AllTrails map service (image overlay, recolored in the browser) |
| Walk / bike network view (5, 10, 15 min) for a clicked member | `data/network.json` (OpenStreetMap street graph, see below) |
| Basemap | CARTO Positron / Dark Matter via MapLibre GL JS |

Transit toggles are nested: MBTA Transit > Subway & Silver Line / Commuter Rail / Bus / Ferry > individual lines. Parent checkboxes switch their
children on or off and show a partial state when only some are on. Popups on members show nearest rapid transit and Bluebikes station
(straight-line meters). The panel counts members within 500 m of a subway station and 250 m of a Bluebikes station (straight-line; 80 m is about a minute of walking). The member popup also lists the nearest bus stop and the routes serving it.

## Network view (walk / bike)

Clicking a member highlights the streets and paths reachable within 5, 10 or 15 minutes (walk 4.8 km/h, bike 15 km/h) in one solid color. Shortest paths run in the browser on `data/network.json`, a compact street graph from OpenStreetMap (study area = members + 3.9 km).
The bike network uses any street, path or cycleway that allows bikes, not only marked bike lanes. One-way streets are ignored, so bike reach is slightly optimistic.

Build or refresh the graph: GitHub > Actions > **Build street network** > Run workflow. It downloads the Massachusetts OSM extract, cuts
the study area, runs `scripts/build_network.py`, and commits `data/network.json`. Re-run it if members are added far outside the current area.

## How the dues protection works

Dues are encrypted with AES-256-GCM, using a key derived from the password (PBKDF2-SHA256, 600,000 iterations). The page decrypts in the
browser only after the correct password is entered. Without it, `dues.enc.js` is unreadable and the page contains no dues data.

- The password is never stored in any file. It is supplied when you build.
- `data/dues_private.csv` (plaintext dues) is git-ignored. Keep it out of the repo and off the web host.
- This protects against casual viewing and view-source. A weak or guessable password can still be cracked offline from the encrypted file.
  Use a long passphrase, and change it (rebuild) if it is ever shared widely or someone leaves.
- Contact data (names, emails) is not in this project at all.

## Refresh the data

Edit `data/members.csv` (public fields) and `data/dues_private.csv` (org_id, status, billed), then:

```
DUES_PASSWORD='your passphrase' python3 scripts/build_members_geojson.py
```

This regenerates `members.geojson` (for GIS tools; public fields only), `members.js`, and `dues.enc.js`. Requires `pip install cryptography`.

## Extending it

External layers are declared in the `CONFIG` block and the `TREE` toggle structure in `index.html`; each is a MapLibre source + layer in
`addAllLayers()`. To add a layer (congestion, TAPA status, etc.), add its config, load it in `loadContext()`, and add a source and layer.
Members carry `org_id` (Airtable record ID) so other tables can be joined on it.

## Notes

- The page asks search engines not to index it (`noindex`), but that is not access control.
- MBTA, Bluebikes and MAPC layers need internet access. The MBTA API is rate limited for anonymous use; the page caches routes and stations in the browser for 24 hours.
