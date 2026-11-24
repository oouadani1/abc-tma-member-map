"""Build the map's data files.

Inputs
  data/members.csv       public member fields (name, address, lat/lng, sector, TMA)
  data/dues_private.csv  org_id, status, billed   (NOT committed; see .gitignore)

Outputs
  data/members.geojson   public fields only (safe for GIS tools)
  data/members.js        same data for index.html
  data/dues.enc.js       dues, encrypted with a password (AES-256-GCM, PBKDF2-SHA256)

The password is read from the DUES_PASSWORD environment variable (or prompted). It is never
written to any file. Without dues_private.csv the encrypted file is skipped.

Usage
  DUES_PASSWORD='...' python3 scripts/build_members_geojson.py
"""
import atexit
import base64
import csv
import hashlib
import getpass
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ITERATIONS = 600_000


def _fingerprint():
    out = []
    for name in ("members.js", "dues.enc.js"):
        f = DATA / name
        out.append(hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else "")
    return out


_before = _fingerprint()


@atexit.register
def _stamp_updated():
    """data/meta.js holds the 'last updated' date shown in the map's glossary; it changes only when the data files change."""
    meta = DATA / "meta.js"
    if _fingerprint() != _before or not meta.exists():
        meta.write_text(f'window.DATA_UPDATED = "{datetime.now(timezone.utc).date().isoformat()}";\n', encoding="utf-8")


def num(v):
    return int(float(v)) if v not in ("", None) else None


def b64(b):
    return base64.b64encode(b).decode("ascii")


# ---- public data ----
features = []
with open(DATA / "members.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(r["lng"]), float(r["lat"])]},
            "properties": {
                "org_id": r["org_id"],
                "name": r["name"],
                "address": r["address"],
                "city": r["city"],
                "sector": r["sector"],
                "tma": r["tma"],
            },
        })

fc = {"type": "FeatureCollection", "features": features}
(DATA / "members.geojson").write_text(json.dumps(fc, indent=1), encoding="utf-8")
(DATA / "members.js").write_text(f'window.MEMBERS = {json.dumps(fc, separators=(",", ":"))};\n', encoding="utf-8")
print(f"members: {len(features)} (public fields only)")

# ---- encrypted dues ----
src = DATA / "dues_private.csv"
if not src.exists():
    print("dues_private.csv not found; dues.enc.js not rebuilt")
    raise SystemExit(0)

dues = {}
with open(src, newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        dues[r["org_id"]] = {"status": r["status"], "billed": num(r["billed"])}

missing = {x["properties"]["org_id"] for x in features} - set(dues)
if missing:
    raise SystemExit(f"dues_private.csv is missing {len(missing)} member(s): {sorted(missing)[:3]}")

password = os.environ.get("DUES_PASSWORD") or getpass.getpass("Dues password: ")
if len(password) < 12:
    raise SystemExit("Use a password of at least 12 characters.")

def unchanged(path, password, dues):
    """True when the existing encrypted file already holds exactly these dues (avoids a new commit on every run)."""
    try:
        blob = json.loads(path.read_text(encoding="utf-8").split("=", 1)[1].strip().rstrip(";"))
        k = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=base64.b64decode(blob["salt"]), iterations=blob["iter"]).derive(password.encode("utf-8"))
        return json.loads(AESGCM(k).decrypt(base64.b64decode(blob["iv"]), base64.b64decode(blob["ct"]), None)) == dues
    except Exception:
        return False


target = DATA / "dues.enc.js"
if target.exists() and unchanged(target, password, dues):
    print(f"dues: {len(dues)} records, unchanged (dues.enc.js kept)")
    raise SystemExit(0)

salt, iv = os.urandom(16), os.urandom(12)
key = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITERATIONS).derive(password.encode("utf-8"))
ct = AESGCM(key).encrypt(iv, json.dumps(dues, separators=(",", ":")).encode("utf-8"), None)  # ciphertext || 16-byte tag
blob = {"v": 1, "kdf": "PBKDF2-SHA256", "iter": ITERATIONS, "salt": b64(salt), "iv": b64(iv), "ct": b64(ct)}
(DATA / "dues.enc.js").write_text("window.DUES_ENC = " + json.dumps(blob) + ";\n", encoding="utf-8")

total = sum(d["billed"] or 0 for d in dues.values())
print(f"dues: {len(dues)} records, ${total:,} total, encrypted -> data/dues.enc.js")
