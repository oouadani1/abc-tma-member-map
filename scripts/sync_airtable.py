"""Pull the map's member data from Airtable (read-only).

Reads the Dues table (Dues Year = 2027) and the Organizations table, then writes
  data/members.csv        public fields: org_id, name, address, city, lat, lng, sector, tma
  data/dues_private.csv   org_id, status, billed   (git-ignored; only ever built on the runner)

Run scripts/build_members_geojson.py afterwards to turn those into members.js / members.geojson / dues.enc.js.

Needs env AIRTABLE_TOKEN: a personal access token with only the data.records:read scope on this base.
Optional env: AIRTABLE_BASE (default below), DUES_YEAR (default 2027).
"""
import csv
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
BASE = os.environ.get("AIRTABLE_BASE", "appIZsPuAIMPYGmBr")
YEAR = os.environ.get("DUES_YEAR", "2027")

DUES_TABLE, ORG_TABLE = "tbl61I8v6tLzP0hvP", "tblPX8UDMBVaVekhg"
D_MEMBER, D_YEAR, D_BILLED, D_STATUS = "fldOwOLnMbnCXxlXO", "fldlmLGYcuWKNdeCX", "fld3snTd353IN1jtx", "fldcci6M5YHB9TMWI"
O_NAME, O_ADDR, O_CITY, O_LAT, O_LNG = "fldBfRgxvoOwkLRkd", "fldsErzdp0mhfOmfk", "fldzPBDNM75lZ0U8p", "fldomlRwH42bpntoU", "fldM6ZLw4sA7uH2ay"
O_SECTOR, O_TMA = "fldXhgTB6YAAMoSxa", "fldClknnSqo6p676Q"


def list_records(table, field_ids, formula=None):
    """All records of a table, with values keyed by field id. Retries on rate limits (5 requests/second per base)."""
    token = os.environ.get("AIRTABLE_TOKEN")
    if not token:
        raise SystemExit("AIRTABLE_TOKEN is not set")
    out, offset = [], None
    while True:
        q = [("returnFieldsByFieldId", "true")] + [("fields[]", f) for f in field_ids]
        if formula:
            q.append(("filterByFormula", formula))
        if offset:
            q.append(("offset", offset))
        req = urllib.request.Request(f"https://api.airtable.com/v0/{BASE}/{table}?" + urllib.parse.urlencode(q),
                                     headers={"Authorization": f"Bearer {token}"})
        for attempt in range(5):
            try:
                with urllib.request.urlopen(req, timeout=60) as r:
                    page = json.load(r)
                break
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt < 4:
                    time.sleep(2 * (attempt + 1))
                    continue
                raise SystemExit(f"Airtable error {e.code} reading {table}: {e.read().decode()[:200]}")
        out.extend(page["records"])
        offset = page.get("offset")
        if not offset:
            return out
        time.sleep(0.25)


def name_of(v):
    """single select values arrive as plain strings from the REST API; tolerate {name: ...} too"""
    return v.get("name") if isinstance(v, dict) else v


def fmt_num(v):
    return "" if v is None else (str(int(v)) if float(v).is_integer() else str(v))


def build_rows(dues_records, org_records):
    orgs = {r["id"]: r.get("fields", {}) for r in org_records}
    members, dues, seen, warnings = [], [], set(), []
    for d in dues_records:
        f = d.get("fields", {})
        links = f.get(D_MEMBER) or []
        if not links:
            warnings.append(f"dues record {d['id']} has no Member")
            continue
        oid = links[0]["id"] if isinstance(links[0], dict) else links[0]
        if oid in seen:
            warnings.append(f"organization {oid} has more than one {YEAR} dues record; using the first")
            continue
        o = orgs.get(oid)
        if o is None:
            warnings.append(f"organization {oid} not found")
            continue
        lat, lng = (o.get(O_LAT) or "").strip(), (o.get(O_LNG) or "").strip()
        try:
            float(lat), float(lng)
        except ValueError:
            warnings.append(f"{o.get(O_NAME, oid)} has no usable Latitude/Longitude; left off the map")
            continue
        seen.add(oid)
        members.append({"org_id": oid, "name": o.get(O_NAME, ""), "address": o.get(O_ADDR, ""), "city": o.get(O_CITY, ""),
                        "lat": lat, "lng": lng, "sector": name_of(o.get(O_SECTOR)) or "", "tma": name_of(o.get(O_TMA)) or "Unverified"})
        dues.append({"org_id": oid, "status": name_of(f.get(D_STATUS)) or "Not Billed", "billed": fmt_num(f.get(D_BILLED))})
    members.sort(key=lambda m: (m["name"].lower(), m["org_id"]))
    dues.sort(key=lambda m: m["org_id"])
    return members, dues, warnings


def write_csv(path, rows, cols):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main():
    dues_records = list_records(DUES_TABLE, [D_MEMBER, D_YEAR, D_BILLED, D_STATUS], formula=f"{{{D_YEAR}}}='{YEAR}'")
    org_records = list_records(ORG_TABLE, [O_NAME, O_ADDR, O_CITY, O_LAT, O_LNG, O_SECTOR, O_TMA])
    members, dues, warnings = build_rows(dues_records, org_records)
    for w in warnings:
        print("::warning::" + w)
    if len(members) < 20:  # guard against a bad token / filter wiping the map
        raise SystemExit(f"Only {len(members)} members found; refusing to overwrite the data files")
    write_csv(DATA / "members.csv", members, ["org_id", "name", "address", "city", "lat", "lng", "sector", "tma"])
    write_csv(DATA / "dues_private.csv", dues, ["org_id", "status", "billed"])
    print(f"{len(members)} members written from {len(dues_records)} {YEAR} dues records")


if __name__ == "__main__":
    main()
