#!/usr/bin/env python3
"""Fail if .well-known/security.txt is missing, has no Expires, or expires in fewer
than 30 days (RFC 9116 recommends keeping it fresh, max 1 year out).

Usage: python3 scripts/check_security_txt.py [root]
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
F = ROOT / ".well-known" / "security.txt"


def main():
    if not F.exists():
        print("FAIL: .well-known/security.txt is missing")
        return 1
    m = re.search(r"(?im)^Expires:\s*(\S+)\s*$", F.read_text())
    if not m:
        print("FAIL: security.txt has no Expires field")
        return 1
    try:
        exp = datetime.fromisoformat(m.group(1).replace("Z", "+00:00"))
    except ValueError:
        print(f"FAIL: security.txt Expires is not a valid ISO 8601 datetime: {m.group(1)}")
        return 1
    days = (exp - datetime.now(timezone.utc)).days
    if days < 30:
        print(f"FAIL: security.txt expires in {days} days (< 30). Renew the Expires field.")
        return 1
    print(f"OK: security.txt valid, expires in {days} days.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
