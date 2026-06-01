#!/usr/bin/env python3
"""
generate_pages.py — build crawlable static pages for audiolibri.org.

The site is a client-rendered SPA, so search engines and AI answer engines
see only the loading spinner. This generator pre-renders static HTML (committed
to the repo, CDN-cacheable) so the ~1793 titles become indexable, each with
schema.org structured data. All pages share the same header/footer chrome as
the SPA (unified look); search submits to /?search= which the SPA executes.

    /audiolibro/<slug>-<id>/   one page per audiobook (Audiobook + FAQ + crumbs)
    /genere/<slug>/            one hub per genre (ItemList)
    /autore/<slug>/            one hub per author (>= 2 titles) (ItemList)
    /generi/  /autori/         index pages (destinations for the main nav)
    /sitemap.xml  /robots.txt

Usage:
    python3 generate_pages.py            # build everything
    python3 generate_pages.py <VIDEO_ID> # build a single exemplar page
"""
import html
import json
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "augmented.json"
SITE = "https://audiolibri.org"
EXEMPLAR_ID = "BInAElMNUBc"
TODAY = date.today().isoformat()
e = html.escape

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&'
         'family=Fraunces:opsz,wght@9..144,500;9..144,600&display=swap" rel="stylesheet">')

SEARCH_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" '
              'viewBox="0 0 16 16" aria-hidden="true"><path d="M11.742 10.344a6.5 6.5 0 1 0-1.397 '
              '1.398h-.001c.03.04.062.078.098.115l3.85 3.85a1 1 0 0 0 1.415-1.414l-3.85-3.85a1.007 '
              '1.007 0 0 0-.115-.1zM12 6.5a5.5 5.5 0 1 1-11 0 5.5 5.5 0 0 1 11 0z"/></svg>')
GITHUB_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="currentColor" '
              'aria-hidden="true"><path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 '
              '0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 '
              '1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 '
              '0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 '
              '1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 '
              '3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 '
              '8.013 0 0016 8c0-4.42-3.58-8-8-8z"></path></svg>')
THEME_SVG = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" '
             'cy="12" r="9"/><path d="M12 3a9 9 0 0 0 0 18z" fill="currentColor" stroke="none"/></svg>')

# Grey-placeholder fallback for deleted videos, shared by hubs/indexes.
FALLBACK_SCRIPT = """<script>
document.querySelectorAll('.nf-card-img').forEach(function(img){
  function fb(){var c=img.closest('.nf-card-cover');if(c)c.classList.add('is-fallback');}
  if(img.complete){if(!img.naturalWidth||img.naturalWidth<=120)fb();}
  img.addEventListener('error',fb);
  img.addEventListener('load',function(){if(img.naturalWidth<=120)fb();});
});
</script>"""


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return re.sub(r"-{2,}", "-", text) or "x"


def iso_duration(seconds) -> str:
    s = int(seconds or 0)
    h, m, sec = s // 3600, (s % 3600) // 60, s % 60
    return "PT" + (f"{h}H" if h else "") + (f"{m}M" if m else "") + (f"{sec}S" if sec else "0S")


def human_duration(seconds) -> str:
    s = int(seconds or 0)
    h, m = s // 3600, (s % 3600) // 60
    if h:
        return f"{h} h {m} min" if m else f"{h} h"
    return f"{m} min" if m else "—"


def compact_duration(seconds) -> str:
    s = int(seconds or 0)
    h, m = s // 3600, (s % 3600) // 60
    return f"{h}h {m}m" if h else f"{m}m"


def iso_date(yyyymmdd: str) -> str:
    if yyyymmdd and len(yyyymmdd) == 8 and yyyymmdd.isdigit():
        return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:]}"
    return ""


def video_id(book: dict) -> str:
    m = re.search(r"(?:v=|youtu\.be/|embed/)([\w-]{11})", book.get("url", ""))
    return m.group(1) if m else ""


def title_of(b):  return (b.get("real_title") or b.get("title") or "Audiolibro").strip()
def author_of(b): return (b.get("real_author") or "Autore sconosciuto").strip()
def genre_of(b):  return (b.get("real_genre") or (b.get("categories") or [""])[0] or "").strip()


def book_slug(b) -> str:
    vid = video_id(b)
    return f"{slugify(title_of(b))}-{vid}" if vid else slugify(title_of(b))


def meta_description(text: str, limit: int = 155) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


PAGE_CSS = """<style>
.bp-wrap { max-width: 980px; margin: 0 auto; padding: clamp(1rem,3vw,2rem) 0 0; }
.bp-crumbs { font-size:var(--text-sm); color:var(--secondary-text); margin-bottom:1.25rem; }
.bp-crumbs a { color:var(--secondary-text); text-decoration:none; }
.bp-crumbs a:hover { color:var(--primary-color); }
.bp-eyebrow { text-transform:uppercase; letter-spacing:.16em; font-size:var(--text-xs); font-weight:700; color:var(--primary-color); }
.bp-title { font-family:var(--font-display); font-size:clamp(2rem,5vw,3.2rem); font-weight:600; line-height:1.05; margin:.3rem 0 .4rem; }
.bp-author { font-size:var(--text-lg); color:var(--secondary-text); margin:0 0 1rem; }
.bp-author b { color:var(--text-color); } .bp-author a { color:inherit; }
.bp-chips { display:flex; flex-wrap:wrap; gap:.5rem; margin-bottom:1.5rem; }
.bp-chip { padding:.25rem .8rem; border-radius:var(--radius-pill); background:rgba(var(--primary-rgb),.1); color:var(--primary-color); font-size:var(--text-xs); font-weight:600; text-decoration:none; }
.bp-player { aspect-ratio:16/9; width:100%; max-width:760px; border:0; border-radius:var(--radius-lg); overflow:hidden; box-shadow:var(--card-shadow); margin-bottom:2rem; background:#000; }
.bp-synopsis h2, .bp-faqs h2 { font-family:var(--font-display); font-size:var(--text-2xl); margin:0 0 .8rem; }
.bp-synopsis p { font-size:var(--text-lg); line-height:1.7; max-width:70ch; }
.bp-faqs { margin-top:2.5rem; }
.bp-faq { border-bottom:1px solid var(--border-color); padding:.9rem 0; }
.bp-faq summary { cursor:pointer; font-weight:600; }
.bp-faq p { color:var(--secondary-text); margin:.6rem 0 0; }
.bp-grid { display:flex; flex-wrap:wrap; gap:var(--space-4); margin-top:1.5rem; }
.bp-lead { font-size:var(--text-lg); color:var(--secondary-text); max-width:70ch; }
.bp-back { display:inline-block; margin-top:2.5rem; color:var(--primary-color); text-decoration:none; font-weight:600; }
.index-grid { display:flex; flex-wrap:wrap; gap:var(--space-3); margin-top:1.5rem; }
.index-item { display:inline-flex; align-items:center; gap:.6rem; padding:.6rem 1.1rem; border:1px solid var(--border-color); border-radius:var(--radius-pill); text-decoration:none; color:var(--text-color); font-weight:600; transition:background-color .2s,border-color .2s,transform .2s; }
.index-item:hover { background:var(--hover-overlay); border-color:var(--secondary-text); transform:translateY(-1px); }
.index-count { color:var(--secondary-text); font-weight:500; font-size:var(--text-sm); }
</style>"""


def head(title, description, canonical, image, og_type="website", extra_ld=()):
    ld = "".join('<script type="application/ld+json">\n'
                 + json.dumps(o, ensure_ascii=False, indent=2) + "\n</script>\n" for o in extra_ld)
    img = (f'<meta property="og:image" content="{e(image)}">\n'
           f'<meta name="twitter:image" content="{e(image)}">') if image else ""
    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<meta name="robots" content="index, follow, max-image-preview:large">
<link rel="canonical" href="{e(canonical)}">
<meta name="theme-color" content="#000000">
<meta name="color-scheme" content="light dark">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="Audiolibri.org">
<meta property="og:locale" content="it_IT">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(description)}">
<meta property="og:url" content="{e(canonical)}">
{img}
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/icons/favicon.ico">
{FONTS}
<link rel="stylesheet" href="/app.css">
{ld}{PAGE_CSS}
</head>"""


def header_html():
    return f"""<header class="site-bar is-scrolled" role="banner">
  <h1 class="site-brand"><a href="/" aria-label="Audiolibri.org — home"><img src="/audiobooks_transparent.png" alt="" width="32" height="32"><span>audiolibri.org</span></a></h1>
  <nav class="main-nav" aria-label="Navigazione principale">
    <a href="/" class="nav-link">Home</a>
    <a href="/generi/" class="nav-link">Generi</a>
    <a href="/autori/" class="nav-link">Autori</a>
  </nav>
  <form class="search-container" role="search" action="/" method="get">
    <label for="s" class="sr-only">Cerca audiolibri per titolo, autore o lettore</label>
    <input type="search" id="s" name="search" class="tw-input" placeholder="Cerca per titolo, autore o lettore" autocomplete="off">
    <button class="tw-button" type="submit" aria-label="Cerca">{SEARCH_SVG}<span class="tw-hidden xs:tw-inline">Cerca</span></button>
  </form>
</header>"""


def footer_html():
    return f"""<footer class="site-footer" role="contentinfo">
  <div class="footer-top">
    <div class="footer-brand">
      <span class="footer-brand-name">audiolibri.org</span>
      <p>La più grande collezione di audiolibri italiani gratuiti.</p>
    </div>
    <div class="footer-cols">
      <nav class="footer-links" aria-label="Collegamenti">
        <a class="footer-link" href="/generi/">Generi</a>
        <a class="footer-link" href="/autori/">Autori</a>
        <a class="footer-link" href="https://github.com/fabriziosalmi/audiolibri/blob/main/ACCESSIBILITY.md" target="_blank" rel="noopener noreferrer">Accessibilità</a>
      </nav>
      <div class="footer-actions">
        <a class="ghost-btn" href="https://github.com/fabriziosalmi/audiolibri" target="_blank" rel="noopener noreferrer" aria-label="Codice sorgente su GitHub">{GITHUB_SVG}<span>GitHub</span></a>
      </div>
    </div>
  </div>
  <div class="footer-base">
    <p>© {date.today().year} Audiolibri.org · Realizzato con ❤️ per gli amanti della letteratura italiana</p>
  </div>
</footer>"""


def shell(head_html, main_html, with_fallback=False):
    return (head_html + '\n<body>\n<div class="container ios-safe-inset">\n'
            + header_html() + "\n<main id=\"main-content\">\n" + main_html
            + "\n</main>\n" + footer_html() + "\n</div>\n"
            + (FALLBACK_SCRIPT if with_fallback else "") + "\n</body>\n</html>")


def card_link(b) -> str:
    vid = video_id(b)
    t, a = title_of(b), author_of(b)
    hue = sum(ord(c) for c in (vid or t)) % 360
    thumb = f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg" if vid else b.get("thumbnail", "")
    initial = e((t or "?").strip()[:1].upper())
    return f"""<a class="nf-card" href="/audiolibro/{book_slug(b)}/" aria-label="{e(t)} di {e(a)}">
  <span class="nf-card-cover" style="--cover-hue:{hue}" data-initial="{initial}">
    <img class="nf-card-img" loading="lazy" alt="" src="{e(thumb)}">
    <span class="nf-card-duration">{e(compact_duration(b.get('duration')))}</span>
  </span>
  <span class="nf-card-body">
    <span class="nf-card-title">{e(t)}</span>
    <span class="nf-card-author">{e(a)}</span>
  </span>
</a>"""


def build_book_page(b: dict):
    vid = video_id(b)
    title, author, genre = title_of(b), author_of(b), genre_of(b)
    synopsis = (b.get("real_synopsis") or b.get("description") or "").strip()
    channel = (b.get("channel") or "").strip()
    dur, views, likes = b.get("duration") or 0, b.get("view_count") or 0, b.get("like_count") or 0
    published = iso_date(b.get("upload_date", ""))
    cover = f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg" if vid else b.get("thumbnail", "")
    rel_dir = f"audiolibro/{book_slug(b)}"
    canonical = f"{SITE}/{rel_dir}/"
    embed = f"https://www.youtube-nocookie.com/embed/{vid}" if vid else ""
    genre_label = genre.capitalize() if genre else ""
    description = meta_description(synopsis) or f"Ascolta gratis l'audiolibro «{title}» di {author}."

    faq = [
        (f"L'audiolibro di «{title}» è gratis?",
         f"Sì. «{title}» è disponibile gratuitamente su Audiolibri.org, in streaming, senza registrazione."),
        ("Chi legge l'audiolibro?",
         f"La lettura è a cura di {channel}." if channel else "La lettura è ad alta voce in italiano."),
        ("Quanto dura?", f"La durata è di circa {human_duration(dur)}."),
        ("Dove posso ascoltarlo?",
         f"Puoi ascoltarlo direttamente in questa pagina, oppure nella libreria completa su {SITE}."),
    ]

    audiobook = {"@context": "https://schema.org", "@type": "Audiobook", "name": title,
                 "author": {"@type": "Person", "name": author}, "inLanguage": "it",
                 "description": synopsis, "url": canonical, "duration": iso_duration(dur),
                 "isAccessibleForFree": True, "isFamilyFriendly": True}
    if genre_label: audiobook["genre"] = genre_label
    if cover: audiobook["thumbnailUrl"] = audiobook["image"] = cover
    if channel:
        audiobook["readBy"] = {"@type": "Person", "name": channel}
        audiobook["publisher"] = {"@type": "Organization", "name": channel}
    if published: audiobook["datePublished"] = published
    if embed:
        audiobook["associatedMedia"] = {"@type": "AudioObject", "contentUrl": b.get("url", ""),
                                         "embedUrl": embed, "duration": iso_duration(dur)}
    stats = []
    if views: stats.append({"@type": "InteractionCounter", "interactionType": "https://schema.org/ListenAction", "userInteractionCount": views})
    if likes: stats.append({"@type": "InteractionCounter", "interactionType": "https://schema.org/LikeAction", "userInteractionCount": likes})
    if stats: audiobook["interactionStatistic"] = stats

    crumbs = [{"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"}]
    if genre_label:
        crumbs.append({"@type": "ListItem", "position": 2, "name": genre_label, "item": f"{SITE}/genere/{slugify(genre)}/"})
    crumbs.append({"@type": "ListItem", "position": len(crumbs) + 1, "name": title, "item": canonical})
    breadcrumb = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": crumbs}
    faqpage = {"@context": "https://schema.org", "@type": "FAQPage",
               "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}

    chips = "".join(f'<span class="bp-chip">{e(x)}</span>' for x in
                    [genre_label, human_duration(dur), (f"{views:,}".replace(",", ".") + " ascolti") if views else ""] if x)
    faq_html = "".join(f'<details class="bp-faq"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in faq)
    crumb_html = '<a href="/">Home</a>' + (f' › <a href="/genere/{slugify(genre)}/">{e(genre_label)}</a>' if genre_label else '') + f' › <span>{e(title)}</span>'
    player = (f'<iframe class="bp-player" src="{e(embed)}" title="Audiolibro: {e(title)}" loading="lazy" '
              'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
              'allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>') if embed else ""

    main_html = f"""<div class="bp-wrap">
    <nav class="bp-crumbs" aria-label="Breadcrumb">{crumb_html}</nav>
    <p class="bp-eyebrow">Audiolibro gratis</p>
    <h1 class="bp-title">{e(title)}</h1>
    <p class="bp-author">di <b><a href="/autore/{slugify(author)}/">{e(author)}</a></b></p>
    <div class="bp-chips">{chips}</div>
    {player}
    <section class="bp-synopsis"><h2>Trama</h2><p>{e(synopsis)}</p></section>
    <section class="bp-faqs"><h2>Domande frequenti</h2>{faq_html}</section>
    <a class="bp-back" href="/">← Tutta la libreria</a>
  </div>"""
    page_title = f"{title} — audiolibro gratis di {author} | Audiolibri.org"
    head_html = head(page_title, description, canonical, cover, "article", (audiobook, breadcrumb, faqpage))
    return rel_dir, shell(head_html, main_html)


def build_hub(kind, label, items, slug):
    rel_dir = f"{kind}/{slug}"
    canonical = f"{SITE}/{rel_dir}/"
    if kind == "genere":
        h1 = f"Audiolibri {label.lower()}"
        lead = f"Tutti gli audiolibri del genere {label.lower()} da ascoltare gratis: {len(items)} titoli."
        page_title = f"Audiolibri {label} gratis — {len(items)} titoli | Audiolibri.org"
    else:
        h1 = f"Audiolibri di {label}"
        lead = f"Tutti gli audiolibri di {label} da ascoltare gratis: {len(items)} titoli."
        page_title = f"Audiolibri di {label} gratis | Audiolibri.org"

    itemlist = {"@context": "https://schema.org", "@type": "ItemList", "name": h1, "numberOfItems": len(items),
                "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{SITE}/audiolibro/{book_slug(b)}/", "name": title_of(b)}
                                    for i, b in enumerate(items)]}
    breadcrumb = {"@context": "https://schema.org", "@type": "BreadcrumbList",
                  "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                                      {"@type": "ListItem", "position": 2, "name": h1, "item": canonical}]}
    grid = "".join(card_link(b) for b in items)
    main_html = f"""<div class="bp-wrap">
    <nav class="bp-crumbs" aria-label="Breadcrumb"><a href="/">Home</a> › <a href="/{ 'generi' if kind=='genere' else 'autori' }/">{ 'Generi' if kind=='genere' else 'Autori' }</a> › <span>{e(h1)}</span></nav>
    <h1 class="bp-title">{e(h1)}</h1>
    <p class="bp-lead">{e(lead)}</p>
    <div class="bp-grid">{grid}</div>
    <a class="bp-back" href="/">← Tutta la libreria</a>
  </div>"""
    head_html = head(page_title, meta_description(lead), canonical, "", "website", (itemlist, breadcrumb))
    return rel_dir, shell(head_html, main_html, with_fallback=True)


def build_index(kind, entries):
    """entries: list of (label, slug, count). kind in {generi, autori}."""
    rel_dir = kind
    canonical = f"{SITE}/{rel_dir}/"
    if kind == "generi":
        h1, sub = "Generi", "genere"
        lead = f"Esplora gli audiolibri italiani gratuiti per genere — {len(entries)} categorie."
    else:
        h1, sub = "Autori", "autore"
        lead = f"Esplora gli audiolibri italiani gratuiti per autore — {len(entries)} autori."
    page_title = f"{h1} — audiolibri italiani gratuiti | Audiolibri.org"

    items = "".join(
        f'<a class="index-item" href="/{sub}/{slug}/">{e(label)}<span class="index-count">{count}</span></a>'
        for label, slug, count in entries)
    itemlist = {"@context": "https://schema.org", "@type": "ItemList", "name": h1, "numberOfItems": len(entries),
                "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": label, "url": f"{SITE}/{sub}/{slug}/"}
                                    for i, (label, slug, count) in enumerate(entries)]}
    breadcrumb = {"@context": "https://schema.org", "@type": "BreadcrumbList",
                  "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                                      {"@type": "ListItem", "position": 2, "name": h1, "item": canonical}]}
    main_html = f"""<div class="bp-wrap">
    <nav class="bp-crumbs" aria-label="Breadcrumb"><a href="/">Home</a> › <span>{e(h1)}</span></nav>
    <h1 class="bp-title">{h1}</h1>
    <p class="bp-lead">{e(lead)}</p>
    <div class="index-grid">{items}</div>
    <a class="bp-back" href="/">← Tutta la libreria</a>
  </div>"""
    head_html = head(page_title, meta_description(lead), canonical, "", "website", (itemlist, breadcrumb))
    return rel_dir, shell(head_html, main_html)


def write(rel_dir, page):
    out = ROOT / rel_dir / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return f"{rel_dir}/"


def build_sitemap(paths):
    urls = f"  <url><loc>{SITE}/</loc><lastmod>{TODAY}</lastmod></url>\n"
    urls += "".join(f"  <url><loc>{SITE}/{p}</loc><lastmod>{TODAY}</lastmod></url>\n" for p in paths)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n")


def main():
    books = json.loads(DATA.read_text())

    if len(sys.argv) > 1 and sys.argv[1] != "all":
        vid = sys.argv[1]
        if vid not in books:
            sys.exit(f"id {vid} not found")
        rel_dir, page = build_book_page(books[vid])
        print("wrote", write(rel_dir, page))
        return

    valid = [b for b in books.values() if video_id(b)]
    paths = []

    for b in valid:
        rel_dir, page = build_book_page(b)
        paths.append(write(rel_dir, page))

    genres, authors = {}, {}
    for b in valid:
        g = genre_of(b)
        if g:
            genres.setdefault(g, []).append(b)
        authors.setdefault(author_of(b), []).append(b)

    genre_entries = []
    for g, items in sorted(genres.items(), key=lambda kv: len(kv[1]), reverse=True):
        items.sort(key=lambda b: b.get("view_count") or 0, reverse=True)
        rel_dir, page = build_hub("genere", g.capitalize(), items, slugify(g))
        paths.append(write(rel_dir, page))
        genre_entries.append((g.capitalize(), slugify(g), len(items)))

    author_entries = []
    for a, items in sorted(authors.items(), key=lambda kv: len(kv[1]), reverse=True):
        if len(items) < 2 or a == "Autore sconosciuto":
            continue
        items.sort(key=lambda b: b.get("view_count") or 0, reverse=True)
        rel_dir, page = build_hub("autore", a, items, slugify(a))
        paths.append(write(rel_dir, page))
        author_entries.append((a, slugify(a), len(items)))

    paths.append(write(*build_index("generi", genre_entries)))
    paths.append(write(*build_index("autori", sorted(author_entries, key=lambda x: x[0].lower()))))

    (ROOT / "sitemap.xml").write_text(build_sitemap(paths), encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")

    print(f"books={len(valid)}  genre_hubs={len(genre_entries)}  author_hubs={len(author_entries)}  "
          f"indexes=2  sitemap_urls={len(paths) + 1}")


if __name__ == "__main__":
    main()
