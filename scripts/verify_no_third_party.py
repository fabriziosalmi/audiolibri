#!/usr/bin/env python3
"""Fail if any external host appears in an auto-loading context, in the generated
HTML or in the served JavaScript.

The site claims that nothing outside audiolibri.org is contacted until the user
presses play. This check enforces that claim on the build output.

Auto-loading contexts inspected in HTML: <img src|srcset>, <script src>,
<iframe src>, <link href>, <source src|srcset>. Inert references are ignored
on purpose: <a href>, data-* attributes, JSON-LD, meta, og:image/twitter:image.

The only allowed external hosts are the click-to-load facade and plain links:
  www.youtube-nocookie.com (data-embed becomes an iframe only after the click)
  www.youtube.com          (watch links, and the iframe API injected on first play)

Usage:  python3 scripts/verify_no_third_party.py [root]
Exit 0 = clean, 1 = violations.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
SELF = "audiolibri.org"
ALLOWED = {"www.youtube-nocookie.com", "www.youtube.com"}

AUTO_TAG = re.compile(
    r'<(?:img|script|iframe|source|link)\b[^>]*?\b(?:src|srcset|href)\s*=\s*"([^"]*)"',
    re.IGNORECASE,
)
URL_HOST = re.compile(r'https?://([a-z0-9.\-]+)', re.IGNORECASE)
# JS string literals that look like a Google image/CDN host being built at runtime.
JS_HOST = re.compile(r'https?://([a-z0-9.\-]+)', re.IGNORECASE)

HTML_GLOBS = ("*.html",)
JS_FILES = ("app.js", "mobile-enhancements.js", "tailwind-mobile.js", "service-worker.js")


def host_of(url):
    m = URL_HOST.search(url)
    return m.group(1).lower() if m else None


def external(host):
    return host and host != SELF and not host.endswith("." + SELF) and host not in ALLOWED


# A <source> inside an <audio preload="none"> loads nothing until the user presses
# play, so it is not an auto-loading context (same contract as the YouTube facade).
SAFE_AUDIO = re.compile(r'<audio\b[^>]*preload="none"[^>]*>.*?</audio>', re.IGNORECASE | re.DOTALL)


def scan_html(path, text):
    text = SAFE_AUDIO.sub("", text)
    bad = []
    for attr_val in AUTO_TAG.findall(text):
        for url in re.split(r'[,\s]+', attr_val):
            url = url.strip()
            if not url.startswith("http"):
                continue
            h = host_of(url)
            if external(h):
                bad.append((h, url[:80]))
    return bad


def scan_js(path, text):
    bad = []
    for h in JS_HOST.findall(text):
        h = h.lower()
        if external(h):
            bad.append((h, ""))
    return bad


def main():
    violations = {}
    html_count = 0
    for g in HTML_GLOBS:
        for p in ROOT.rglob(g):
            if any(part in (".git", ".cache", "node_modules") for part in p.parts):
                continue
            html_count += 1
            bad = scan_html(p, p.read_text(encoding="utf-8", errors="ignore"))
            if bad:
                violations[str(p.relative_to(ROOT))] = sorted(set(bad))
    for name in JS_FILES:
        p = ROOT / name
        if p.exists():
            bad = scan_js(p, p.read_text(encoding="utf-8", errors="ignore"))
            if bad:
                violations[name] = sorted(set(bad))

    if violations:
        print(f"FAIL: external hosts in auto-loading contexts ({len(violations)} file/i):")
        for f, hosts in sorted(violations.items()):
            uniq = sorted({h for h, _ in hosts})
            print(f"  {f}: {', '.join(uniq)}")
        return 1

    print(f"OK: {html_count} HTML files + {len(JS_FILES)} JS files scanned, "
          f"no external auto-loading host (allowed: {', '.join(sorted(ALLOWED))}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
