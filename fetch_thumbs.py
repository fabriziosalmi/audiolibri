#!/usr/bin/env python3
"""Fetch YouTube thumbnails to a local cache and derive the WebP variants the
site actually serves, so the visitor's browser never contacts i.ytimg.com.

Build-time only. Deterministic and idempotent:
- reads the video ids from augmented.json (the url field);
- downloads the best available thumbnail per id (maxresdefault -> hqdefault ->
  mqdefault), first HTTP 200 image wins, into .cache/thumbs/<vid>.jpg written
  atomically (temp file + os.replace);
- skips ids already cached with a plausible size; --force refetches;
- derives assets/thumbs/<vid>-320.webp and <vid>-640.webp (quality 80, EXIF
  stripped, no upscaling beyond the source); skips ids whose outputs already
  exist unless --force;
- ids without any usable thumbnail get no per-id file: the templates fall back to
  the local placeholder assets/thumbs/placeholder-{320,640}.webp (generated here);
- writes build/reports/thumbs.json.

No third-party runtime code is added: this only produces static assets the site
serves from its own origin.
"""
import argparse
import concurrent.futures
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parent
DATA = ROOT / "augmented.json"
CACHE = ROOT / ".cache" / "thumbs"
OUT = ROOT / "assets" / "thumbs"
REPORT = ROOT / "build" / "reports" / "thumbs.json"

UA = "audiolibri.org-thumb-fetch/1.0 (+https://audiolibri.org)"
RES_ORDER = ("maxresdefault", "hqdefault", "mqdefault")
WIDTHS = (320, 640)
TIMEOUT = 15
MIN_BYTES = 1000  # below this a ytimg 200 is the grey "no thumbnail" filler, not a real image
RETRY_CODES = (429, 500, 502, 503, 504)


def video_id(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|embed/)([\w-]{11})", url or "")
    return m.group(1) if m else ""


def load_vids() -> list:
    d = json.loads(DATA.read_text())
    seen, out = set(), []
    for b in d.values():
        v = video_id(b.get("url", ""))
        if v and v not in seen:
            seen.add(v)
            out.append(v)
    return out


def cache_file(vid: str):
    p = CACHE / f"{vid}.jpg"
    return p if (p.exists() and p.stat().st_size >= MIN_BYTES) else None


def outputs_exist(vid: str) -> bool:
    return all((OUT / f"{vid}-{w}.webp").exists() for w in WIDTHS)


def fetch_one(vid: str, force: bool):
    if not force and cache_file(vid):
        return (vid, "cached", None)
    for res in RES_ORDER:
        url = f"https://i.ytimg.com/vi/{vid}/{res}.jpg"
        for attempt in range(4):
            try:
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                    data = r.read()
                    ct = r.headers.get("Content-Type", "")
                    if r.status == 200 and ct.startswith("image/") and len(data) >= MIN_BYTES:
                        CACHE.mkdir(parents=True, exist_ok=True)
                        tmp = CACHE / f".{vid}.{res}.tmp"
                        tmp.write_bytes(data)
                        os.replace(tmp, CACHE / f"{vid}.jpg")
                        return (vid, "fetched", res)
                break  # 200 but not a usable image -> try the next resolution
            except urllib.error.HTTPError as e:
                if e.code in RETRY_CODES:
                    time.sleep(2 ** attempt)
                    continue
                break  # 404 and friends -> try the next resolution
            except Exception:
                time.sleep(2 ** attempt)
                continue
    return (vid, "failed", None)


def _resize_width(im: "Image.Image", w: int) -> "Image.Image":
    if im.width <= w:
        return im.copy()
    h = round(im.height * w / im.width)
    return im.resize((w, h), Image.LANCZOS)


def derive_one(vid: str, force: bool):
    if not force and outputs_exist(vid):
        return "kept"
    src = cache_file(vid)
    if not src:
        return "no-source"
    OUT.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as im:
        im = im.convert("RGB")  # convert also drops any EXIF
        for w in WIDTHS:
            c = _resize_width(im, w)
            tmp = OUT / f".{vid}-{w}.tmp.webp"
            c.save(tmp, "WEBP", quality=80, method=6)
            os.replace(tmp, OUT / f"{vid}-{w}.webp")
    return "derived"


def make_placeholder(force: bool):
    # A calm dark card matching the facade gradient, so a missing thumbnail reads
    # as intentional rather than broken. Generated once, deterministically.
    if not force and all((OUT / f"placeholder-{w}.webp").exists() for w in WIDTHS):
        return
    OUT.mkdir(parents=True, exist_ok=True)
    for w in WIDTHS:
        h = round(w * 9 / 16)
        base = Image.new("RGB", (w, h))
        top, bot = (27, 27, 32), (11, 11, 14)  # #1b1b20 -> #0b0b0e
        px = base.load()
        for y in range(h):
            t = y / max(1, h - 1)
            row = tuple(round(top[i] + (bot[i] - top[i]) * t) for i in range(3))
            for x in range(w):
                px[x, y] = row
        tmp = OUT / f".placeholder-{w}.tmp.webp"
        base.save(tmp, "WEBP", quality=80, method=6)
        os.replace(tmp, OUT / f"placeholder-{w}.webp")


def main():
    ap = argparse.ArgumentParser(description="Fetch + derive local thumbnails.")
    ap.add_argument("--force", action="store_true", help="refetch and rederive everything")
    ap.add_argument("--workers", type=int, default=8, help="parallel downloads (default 8)")
    ap.add_argument("--no-fetch", action="store_true", help="skip download, only derive from cache")
    ap.add_argument("--no-derive", action="store_true", help="skip derive, only download to cache")
    args = ap.parse_args()

    vids = load_vids()
    fetched = cached = failed = 0
    failed_ids = []

    if not args.no_fetch:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as ex:
            for vid, status, _res in ex.map(lambda v: fetch_one(v, args.force), vids):
                if status == "fetched":
                    fetched += 1
                elif status == "cached":
                    cached += 1
                else:
                    failed += 1
                    failed_ids.append(vid)

    derived = kept = no_source = 0
    make_placeholder(args.force)
    if not args.no_derive:
        for vid in vids:
            r = derive_one(vid, args.force)
            if r == "derived":
                derived += 1
            elif r == "kept":
                kept += 1
            else:
                no_source += 1

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "total_ids": len(vids),
        "fetch": {"fetched": fetched, "cached": cached, "failed": failed},
        "derive": {"derived": derived, "kept": kept, "no_source": no_source},
        "failed_ids": sorted(failed_ids),
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["fetch"] | report["derive"], indent=2))
    print(f"failed ids: {len(failed_ids)} -> placeholder; report: {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
