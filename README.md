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
| MBTA Bus (default off; routes at zoom 11.5+, stops at zoom 15+; commuter/express buses excluded) | MBTA V3 API |
| Station and bus stop popups: next two departures per line, grouped by direction | MBTA V3 `/predictions` (live) |
| Bluebikes stations (name, docks, live bikes and open docks on click) | Bluebikes GBFS (live) |
| Bike lanes (green), shared-use paths (teal), walking trails | MAPC AllTrails map service (image overlay, recolored in the browser) |
| Walk / bike network view (5, 10, 15 min) for a clicked member | `data/network.json` (OpenStreetMap street graph, see below) |
| Basemap | CARTO Positron / Dark Matter via MapLibre GL JS |

Transit toggles are nested: MBTA Transit > Subway & Silver Line / Commuter Rail / Bus / Ferry > individual lines. Organizations are drawn as rounded
squares (colored by sector, or by dues status once unlocked); stations and stops are circles.

The four tiles under the organization count show the share of organizations with a commuter rail station, subway station, bus stop or Bluebikes
station within 50, 250, 500 or 1,000 m of walking along streets and paths (the same street network as the network view, not straight-line).
The "i" button next to the title has a plain-text glossary of walking and biking speeds and conversions.

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

**Automatic (Airtable):** the *Sync from Airtable* GitHub Action runs every 6 hours (and on demand from the Actions tab). It reads the
2027 Dues table and the Organizations table (read-only), rebuilds `members.csv`, `members.js`, `members.geojson` and the encrypted
`dues.enc.js`, and commits only if something changed. Setup: create a read-only Airtable token and add two repository secrets,
`AIRTABLE_TOKEN` and `DUES_PASSWORD` (Settings > Secrets and variables > Actions). An organization appears on the map when it has a
2027 Dues record and a Latitude/Longitude on its Organizations record; warnings in the run log list any that are skipped.
`scripts/sync_airtable.py` has the field IDs it reads; to change the dues year set `DUES_YEAR`.

**Manual:** edit `data/members.csv` (org_id, name, address, city, lat, lng, sector, tma) and `data/dues_private.csv` (org_id, status, billed), then:

```
DUES_PASSWORD='your passphrase' python3 scripts/build_members_geojson.py
```

Requires `pip install cryptography`. The script keeps `dues.enc.js` untouched when the dues have not changed, and `data/meta.js` (the "last updated" date in the glossary) only changes when the data does.

## Extending it

External layers are declared in the `CONFIG` block and the `TREE` toggle structure in `index.html`; each is a MapLibre source + layer in
`addAllLayers()`. To add a layer (congestion, TAPA status, etc.), add its config, load it in `loadContext()`, and add a source and layer.
Members carry `org_id` (Airtable record ID) so other tables can be joined on it.

## Notes

- The page asks search engines not to index it (`noindex`), but that is not access control.
- MBTA, Bluebikes and MAPC layers need internet access. The MBTA API is rate limited for anonymous use; the page caches routes and stations in the browser for 24 hours.
