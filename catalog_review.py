#!/usr/bin/env python3
"""Flag catalogue entries whose metadata suggests a work that may NOT be in the
public domain, so a human can review them.

Read-only: it writes only a report (docs/audit/06-catalog-review.md, which is NOT
in the public repo) and never removes anything. Removal is a manual decision, made
by adding an identifier to the versioned denylist.txt that generate_pages.py reads.

Explicit criterion: an entry is flagged when its title / real_title / channel /
synopsis mentions a modern publisher (a commercial edition is protected even when
the underlying text is public domain) or a named translation (a translation is
protected in its own right). This does NOT conclude on the lawfulness of any
content; it only lists cases to verify by hand, ordered by confidence.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "augmented.json"
OUT = ROOT / "docs" / "audit" / "06-catalog-review.md"

PUBLISHERS = [
    "mondadori", "einaudi", "adelphi", "feltrinelli", "sellerio", "bompiani",
    "rizzoli", "garzanti", "emons", "longanesi", "guanda", "neri pozza", "marsilio",
    "salani", "piemme", "newton compton", "minimum fax", "nottetempo", "fazi",
    "la nave di teseo", "sonzogno", "sperling", "corbaccio", "nord", "fanucci",
]
TRANSLATION = ["traduzione di", "traduzione a cura", "tradotto da", "traduttore"]


def video_id(url):
    m = re.search(r"(?:v=|youtu\.be/|embed/)([\w-]{11})", url or "")
    return m.group(1) if m else ""


def main():
    books = json.loads(DATA.read_text())
    rows = []
    for key, b in books.items():
        text = " ".join(str(b.get(f, "")) for f in
                        ("title", "real_title", "channel", "real_synopsis")).lower()
        pubs = [p for p in PUBLISHERS if p in text]
        trans = [t for t in TRANSLATION if t in text]
        score = len(pubs) * 2 + len(trans)
        if score:
            rows.append((score, key, video_id(b.get("url", "")),
                         (b.get("real_title") or b.get("title") or "").strip(),
                         (b.get("real_author") or "").strip(),
                         sorted(set(pubs + trans))))
    rows.sort(key=lambda r: (-r[0], r[3].lower()))

    out = [
        "# Fase 6 - Revisione catalogo (candidati NON pubblico dominio)",
        "",
        "Read-only, generato da catalog_review.py. Nessuna rimozione automatica.",
        "",
        "Criterio esplicito: la scheda e' segnalata se titolo / autore / canale / trama",
        "menziona un editore moderno (l'edizione commerciale e' protetta anche per un testo",
        "di pubblico dominio) o una traduzione con nome (protetta a se'). Questo NON conclude",
        "sulla liceita' di alcun contenuto: elenca solo i casi da verificare a mano.",
        "",
        "Per ESCLUDERE una scheda dal sito: aggiungi il suo identificatore (video id, oppure",
        "la chiave qui sotto) a denylist.txt, una per riga. Tracciato e reversibile.",
        "",
        f"Totale segnalati: {len(rows)}",
        "",
        "| conf | id per denylist | titolo | autore | marcatori |",
        "|---|---|---|---|---|",
    ]
    for score, key, vid, title, author, marks in rows:
        out.append(f"| {score} | `{vid or key}` | {title[:52]} | {author[:28]} | {', '.join(marks)} |")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(out) + "\n")
    print(f"flagged {len(rows)} entries -> {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
