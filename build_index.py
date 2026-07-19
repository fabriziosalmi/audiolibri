#!/usr/bin/env python3
"""Build a lightweight home index (index.min.json) from the full dataset.

The homepage SPA (app.js → processAudiobooksData/renderHomeRows/performSearch/
displayBook) only ever reads a handful of fields per record, and it already
truncates the synopsis to 320 chars in the hero. Yet the home currently fetches
the whole `augmented.json` (~6.3 MB serialized) with `cache:'no-cache'`, which
re-downloads every visit and blocks the main thread on JSON.parse.

This script emits `index.min.json` containing ONLY the fields the home uses,
with the same field NAMES as augmented.json so `processAudiobooksData` needs no
changes. Dead weight dropped: full `description` (kept only as a 320-char
`real_synopsis` fallback), `transcript`, `summary`, `raw_response`, and other
build-time fields never read by the client.

Run at build time (before/with generate_pages.py):  python3 build_index.py
Output: index.min.json  (app.js fetches this instead of augmented.json)
"""
import json
import gzip
import os
import sys

SRC_CANDIDATES = ["augmented.json", "audiobooks.json"]
OUT = "index.min.json"

# Max synopsis length kept in the index. displayBook() already trims to 320,
# and performSearch() matches substrings — 320 chars preserve both behaviours.
SYNOPSIS_MAX = 320
# Cap noisy YouTube keyword tags (used by performSearch) to keep the index lean.
TAGS_MAX = 12

# Fields read by app.js (processAudiobooksData). Same names as the source so the
# client code is untouched. `description`/`transcript`/`summary`/`raw_response`
# and other internal fields are intentionally omitted.
KEEP = {
    "real_title", "title", "part_display", "series", "part",
    "real_author", "real_genre",
    "thumbnail", "audio_url", "audio_file", "audio_chapters",
    "duration", "url", "channel", "channel_url", "categories",
    "upload_date", "view_count", "like_count",
    "source", "embed_type", "embed_url", "license",
}


def pick_source():
    for name in SRC_CANDIDATES:
        if os.path.exists(name):
            return name
    sys.exit(f"No source dataset found (looked for {SRC_CANDIDATES}).")


def reduce_record(book):
    out = {k: v for k, v in book.items() if k in KEEP and v not in (None, "", [], {})}

    # Resolve the synopsis exactly like the client would (real_synopsis, else
    # the long YouTube description) and truncate — this is the only trama the
    # home ever shows or searches, so we never ship the full description.
    synopsis = (book.get("real_synopsis") or book.get("description") or "").strip()
    if synopsis:
        out["real_synopsis"] = synopsis[:SYNOPSIS_MAX]

    tags = book.get("tags")
    if isinstance(tags, list) and tags:
        out["tags"] = tags[:TAGS_MAX]

    return out


def main():
    src = pick_source()
    with open(src, encoding="utf-8") as f:
        data = json.load(f)

    index = {vid: reduce_record(book) for vid, book in data.items()}

    payload = json.dumps(index, ensure_ascii=False, separators=(",", ":"))
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(payload)

    raw = len(payload.encode("utf-8"))
    gz = len(gzip.compress(payload.encode("utf-8"), 9))
    src_raw = os.path.getsize(src)
    print(f"source      : {src} ({src_raw/1e6:.2f} MB)")
    print(f"{OUT} : {raw/1e6:.2f} MB raw / {gz/1024:.0f} KB gzip  ({len(index)} records)")
    print(f"reduction   : {100*(1-raw/src_raw):.0f}% raw vs source")


if __name__ == "__main__":
    main()
