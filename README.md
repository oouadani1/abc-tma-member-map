# ABC TMA Member Map

Lightweight static map of TMA member properties over MBTA transit and Bluebikes. No build step for viewing, no API keys.
It opens on locations only. Dues sit in a collapsed, password-protected section.

## View it

Double-click `index.html`, or serve the folder (`python3 -m http.server`). For hosting, upload `index.html` and the `data` folder
(`members.js`, `dues.enc.js`; the other `data` files are optional). The dues unlock needs the page to be on https or opened locally.

## What is on the map

| Layer | Source |
|---|---|
| Members (62), colored by sector or TMA, sized by sq ft | `data/members.js` (public fields only) |
| Dues status / amounts (unlock with password) | `data/dues.enc.js` (encrypted) |
| MBTA rapid transit + commuter rail stations | MassGIS/MBTA files in the `ma-bikeshare-coverage` repo (live from GitHub) |
| MBTA rapid transit lines | MBTA V3 API `/shapes` (live) |
| Bluebikes stations | Bluebikes GBFS (live) |
| Basemap | CARTO Positron / Dark Matter via MapLibre GL JS |

Popups show nearest rapid transit station and nearest Bluebikes station (straight-line meters). The panel counts members within
800 m of rapid transit and 400 m of Bluebikes. Walkshed rings are plain circles, not street-network walksheds.

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

All external layers are entries in the `CONFIG` block in `index.html`, each a MapLibre source + layer in `addAllLayers()`. To add a layer
(GTFS stops/routes, congestion, TAPA status, bus stops), add a URL to `CONFIG.sources`, fetch it in `loadContext()`, and add a source and
layer. Members carry `org_id` (Airtable record ID) so other tables can be joined on it.

## Notes

- The page asks search engines not to index it (`noindex`), but that is not access control.
- Layers read from GitHub, MBTA and Bluebikes need internet access. To work offline, save those files into `data/` and point `CONFIG.sources` at them.
