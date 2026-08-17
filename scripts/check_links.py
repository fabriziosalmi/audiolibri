#!/usr/bin/env python3
"""Fail if an internal link (href/src starting with /) points to something that does
not exist in the build output (a page directory with index.html, or a real file).

Usage: python3 scripts/check_links.py [root]
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
REF = re.compile(r'(?:href|src)="(/[^"#?]*)"')


def resolves(path):
    p = path.strip("/")
    if p == "":
        return True
    fp = ROOT / p
    return fp.is_file() or (fp / "index.html").is_file()


def main():
    links = {}
    for page in ROOT.rglob("*.html"):
        if any(x in page.parts for x in (".git", ".cache", "node_modules", "docs")):
            continue
        for ref in REF.findall(page.read_text(encoding="utf-8", errors="ignore")):
            links.setdefault(ref, page)
    broken = sorted(h for h in links if not resolves(h))
    if broken:
        print(f"FAIL: {len(broken)} internal links point to missing targets:")
        for h in broken[:40]:
            print(f"  {h}   (e.g. in {links[h].relative_to(ROOT)})")
        return 1
    print(f"OK: {len(links)} unique internal links, all resolve.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
