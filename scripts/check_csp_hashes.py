#!/usr/bin/env python3
"""Fail if the sha256 of the executable inline scripts in the build output no longer
matches scripts/csp-hashes.txt (the hashes hard-coded in the Cloudflare CSP).

When this fails, an inline script changed: update the CSP on Cloudflare AND rerun
`python3 scripts/gen_csp_hashes.py` (or regenerate scripts/csp-hashes.txt) so the two
stay in sync. Otherwise the browser would block the changed script.

Usage: python3 scripts/check_csp_hashes.py [root]
"""
import base64
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
EXPECTED = ROOT / "scripts" / "csp-hashes.txt"
INLINE = re.compile(r'(<script(?![^>]*\bsrc=)[^>]*>)(.*?)</script>', re.DOTALL)


def current_hashes():
    hashes = set()
    for p in ROOT.rglob("*.html"):
        if any(x in p.parts for x in (".git", ".cache", "node_modules", "docs")):
            continue
        for tag, body in INLINE.findall(p.read_text(encoding="utf-8", errors="ignore")):
            if "json" in tag.lower() or body.strip() == "":
                continue
            hashes.add("sha256-" + base64.b64encode(hashlib.sha256(body.encode("utf-8")).digest()).decode())
    return hashes


def main():
    if not EXPECTED.exists():
        print(f"FAIL: {EXPECTED} missing")
        return 1
    expected = {ln.strip() for ln in EXPECTED.read_text().splitlines() if ln.strip()}
    got = current_hashes()
    extra = got - expected      # in the output but NOT allowed by the CSP -> blocked
    missing = expected - got    # allowed by the CSP but no longer emitted -> harmless
    if extra:
        print("FAIL: inline scripts whose hash is NOT in the CSP allowlist (would be blocked):")
        for h in sorted(extra):
            print("  " + h)
        print("Update the Cloudflare CSP and scripts/csp-hashes.txt to match.")
        return 1
    if missing:
        print("WARN: CSP allows hashes no longer present in the output (safe; prune when convenient):")
        for h in sorted(missing):
            print("  " + h)
    print(f"OK: {len(got)} inline-script hashes, all present in the CSP allowlist.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
