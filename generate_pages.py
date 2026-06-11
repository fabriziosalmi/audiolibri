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

# Fonts are self-hosted via @font-face in app.css (no third-party calls); just preload.
FONTS = ('<link rel="preload" href="/fonts/inter-latin.woff2" as="font" type="font/woff2" crossorigin>'
         '<link rel="preload" href="/fonts/fraunces-latin.woff2" as="font" type="font/woff2" crossorigin>')

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

# Display title disambiguates multi-part series ("Figlia del mare — Capitolo 12").
# IMPORTANT: book_slug() uses title_of() (the series name), NOT this — so adding a
# part suffix changes the visible/<title>/<h1> text but never the page URL.
def display_title_of(b):
    pd = (b.get("part_display") or "").strip()
    return f"{title_of(b)} — {pd}" if pd else title_of(b)


def book_slug(b) -> str:
    vid = video_id(b)
    return f"{slugify(title_of(b))}-{vid}" if vid else f"{slugify(title_of(b))}-{b.get('id', '')}"


def meta_description(text: str, limit: int = 155) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "…"


PAGE_CSS = """<style>
.bp-wrap { max-width: 980px; margin: 0 auto; padding: clamp(1rem,3vw,2rem) 0 0; }
.bp-crumbs { font-size:var(--text-sm); color:var(--secondary-text); margin-bottom:1.25rem; }
.bp-crumbs a { color:var(--secondary-text); text-decoration:none; }
.bp-crumbs a:hover { color:var(--primary-color); }
.bp-eyebrow { text-transform:uppercase; letter-spacing:.16em; font-size:var(--text-xs); font-weight:700; color:var(--primary-color); }
.bp-title { font-family:var(--font-display); font-size:clamp(2rem,5vw,3.2rem); font-weight:600; line-height:1.05; margin:.3rem 0 .4rem; color:var(--header-color); -webkit-text-fill-color:var(--header-color); background:none; }
.bp-author { font-size:var(--text-lg); color:var(--secondary-text); margin:0 0 1rem; }
.bp-author b { color:var(--text-color); } .bp-author a { color:inherit; }
.bp-series { font-size:var(--text-sm); margin:-.4rem 0 1rem; color:var(--secondary-text); }
.bp-series a { color:var(--primary-color); text-decoration:none; font-weight:600; }
.bp-series a:hover { text-decoration:underline; }
.bp-chips { display:flex; flex-wrap:wrap; gap:.5rem; margin-bottom:1.5rem; }
.bp-chip { padding:.25rem .8rem; border-radius:var(--radius-pill); background:rgba(var(--primary-rgb),.1); color:var(--primary-color); font-size:var(--text-xs); font-weight:600; text-decoration:none; }
.bp-player { aspect-ratio:16/9; width:100%; max-width:760px; border:0; border-radius:var(--radius-lg); overflow:hidden; box-shadow:var(--card-shadow); margin-bottom:2rem; background:#000; }
.bp-synopsis h2, .bp-faqs h2 { font-family:var(--font-display); font-size:var(--text-2xl); margin:0 0 .8rem; }
.bp-synopsis p { font-size:var(--text-lg); line-height:1.7; max-width:70ch; }
.bp-faqs { margin-top:2.5rem; }
.bp-faq { border-bottom:1px solid var(--border-color); padding:.9rem 0; }
.bp-faq summary { cursor:pointer; font-weight:600; }
.bp-faq p { color:var(--secondary-text); margin:.6rem 0 0; }
.bp-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(170px,1fr)); gap:var(--space-5) var(--space-4); margin-top:1.5rem; }
.bp-grid .nf-card { width:auto; }
.bp-lead { font-size:var(--text-lg); color:var(--secondary-text); max-width:70ch; }
.bp-back { display:inline-block; margin-top:2.5rem; color:var(--primary-color); text-decoration:none; font-weight:600; }
a.bp-chip { text-decoration:none; transition:background-color .2s; }
a.bp-chip:hover { background:rgba(var(--primary-rgb),.2); }
.bp-related { margin-top:2.5rem; }
.bp-related h2 { font-family:var(--font-display); font-size:var(--text-2xl); margin:0 0 .8rem; }
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
<meta name="referrer" content="strict-origin-when-cross-origin">
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
  <div class="site-brand"><a href="/" aria-label="Audiolibri.org — home"><img src="/audiobooks_transparent.png" alt="" width="32" height="32"><span>audiolibri.org</span></a></div>
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
    return (head_html + '\n<body>\n<a href="#main-content" class="skip-link">Salta al contenuto</a>\n<div class="container ios-safe-inset">\n'
            + header_html() + "\n<main id=\"main-content\">\n" + main_html
            + "\n</main>\n" + footer_html() + "\n</div>\n"
            + (FALLBACK_SCRIPT if with_fallback else "") + "\n</body>\n</html>")


def card_link(b) -> str:
    vid = video_id(b)
    t, a = display_title_of(b), author_of(b)
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


def build_book_page(b: dict, related=(), in_series=False, series_name=None):
    vid = video_id(b)
    title, author, genre = display_title_of(b), author_of(b), genre_of(b)
    synopsis = (b.get("real_synopsis") or b.get("description") or "").strip()
    channel = (b.get("channel") or "").strip()
    dur, views, likes = b.get("duration") or 0, b.get("view_count") or 0, b.get("like_count") or 0
    published = iso_date(b.get("upload_date", ""))
    cover = f"https://i.ytimg.com/vi/{vid}/maxresdefault.jpg" if vid else b.get("thumbnail", "")
    rel_dir = f"audiolibro/{book_slug(b)}"
    canonical = f"{SITE}/{rel_dir}/"
    embed_type = b.get("embed_type", "youtube" if vid else "audio")
    embed_url = b.get("embed_url", f"https://www.youtube-nocookie.com/embed/{vid}" if vid else "")
    audio_url = b.get("audio_url", b.get("audio_file", ""))
    audio_chapters = b.get("audio_chapters", [])
    source = b.get("source", "youtube" if vid else "unknown")
    source_url = b.get("url", "")
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
    if embed_url:
        audiobook["associatedMedia"] = {"@type": "AudioObject", "contentUrl": b.get("url", ""),
                                         "embedUrl": embed_url, "duration": iso_duration(dur)}
    stats = []
    if views: stats.append({"@type": "InteractionCounter", "interactionType": "https://schema.org/ListenAction", "userInteractionCount": views})
    if likes: stats.append({"@type": "InteractionCounter", "interactionType": "https://schema.org/LikeAction", "userInteractionCount": likes})
    if stats: audiobook["interactionStatistic"] = stats

    series_name = (series_name or b.get("series") or "").strip()
    part = b.get("part")
    series_slug = slugify(series_name) if (in_series and series_name) else ""
    if series_slug:
        audiobook["partOfSeries"] = {"@type": "BookSeries", "name": series_name, "url": f"{SITE}/serie/{series_slug}/"}
        if part is not None:
            audiobook["position"] = part

    crumbs = [{"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"}]
    if genre_label:
        crumbs.append({"@type": "ListItem", "position": len(crumbs) + 1, "name": genre_label, "item": f"{SITE}/genere/{slugify(genre)}/"})
    if series_slug:
        crumbs.append({"@type": "ListItem", "position": len(crumbs) + 1, "name": series_name, "item": f"{SITE}/serie/{series_slug}/"})
    crumbs.append({"@type": "ListItem", "position": len(crumbs) + 1, "name": title, "item": canonical})
    breadcrumb = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": crumbs}
    faqpage = {"@context": "https://schema.org", "@type": "FAQPage",
               "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}

    chips = ""
    if genre_label:
        chips += f'<a class="bp-chip" href="/genere/{slugify(genre)}/">{e(genre_label)}</a>'
    if dur:
        chips += f'<span class="bp-chip">{e(human_duration(dur))}</span>'
    if views:
        chips += f'<span class="bp-chip">{e(f"{views:,}".replace(",", ".") + " ascolti")}</span>'
    related_html = ""
    if related:
        related_cards = "".join(card_link(rb) for rb in related)
        related_html = f'<section class="bp-related"><h2>Da ascoltare dopo</h2><div class="bp-grid">{related_cards}</div></section>'
    faq_html = "".join(f'<details class="bp-faq"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in faq)
    crumb_html = ('<a href="/">Home</a>'
                  + (f' › <a href="/genere/{slugify(genre)}/">{e(genre_label)}</a>' if genre_label else '')
                  + (f' › <a href="/serie/{series_slug}/">{e(series_name)}</a>' if series_slug else '')
                  + f' › <span>{e(title)}</span>')
    series_link_html = f'\n    <p class="bp-series">Parte di <a href="/serie/{series_slug}/">«{e(series_name)}»</a></p>' if series_slug else ''
    player = ""
    if embed_type == "youtube" and vid:
        player = (f'<iframe class="bp-player" src="{e(embed_url)}" title="Audiolibro: {e(title)}" loading="lazy" '
                  'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
                  'allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>')
    elif embed_type == "iframe" and embed_url:
        player = (f'<iframe class="bp-player" src="{e(embed_url)}" title="Audiolibro: {e(title)}" loading="lazy" '
                  'style="border:0;" allowfullscreen referrerpolicy="strict-origin-when-cross-origin"></iframe>')
    elif embed_type == "link_out":
        btn_label = "Ascolta su Spotify" if source == "spotify" else f"Ascolta su {source.capitalize()}"
        btn_color = "#1DB954" if source == "spotify" else "var(--primary-color)"
        player = f"""
        <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; background:rgba(255,255,255,0.03); border:1px dashed var(--border-color); border-radius:var(--radius-lg); padding:2.5rem; text-align:center; margin-bottom:2rem; width:100%;">
            <p style="margin:0 0 1.25rem; font-size:var(--text-lg); color:var(--secondary-text);">Questo audiolibro è disponibile esternamente su {e(source.capitalize())}.</p>
            <a class="ios-button" href="{e(source_url)}" target="_blank" rel="noopener noreferrer" style="text-decoration:none; display:inline-flex; align-items:center; gap:0.5rem; color:white; font-weight:600; background-color:{btn_color};">
                {e(btn_label)}
            </a>
        </div>
        """
    elif embed_type == "audio" and audio_url:
        chapters_list_html = ""
        script_html = ""
        if audio_chapters and len(audio_chapters) > 1:
            chapters_li = []
            for idx, ch in enumerate(audio_chapters):
                ch_title = ch.get("title") or f"Capitolo {idx+1}"
                ch_url = ch.get("audio_url")
                ch_dur = ch.get("duration") or 0
                ch_dur_str = human_duration(ch_dur) if ch_dur else ""
                
                chapters_li.append(f"""
                <li style="display:flex; justify-content:space-between; align-items:center; padding:0.6rem 0.8rem; border:1px solid var(--border-color); border-radius:var(--radius-md); background:var(--hover-overlay); gap:1rem;">
                    <span style="font-weight:600; font-size:var(--text-sm);">{e(ch_title)}</span>
                    <div style="display:flex; gap:0.5rem; align-items:center;">
                        {f'<span style="font-size:var(--text-xs); color:var(--secondary-text); margin-right:0.5rem;">{e(ch_dur_str)}</span>' if ch_dur_str else ''}
                        <button onclick="playChapter('{e(ch_url)}', '{e(ch_title)}')" class="index-item" style="padding:0.25rem 0.7rem; font-size:var(--text-xs); margin:0; cursor:pointer; background:var(--background-color);">Ascolta</button>
                        <a href="{e(ch_url)}" target="_blank" rel="noopener noreferrer" class="index-item" style="padding:0.25rem 0.7rem; font-size:var(--text-xs); margin:0; text-decoration:none; background:var(--background-color);">Apri</a>
                    </div>
                </li>
                """)
            
            chapters_list_html = f"""
            <div class="bp-chapters" style="margin-top:2rem; border-top:1px solid var(--border-color); padding-top:1.5rem;">
                <h2 style="font-family:var(--font-display); font-size:var(--text-xl); margin-bottom:1rem;" id="active-chapter-title">Capitoli</h2>
                <ul class="chapters-list" style="list-style:none; padding:0; margin:0; display:flex; flex-direction:column; gap:0.6rem;">
                    {"".join(chapters_li)}
                </ul>
            </div>
            """
            
            script_html = """
            <script>
            function playChapter(url, title) {
                var player = document.getElementById('audio-player-static');
                if (player) {
                    player.src = url;
                    player.play().catch(function(err) { console.log('Autoplay blocked:', err); });
                }
                var titleEl = document.getElementById('active-chapter-title');
                if (titleEl) {
                    titleEl.textContent = 'Ora in riproduzione: ' + title;
                }
            }
            </script>
            """
            
        player = f"""
        <audio id="audio-player-static" class="bp-player" style="height:54px; width:100%; border-radius:var(--radius-md); margin-bottom:1rem;" controls preload="metadata">
            <source src="{e(audio_url)}" type="audio/mpeg">
            Il tuo browser non supporta l'elemento audio.
        </audio>
        {script_html}
        {chapters_list_html}
        """

    main_html = f"""<div class="bp-wrap">
    <nav class="bp-crumbs" aria-label="Breadcrumb">{crumb_html}</nav>
    <p class="bp-eyebrow">Audiolibro gratis</p>
    <h1 class="bp-title">{e(title)}</h1>
    <p class="bp-author">di <b><a href="/autore/{slugify(author)}/">{e(author)}</a></b></p>{series_link_html}
    <div class="bp-chips">{chips}</div>
    {player}
    <section class="bp-synopsis"><h2>Trama</h2><p>{e(synopsis)}</p></section>
    <section class="bp-faqs"><h2>Domande frequenti</h2>{faq_html}</section>
    {related_html}
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
                "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{SITE}/audiolibro/{book_slug(b)}/", "name": display_title_of(b)}
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


def build_series(name, chapters):
    """A multi-part audiobook: one page listing its chapters in reading order."""
    chapters = sorted(chapters, key=lambda b: b.get("part") or 0)
    slug = slugify(name)
    rel_dir = f"serie/{slug}"
    canonical = f"{SITE}/{rel_dir}/"
    lead = f"Tutti i {len(chapters)} capitoli di «{name}» da ascoltare gratis, in ordine."
    page_title = f"{name} — audiolibro completo gratis, {len(chapters)} capitoli | Audiolibri.org"
    itemlist = {"@context": "https://schema.org", "@type": "ItemList", "name": name, "numberOfItems": len(chapters),
                "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{SITE}/audiolibro/{book_slug(b)}/", "name": display_title_of(b)}
                                    for i, b in enumerate(chapters)]}
    breadcrumb = {"@context": "https://schema.org", "@type": "BreadcrumbList",
                  "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                                      {"@type": "ListItem", "position": 2, "name": "Serie", "item": f"{SITE}/serie/"},
                                      {"@type": "ListItem", "position": 3, "name": name, "item": canonical}]}
    grid = "".join(card_link(b) for b in chapters)
    main_html = f"""<div class="bp-wrap">
    <nav class="bp-crumbs" aria-label="Breadcrumb"><a href="/">Home</a> › <a href="/serie/">Serie</a> › <span>{e(name)}</span></nav>
    <p class="bp-eyebrow">Audiolibro a puntate</p>
    <h1 class="bp-title">{e(name)}</h1>
    <p class="bp-lead">{e(lead)}</p>
    <div class="bp-grid">{grid}</div>
    <a class="bp-back" href="/serie/">← Tutte le serie</a>
  </div>"""
    head_html = head(page_title, meta_description(lead), canonical, "", "website", (itemlist, breadcrumb))
    return rel_dir, shell(head_html, main_html, with_fallback=True)


def build_index(kind, entries):
    """entries: list of (label, slug, count). kind in {generi, autori, serie}."""
    rel_dir = kind
    canonical = f"{SITE}/{rel_dir}/"
    if kind == "generi":
        h1, sub = "Generi", "genere"
        lead = f"Esplora gli audiolibri italiani gratuiti per genere — {len(entries)} categorie."
    elif kind == "autori":
        h1, sub = "Autori", "autore"
        lead = f"Esplora gli audiolibri italiani gratuiti per autore — {len(entries)} autori."
    else:  # serie
        h1, sub = "Serie", "serie"
        lead = f"Audiolibri a puntate, da ascoltare capitolo per capitolo — {len(entries)} serie."
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


def related_for(b, authors, genres, limit=12):
    """Pick related titles for a book page: same author first, then same genre."""
    seen = {b.get("id")}
    out = []

    def add_from(pool):
        for rb in sorted(pool, key=lambda x: x.get("view_count") or 0, reverse=True):
            rid = rb.get("id")
            if rid and rid not in seen:
                seen.add(rid)
                out.append(rb)
                if len(out) >= limit:
                    return True
        return False

    a = author_of(b)
    if a and a != "Autore sconosciuto" and add_from(authors.get(a, [])):
        return out
    g = genre_of(b)
    if g:
        add_from(genres.get(g, []))
    return out


def main():
    books = json.loads(DATA.read_text())
    for k, b in books.items():
        b["id"] = k
    valid = [b for b in books.values() if (video_id(b) or b.get("audio_url") or b.get("audio_file") or b.get("embed_url") or b.get("embed_type") == "link_out")]

    # Group once: drives both the hub pages and the "related" lists on book pages.
    genres, authors = {}, {}
    for b in valid:
        g = genre_of(b)
        if g:
            genres.setdefault(g, []).append(b)
        authors.setdefault(author_of(b), []).append(b)

    # Multi-part series get their own page. Group by SLUG (case/spacing-insensitive)
    # so casing variants of one title ("L'innocenza"/"L'Innocenza") merge into a
    # single page instead of colliding on the same /serie/<slug>/ URL.
    series_groups = {}  # slug -> {"names": {name: count}, "chapters": [...]}
    for b in valid:
        s = (b.get("series") or "").strip()
        if s and b.get("part") is not None:
            sl = slugify(s)
            g = series_groups.setdefault(sl, {"names": {}, "chapters": []})
            g["names"][s] = g["names"].get(s, 0) + 1
            g["chapters"].append(b)
    series_groups = {sl: g for sl, g in series_groups.items() if len(g["chapters"]) >= 2}
    multi_series_slugs = set(series_groups)
    series_name_by_slug = {sl: max(g["names"], key=g["names"].get) for sl, g in series_groups.items()}

    def series_args(b):
        sl = slugify((b.get("series") or "").strip()) if (b.get("series") and b.get("part") is not None) else ""
        return (sl in multi_series_slugs), series_name_by_slug.get(sl)

    if len(sys.argv) > 1 and sys.argv[1] != "all":
        vid = sys.argv[1]
        if vid not in books:
            sys.exit(f"id {vid} not found")
        b = books[vid]
        in_s, sname = series_args(b)
        rel_dir, page = build_book_page(b, related_for(b, authors, genres), in_series=in_s, series_name=sname)
        print("wrote", write(rel_dir, page))
        return

    paths = []
    for b in valid:
        in_s, sname = series_args(b)
        rel_dir, page = build_book_page(b, related_for(b, authors, genres), in_series=in_s, series_name=sname)
        paths.append(write(rel_dir, page))

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

    series_entries = []
    for sl, g in sorted(series_groups.items(), key=lambda kv: len(kv[1]["chapters"]), reverse=True):
        name = series_name_by_slug[sl]
        rel_dir, page = build_series(name, g["chapters"])
        paths.append(write(rel_dir, page))
        series_entries.append((name, sl, len(g["chapters"])))

    paths.append(write(*build_index("generi", genre_entries)))
    paths.append(write(*build_index("autori", sorted(author_entries, key=lambda x: x[0].lower()))))
    if series_entries:
        paths.append(write(*build_index("serie", sorted(series_entries, key=lambda x: x[0].lower()))))

    (ROOT / "sitemap.xml").write_text(build_sitemap(paths), encoding="utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")

    print(f"books={len(valid)}  genre_hubs={len(genre_entries)}  author_hubs={len(author_entries)}  "
          f"series={len(series_entries)}  indexes={2 + (1 if series_entries else 0)}  sitemap_urls={len(paths) + 1}")


if __name__ == "__main__":
    main()
