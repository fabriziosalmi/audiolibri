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
# Click-to-load. Nothing is requested from the embed provider until a visitor
# asks for the recording: the request becomes the consent, and the site needs
# no banner to ask for something it never does unprompted.
FACADE_SCRIPT = """<script>
(function () {
  document.addEventListener('click', function (ev) {
    var btn = ev.target.closest ? ev.target.closest('.bp-facade-play') : null;
    if (!btn) return;
    var box = btn.closest('.bp-facade');
    var src = box && box.getAttribute('data-embed');
    if (!src) return;
    var frame = document.createElement('iframe');
    frame.className = 'bp-player';
    frame.src = src + (src.indexOf('?') === -1 ? '?' : '&') + 'autoplay=1';
    frame.title = box.getAttribute('data-title') || '';
    var allow = box.getAttribute('data-allow');
    if (allow) frame.setAttribute('allow', allow);
    frame.setAttribute('allowfullscreen', '');
    frame.setAttribute('referrerpolicy', 'strict-origin-when-cross-origin');
    box.replaceWith(frame);
    frame.focus();
  });
})();
</script>"""

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
.bp-facade { position:relative; aspect-ratio:16/9; width:100%; max-width:760px; border-radius:var(--radius-lg); overflow:hidden; box-shadow:var(--card-shadow); margin-bottom:2rem; background:linear-gradient(140deg,#1b1b20,#0b0b0e); display:flex; flex-direction:column; align-items:center; justify-content:center; gap:1rem; padding:1.5rem; text-align:center; }
.bp-facade-play { width:74px; height:74px; border-radius:50%; border:0; cursor:pointer; background:var(--primary-color); color:#fff; display:flex; align-items:center; justify-content:center; box-shadow:0 6px 24px rgba(0,0,0,.45); transition:transform .15s ease; }
.bp-facade-play:hover, .bp-facade-play:focus-visible { transform:scale(1.07); }
.bp-facade-play svg { width:30px; height:30px; margin-left:4px; fill:currentColor; }
.bp-facade-note { margin:0; max-width:52ch; font-size:var(--text-xs); line-height:1.5; color:rgba(255,255,255,.72); }
.bp-facade-note a { color:#fff; }
.bp-player { aspect-ratio:16/9; width:100%; max-width:760px; border:0; border-radius:var(--radius-lg); overflow:hidden; box-shadow:var(--card-shadow); margin-bottom:2rem; background:#000; }
.bp-synopsis h2, .bp-faqs h2 { font-family:var(--font-display); font-size:var(--text-2xl); margin:0 0 .8rem; }
.bp-synopsis p { font-size:var(--text-lg); line-height:1.7; max-width:70ch; }
.bp-ai-note { font-size:var(--text-sm); line-height:1.55; max-width:70ch; opacity:.72; border-left:3px solid currentColor; padding-left:.75rem; margin-top:.9rem; }
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
.bp-facts-wrap { margin-top:2.2rem; }
.bp-facts-wrap h2 { font-family:var(--font-display); font-size:var(--text-2xl); margin:0 0 .8rem; }
.bp-facts { display:grid; grid-template-columns:repeat(auto-fill,minmax(190px,1fr)); gap:.7rem 1.6rem; margin:0; }
.bp-fact { border-bottom:1px solid var(--border-color); padding:.4rem 0; }
.bp-fact dt { font-size:var(--text-xs); text-transform:uppercase; letter-spacing:.06em; color:var(--secondary-text); }
.bp-fact dd { margin:.15rem 0 0; font-weight:600; color:var(--text-color); }
.bp-fact dd a { color:var(--primary-color); text-decoration:none; }
.bp-authorbio { font-size:var(--text-lg); line-height:1.7; color:var(--secondary-text); max-width:72ch; margin:.2rem 0 1.8rem; }
</style>"""


def head(title, description, canonical, image, og_type="website", extra_ld=(), noindex=False):
    ld = "".join('<script type="application/ld+json">\n'
                 + json.dumps(o, ensure_ascii=False, indent=2) + "\n</script>\n" for o in extra_ld)
    img = (f'<meta property="og:image" content="{e(image)}">\n'
           f'<meta name="twitter:image" content="{e(image)}">') if image else ""
    robots = "noindex, follow" if noindex else "index, follow, max-image-preview:large"
    return f"""<!DOCTYPE html>
<html lang="it">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="referrer" content="strict-origin-when-cross-origin">
<title>{e(title)}</title>
<meta name="description" content="{e(description)}">
<meta name="robots" content="{robots}">
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
        <a class="footer-link" href="/privacy.html">Privacy</a>
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


def thumb_local(vid, w, absolute=False):
    """Local self-hosted cover path (WebP), replacing the i.ytimg.com URL. Falls
    back to the placeholder when the thumbnail was not fetched, so the browser
    never contacts Google and never gets a 404."""
    if vid and (ROOT / f"assets/thumbs/{vid}-{w}.webp").exists():
        rel = f"/assets/thumbs/{vid}-{w}.webp"
    else:
        rel = f"/assets/thumbs/placeholder-{w}.webp"
    return f"{SITE}{rel}" if absolute else rel


def card_link(b) -> str:
    vid = video_id(b)
    t, a = display_title_of(b), author_of(b)
    hue = sum(ord(c) for c in (vid or t)) % 360
    thumb = thumb_local(vid, 320)
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


# Short original biographies (public-domain facts) for well-known authors, used
# on /autore/<slug>/ hubs for E-E-A-T. Keyed by a lowercase substring of the name
# so variants ("H.P. Lovecraft" / "Howard Phillips Lovecraft") both match.
AUTHOR_BIOS = {
    "pirandello": "Luigi Pirandello (1867–1936) è stato uno dei massimi narratori e drammaturghi italiani, premio Nobel per la letteratura nel 1934. La sua opera indaga l'identità e il contrasto tra vita e «maschera», da «Il fu Mattia Pascal» a «Uno, nessuno e centomila».",
    "verga": "Giovanni Verga (1840–1922), scrittore siciliano, è il maggiore esponente del Verismo italiano. Con «I Malavoglia» e le novelle di «Vita dei campi» raccontò con crudo realismo il mondo dei vinti.",
    "annunzio": "Gabriele D'Annunzio (1863–1938) fu poeta, romanziere e drammaturgo, figura dominante dell'Estetismo e del Decadentismo italiano, celebre per la ricerca formale e il culto della «vita inimitabile».",
    "manzoni": "Alessandro Manzoni (1785–1873) è l'autore de «I Promessi Sposi», il romanzo che ha fondato la lingua letteraria italiana moderna, unendo fede, storia e attenzione agli umili.",
    "leopardi": "Giacomo Leopardi (1798–1837) è tra i più grandi poeti e pensatori italiani. I «Canti» e le «Operette morali» esprimono, con altissima musicalità, la sua riflessione sul dolore e sull'infinito.",
    "dante": "Dante Alighieri (1265–1321), padre della lingua italiana, è l'autore della «Divina Commedia», il poema che attraversa Inferno, Purgatorio e Paradiso ed è pietra angolare della letteratura mondiale.",
    "boccaccio": "Giovanni Boccaccio (1313–1375) è l'autore del «Decameron», raccolta di cento novelle che ritrae con arguzia la società del Trecento e segna la nascita della prosa narrativa europea.",
    "collodi": "Carlo Collodi (1826–1890), pseudonimo di Carlo Lorenzini, è l'autore de «Le avventure di Pinocchio», tra i libri per l'infanzia più letti e tradotti al mondo.",
    "de amicis": "Edmondo De Amicis (1846–1908), scrittore e giornalista, è celebre soprattutto per «Cuore», il libro che ha accompagnato generazioni di studenti italiani.",
    "svevo": "Italo Svevo (1861–1928), scrittore triestino, è l'autore de «La coscienza di Zeno», romanzo pioniere dell'introspezione psicologica nella narrativa italiana.",
    "deledda": "Grazia Deledda (1871–1936), scrittrice sarda, fu premio Nobel per la letteratura nel 1926. I suoi romanzi ritraggono con intensità la Sardegna e i suoi conflitti morali.",
    "poe": "Edgar Allan Poe (1809–1849), scrittore statunitense, è maestro del racconto gotico e inventore del racconto poliziesco, celebre per «Il gatto nero», «Il pozzo e il pendolo» e la poesia «Il corvo».",
    "lovecraft": "Howard Phillips Lovecraft (1890–1937), scrittore statunitense, è il padre dell'«orrore cosmico». Il suo universo, dominato da entità come Cthulhu, ha influenzato profondamente la narrativa horror e fantastica.",
    "wilde": "Oscar Wilde (1854–1900), scrittore e drammaturgo irlandese dell'Estetismo, è autore de «Il ritratto di Dorian Gray» e di commedie brillanti come «L'importanza di chiamarsi Ernesto».",
    "dickens": "Charles Dickens (1812–1870) è tra i più grandi narratori inglesi dell'età vittoriana. Con «Oliver Twist» e «Canto di Natale» denunciò le ingiustizie sociali del suo tempo.",
    "stevenson": "Robert Louis Stevenson (1850–1894), scrittore scozzese, è autore di classici dell'avventura e del fantastico come «L'isola del tesoro» e «Lo strano caso del dottor Jekyll e del signor Hyde».",
    "conan doyle": "Arthur Conan Doyle (1859–1930), scrittore britannico, ha creato Sherlock Holmes, il più celebre detective della letteratura, protagonista di romanzi e racconti tradotti in tutto il mondo.",
    "bram stoker": "Bram Stoker (1847–1912), scrittore irlandese, è autore di «Dracula», il romanzo che ha fissato l'immaginario moderno del vampiro.",
    "mary shelley": "Mary Shelley (1797–1851), scrittrice inglese, con «Frankenstein» ha dato origine alla fantascienza moderna, interrogandosi sui limiti della scienza e sulla responsabilità del creatore.",
    "twain": "Mark Twain (1835–1910), pseudonimo di Samuel Clemens, è tra i padri della letteratura statunitense, autore de «Le avventure di Tom Sawyer» e «Huckleberry Finn».",
    "jack london": "Jack London (1876–1916), scrittore statunitense, è celebre per i romanzi d'avventura ambientati nella natura selvaggia, come «Il richiamo della foresta» e «Zanna Bianca».",
    "kafka": "Franz Kafka (1883–1924), scrittore boemo di lingua tedesca, è autore di opere come «La metamorfosi» e «Il processo», emblemi dell'angoscia e dell'assurdo della condizione moderna.",
    "maupassant": "Guy de Maupassant (1850–1893), maestro francese del racconto, ha lasciato centinaia di novelle di straordinaria efficacia, dal realismo al fantastico, come «Le Horla» e «Palla di sego».",
    "verne": "Jules Verne (1828–1905), scrittore francese, è considerato il padre della fantascienza per romanzi visionari come «Ventimila leghe sotto i mari» e «Il giro del mondo in 80 giorni».",
    "victor hugo": "Victor Hugo (1802–1885), gigante del Romanticismo francese, è autore de «I miserabili» e «Notre-Dame de Paris», affreschi potenti di giustizia sociale e umanità.",
    "dostoevskij": "Fëdor Dostoevskij (1821–1881), tra i massimi romanzieri russi, ha esplorato le profondità morali e psicologiche dell'uomo in «Delitto e castigo» e «I fratelli Karamazov».",
    "tolstoj": "Lev Tolstoj (1828–1910), scrittore russo, è autore dei monumentali «Guerra e pace» e «Anna Karenina», tra i vertici del romanzo realista di ogni tempo.",
    "cechov": "Anton Čechov (1860–1904), scrittore e drammaturgo russo, è maestro del racconto moderno e del teatro, capace di cogliere con delicatezza le sfumature dell'animo umano.",
    "kipling": "Rudyard Kipling (1865–1936), scrittore britannico, premio Nobel nel 1907, è celebre per «Il libro della giungla» e per i racconti ambientati nell'India coloniale.",
    "carroll": "Lewis Carroll (1832–1898), pseudonimo di Charles Dodgson, matematico e scrittore inglese, è autore di «Alice nel Paese delle Meraviglie», capolavoro del nonsense.",
}


def author_bio(author):
    a = (author or "").lower()
    for key, bio in AUTHOR_BIOS.items():
        if key in a:
            return bio
    return ""


def build_book_page(b: dict, related=(), in_series=False, series_name=None):
    vid = video_id(b)
    replacement = EMBED_REPLACEMENTS.get(vid)
    embed_vid = replacement or vid  # the id the PLAYER loads; slug/URL stay on `vid`
    estatus = None if replacement else EMBED_STATUS.get(vid)  # a replacement fixes the break
    title, author, genre = display_title_of(b), author_of(b), genre_of(b)
    # real_synopsis is written by augment.py / synopsis_reprocessor.py, which
    # ask a local language model to rewrite the source material. When it is
    # missing we fall back to the channel's own description, which is not
    # generated - so the notice below is only shown when it actually applies.
    synopsis = (b.get("real_synopsis") or "").strip()
    synopsis_is_generated = bool(synopsis)
    if not synopsis:
        synopsis = (b.get("description") or "").strip()
    channel = (b.get("channel") or "").strip()
    dur, views, likes = b.get("duration") or 0, b.get("view_count") or 0, b.get("like_count") or 0
    published = iso_date(b.get("upload_date", ""))
    cover = thumb_local(embed_vid, 640, absolute=True)
    rel_dir = f"audiolibro/{book_slug(b)}"
    canonical = f"{SITE}/{rel_dir}/"
    embed_type = b.get("embed_type", "youtube" if vid else "audio")
    embed_url = (f"https://www.youtube-nocookie.com/embed/{embed_vid}" if replacement
                 else b.get("embed_url", f"https://www.youtube-nocookie.com/embed/{vid}" if vid else ""))
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
    if embed_url and not estatus:
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
    # NB: no FAQPage JSON-LD — Google retired FAQ rich results (May 2026), so the
    # markup only bloated the HTML. The visible FAQ section below is kept (useful
    # content for users and AI answer engines).

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

    # Factual "Scheda" block: real, per-title data (reader, year, language, ...)
    # that gives thin pages unique substance without inventing prose.
    facts = [("Autore", f'<a href="/autore/{slugify(author)}/">{e(author)}</a>')]
    if channel: facts.append(("Lettore", e(channel)))
    if genre_label: facts.append(("Genere", f'<a href="/genere/{slugify(genre)}/">{e(genre_label)}</a>'))
    if series_slug: facts.append(("Serie", f'<a href="/serie/{series_slug}/">{e(series_name)}</a>'))
    if dur: facts.append(("Durata", e(human_duration(dur))))
    if published: facts.append(("Anno", e(published[:4])))
    facts.append(("Lingua", "Italiano"))
    if views: facts.append(("Ascolti", e(f"{views:,}".replace(",", "."))))
    facts.append(("Disponibilità", "Gratis, in streaming"))
    facts_html = "".join(f'<div class="bp-fact"><dt>{lbl}</dt><dd>{val}</dd></div>' for lbl, val in facts)
    facts_section = f'<section class="bp-facts-wrap"><h2>Scheda</h2><dl class="bp-facts">{facts_html}</dl></section>'
    faq_html = "".join(f'<details class="bp-faq"><summary>{e(q)}</summary><p>{e(a)}</p></details>' for q, a in faq)
    # Trama, titolo, autore e genere non sono scritti da noi né presi dalla
    # fonte: li ricava un modello linguistico dal materiale del canale. Chi
    # legge deve poterlo sapere lì, accanto al testo, non solo nell'informativa.
    ai_notice = ('<p class="bp-ai-note">Trama, titolo, autore e genere di questa scheda sono '
                 'stati generati automaticamente da un modello linguistico a partire dal '
                 'materiale pubblicato dal canale. Possono contenere errori: l\'audio è '
                 'sempre la fonte attendibile.</p>') if synopsis_is_generated else ''
    crumb_html = ('<a href="/">Home</a>'
                  + (f' › <a href="/genere/{slugify(genre)}/">{e(genre_label)}</a>' if genre_label else '')
                  + (f' › <a href="/serie/{series_slug}/">{e(series_name)}</a>' if series_slug else '')
                  + f' › <span>{e(title)}</span>')
    series_link_html = f'\n    <p class="bp-series">Parte di <a href="/serie/{series_slug}/">«{e(series_name)}»</a></p>' if series_slug else ''
    def facade(url: str, allow: str, provider: str, watch_url: str = "") -> str:
        """A play control that loads nothing until it is pressed.

        The embed is what makes this site need a consent banner: it contacts the
        provider, and sets its cookies, before the visitor has asked for
        anything. Deferring it to an explicit press turns the request into the
        act of asking, and the banner becomes unnecessary rather than merely
        compliant.
        """
        fallback = (f'<noscript><p class="bp-facade-note">Attiva JavaScript oppure '
                    f'<a href="{e(watch_url or url)}" rel="noopener noreferrer" target="_blank">'
                    f'apri l\'audiolibro su {e(provider)}</a>.</p></noscript>') if (watch_url or url) else ""
        return (f'<div class="bp-facade" data-embed="{e(url)}" data-title="Audiolibro: {e(title)}" '
                f'data-allow="{e(allow)}">'
                f'<button type="button" class="bp-facade-play" aria-label="Riproduci: {e(title)}">'
                f'<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M8 5v14l11-7z"/></svg>'
                f'</button>'
                f'<p class="bp-facade-note">Premi play per caricare il lettore. Solo allora '
                f'{e(provider)} riceve il tuo indirizzo IP e puo\u0300 impostare cookie. '
                f'Fino a quel momento questa pagina non contatta alcun servizio esterno: '
                f'copertina, testo e risorse sono serviti da audiolibri.org.</p>'
                f'{fallback}</div>{FACADE_SCRIPT}')

    player = ""
    if estatus in (401, 403):
        player = (f'<div style="display:flex; flex-direction:column; align-items:center; justify-content:center; background:rgba(255,255,255,0.03); border:1px dashed var(--border-color); border-radius:var(--radius-lg); padding:2.5rem; text-align:center; margin-bottom:2rem; width:100%;">'
                  f'<p style="margin:0 0 1.25rem; font-size:var(--text-lg); color:var(--secondary-text);">L\'incorporamento è stato disattivato dal canale, ma puoi ascoltare «{e(title)}» gratis su YouTube.</p>'
                  f'<a class="ios-button" href="https://www.youtube.com/watch?v={e(vid)}" target="_blank" rel="noopener noreferrer" style="text-decoration:none; display:inline-flex; align-items:center; gap:0.5rem; color:white; font-weight:600; background-color:#FF0000;">▶ Ascolta su YouTube</a>'
                  f'</div>')
    elif estatus == 404:
        player = (f'<div style="display:flex; flex-direction:column; align-items:center; justify-content:center; background:rgba(255,255,255,0.03); border:1px dashed var(--border-color); border-radius:var(--radius-lg); padding:2.5rem; text-align:center; margin-bottom:2rem; width:100%;">'
                  f'<p style="margin:0; font-size:var(--text-lg); color:var(--secondary-text);">Questo audiolibro non è più disponibile alla fonte. Trovi tanti altri titoli qui sotto e nella <a href="/">libreria completa</a>.</p>'
                  f'</div>')
    elif embed_type == "youtube" and vid:
        player = facade(
            embed_url,
            "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture",
            "YouTube",
            f"https://www.youtube.com/watch?v={embed_vid}",
        )
    elif embed_type == "iframe" and embed_url:
        allow = "autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share" if source == "facebook" else ""
        player = facade(embed_url, allow, source.capitalize(), source_url)
    elif embed_type == "link_out":
        btn_label = "Ascolta su Spotify" if source == "spotify" else ("Ascolta su Facebook" if source == "facebook" else f"Ascolta su {source.capitalize()}")
        btn_color = "#1DB954" if source == "spotify" else ("#1877F2" if source == "facebook" else "var(--primary-color)")
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
        <audio id="audio-player-static" class="bp-player" style="height:54px; width:100%; border-radius:var(--radius-md); margin-bottom:1rem;" controls preload="none">
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
    <section class="bp-synopsis"><h2>Trama</h2><p>{e(synopsis)}</p>{ai_notice}</section>
    {facts_section}
    <section class="bp-faqs"><h2>Domande frequenti</h2>{faq_html}</section>
    {related_html}
    <a class="bp-back" href="/">← Tutta la libreria</a>
  </div>"""
    page_title = f"{title} — audiolibro gratis di {author} | Audiolibri.org"
    # The content is a YouTube video, so also expose VideoObject → eligible for
    # video rich results. Google requires uploadDate, so emit only when present.
    schemas = [audiobook, breadcrumb]
    if embed_type == "youtube" and vid and published and not estatus:
        schemas.append({"@context": "https://schema.org", "@type": "VideoObject",
                        "name": title, "description": synopsis or f"Audiolibro «{title}» di {author}.",
                        "thumbnailUrl": cover, "uploadDate": f"{published}T00:00:00+00:00", "duration": iso_duration(dur),
                        "contentUrl": b.get("url", ""), "embedUrl": embed_url})
    head_html = head(page_title, description, canonical, cover, "article", tuple(schemas), noindex=(estatus == 404))
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
    bio_html = ""
    if kind == "autore":
        bio = author_bio(label)
        if bio:
            bio_html = f'<p class="bp-authorbio">{e(bio)}</p>'
    main_html = f"""<div class="bp-wrap">
    <nav class="bp-crumbs" aria-label="Breadcrumb"><a href="/">Home</a> › <a href="/{ 'generi' if kind=='genere' else 'autori' }/">{ 'Generi' if kind=='genere' else 'Autori' }</a> › <span>{e(h1)}</span></nav>
    <h1 class="bp-title">{e(h1)}</h1>
    <p class="bp-lead">{e(lead)}</p>
    {bio_html}
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
    elif kind == "raccolte":
        h1, sub = "Raccolte", "raccolta"
        lead = f"Raccolte tematiche di audiolibri gratuiti — {len(entries)} collezioni per genere, età e occasione."
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


# ---- Thematic collections -------------------------------------------------
# Curated landing pages under /raccolta/<slug>/ grouping titles by theme, to
# capture informational queries ("audiolibri per bambini", "horror", ...).
# Each carries a unique intro so the page is not thin/duplicate content.

def _meta(b):
    # Match on reliable fields only — NOT real_synopsis, whose text is polluted by
    # channel promo blurbs ("...anche per bambini", contacts) that cause false
    # positives (e.g. 46 Camilleri novels landing in the kids collection).
    return " ".join([title_of(b), author_of(b), genre_of(b),
                     " ".join(b.get("categories") or [])]).lower()


# Titles kept out of every curated collection: sensitive / true-crime content
# that must not sit next to literary works or on kid-facing pages.
_COLLECTION_BLOCK = ("pedofil", "deep web", "stupro", "incesto", "violenza sessuale")


def _blocked(b):
    text = (title_of(b) + " " + (b.get("real_synopsis") or "")).lower()
    return any(w in text for w in _COLLECTION_BLOCK)


try:
    EMBED_STATUS = {k: int(v) for k, v in json.loads((ROOT / "embed_status.json").read_text()).items()}
except FileNotFoundError:
    EMBED_STATUS = {}

# Maps a broken video id -> an embeddable replacement id. The page keeps the
# ORIGINAL id in its slug/URL/metadata (so nothing 404s); only the player loads
# the replacement. Populated by hand after vetting alternatives.
try:
    EMBED_REPLACEMENTS = {k: str(v) for k, v in json.loads((ROOT / "embed_replacements.json").read_text()).items()}
except FileNotFoundError:
    EMBED_REPLACEMENTS = {}


def _embed_broken(b) -> bool:
    """True if the embed is disabled/removed AND there's no working replacement."""
    v = video_id(b)
    return v in EMBED_STATUS and v not in EMBED_REPLACEMENTS


def _embed_dead(b) -> bool:
    """True if the source video is gone (404) and has no replacement — page gets noindex + no sitemap."""
    v = video_id(b)
    return EMBED_STATUS.get(v) == 404 and v not in EMBED_REPLACEMENTS


COLLECTIONS = [
    dict(slug="audiolibri-per-bambini",
         h1="Audiolibri per bambini e fiabe",
         title="Audiolibri per bambini gratis: fiabe e favole da ascoltare | Audiolibri.org",
         intro="Fiabe classiche, favole della tradizione e filastrocche per i più piccoli, lette ad "
               "alta voce e pronte da ascoltare. Una raccolta pensata per accompagnare il gioco, la "
               "nanna o i viaggi in auto — tutta gratuita, in streaming e senza registrazione.",
         match=lambda b: genre_of(b).lower() == "fiaba"
               or any(k in _meta(b) for k in ("fiaba", "fiabe", "favola", "filastrocc", "cappuccetto", "pinocchio"))),
    dict(slug="classici-della-scuola",
         h1="Classici della letteratura da ascoltare",
         title="Classici della scuola gratis: Manzoni, Pirandello, Verga e altri | Audiolibri.org",
         intro="I grandi classici della letteratura italiana più letti a scuola, da «I Promessi Sposi» "
               "alla «Divina Commedia», da Pirandello a Verga e Leopardi. Perfetti per ripassare "
               "un'opera ascoltandola, o per riscoprirla con calma, gratis e in streaming.",
         match=lambda b: any(k in _meta(b) for k in (
               "promessi sposi", "divina commedia", "dante alighieri", "manzoni", "pirandello",
               "giovanni verga", "leopardi", "decameron", "boccaccio", "foscolo", "italo svevo"))),
    dict(slug="audiolibri-horror",
         h1="Audiolibri horror da ascoltare",
         title="Audiolibri horror gratis: Poe, Lovecraft e racconti del terrore | Audiolibri.org",
         intro="Racconti del terrore e atmosfere gotiche: da H.P. Lovecraft a Edgar Allan Poe, le storie "
               "che hanno definito la paura in letteratura. Narrazioni che trasformano l'ascolto in un "
               "brivido, gratis e senza registrazione.",
         match=lambda b: genre_of(b).lower() == "horror"
               or any(k in _meta(b) for k in ("lovecraft", "edgar allan poe", "dracula", "frankenstein", "arthur machen", "algernon blackwood"))),
    dict(slug="audiolibri-gialli",
         h1="Audiolibri gialli e thriller",
         title="Audiolibri gialli gratis: mistero e thriller da ascoltare | Audiolibri.org",
         intro="Delitti, indagini e misteri da risolvere un capitolo alla volta. Una raccolta di gialli, "
               "polizieschi e thriller da ascoltare gratuitamente, per chi ama tenere il fiato sospeso "
               "fino all'ultima rivelazione.",
         match=lambda b: genre_of(b).lower() in ("giallo", "mistero")
               or any(k in _meta(b) for k in ("camilleri", "montalbano", "agatha christie", "sherlock", "conan doyle", "simenon", "poliziesco"))),
    dict(slug="racconti-brevi",
         h1="Racconti brevi da ascoltare",
         title="Racconti brevi gratis: audiolibri sotto i 15 minuti | Audiolibri.org",
         intro="Storie complete in pochi minuti, perfette per una pausa pranzo, una passeggiata o "
               "l'attesa del treno. Racconti brevi da ascoltare tutti d'un fiato, gratis e in streaming.",
         match=lambda b: 0 < (b.get("duration") or 0) <= 900),
    dict(slug="opere-integrali",
         h1="Audiolibri integrali oltre un'ora",
         title="Audiolibri integrali gratis: opere complete da ascoltare | Audiolibri.org",
         intro="Romanzi e opere lette per intero, dall'inizio alla fine, per chi vuole immergersi in una "
               "storia lunga senza interruzioni. Audiolibri integrali di oltre un'ora, gratuiti e in streaming.",
         match=lambda b: (b.get("duration") or 0) >= 3600),
]


def build_collection(c, items):
    rel_dir = f"raccolta/{c['slug']}"
    canonical = f"{SITE}/{rel_dir}/"
    h1, intro = c["h1"], c["intro"]
    lead = f"{len(items)} audiolibri da ascoltare gratis, in streaming e senza registrazione."
    itemlist = {"@context": "https://schema.org", "@type": "ItemList", "name": h1, "numberOfItems": len(items),
                "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{SITE}/audiolibro/{book_slug(b)}/", "name": display_title_of(b)}
                                    for i, b in enumerate(items)]}
    breadcrumb = {"@context": "https://schema.org", "@type": "BreadcrumbList",
                  "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                                      {"@type": "ListItem", "position": 2, "name": "Raccolte", "item": f"{SITE}/raccolte/"},
                                      {"@type": "ListItem", "position": 3, "name": h1, "item": canonical}]}
    grid = "".join(card_link(b) for b in items)
    main_html = f"""<div class="bp-wrap">
    <nav class="bp-crumbs" aria-label="Breadcrumb"><a href="/">Home</a> › <a href="/raccolte/">Raccolte</a> › <span>{e(h1)}</span></nav>
    <p class="bp-eyebrow">Raccolta</p>
    <h1 class="bp-title">{e(h1)}</h1>
    <p class="bp-lead">{e(lead)}</p>
    <div class="bp-synopsis"><p>{e(intro)}</p></div>
    <div class="bp-grid">{grid}</div>
    <a class="bp-back" href="/raccolte/">← Tutte le raccolte</a>
  </div>"""
    head_html = head(c["title"], meta_description(intro), canonical, "", "website", (itemlist, breadcrumb))
    return rel_dir, shell(head_html, main_html, with_fallback=True)


def write(rel_dir, page):
    out = ROOT / rel_dir / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page, encoding="utf-8")
    return f"{rel_dir}/"


def _lastmod(books):
    """Most-recent upload date among these books (YYYY-MM-DD), else today.
    Stable across rebuilds (a page's lastmod only moves when new content lands),
    so Google can trust the freshness signal instead of seeing every URL as
    'changed today' on each deploy."""
    dates = [d for d in (iso_date(b.get("upload_date", "")) for b in books) if d]
    return max(dates) if dates else TODAY


def build_sitemap(entries):
    """entries: list of (rel_path, lastmod)."""
    urls = f"  <url><loc>{SITE}/</loc><lastmod>{TODAY}</lastmod></url>\n"
    urls += "".join(f"  <url><loc>{SITE}/{p}</loc><lastmod>{lm}</lastmod></url>\n" for p, lm in entries)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' + urls + "</urlset>\n")


def related_for(b, authors, genres, limit=12):
    """Pick related titles for a book page: same author first, then same genre."""
    seen = {b.get("id")}
    out = []

    def add_from(pool):
        for rb in sorted(pool, key=lambda x: x.get("view_count") or 0, reverse=True):
            rid = rb.get("id")
            if rid and rid not in seen and not _blocked(rb) and not _embed_broken(rb):
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


def build_home_explore(valid, genre_entries, coll_entries):
    """Static, crawlable homepage links so the home isn't empty for bots that
    don't execute JS (AI crawlers) and to spread internal links to hubs."""
    colls = "".join(f'<a href="/raccolta/{slug}/">{e(h1)}</a>' for h1, slug, _ in coll_entries)
    gens = "".join(f'<a href="/genere/{slug}/">{e(label)}</a>' for label, slug, _ in genre_entries)
    top = [b for b in sorted(valid, key=lambda x: x.get("view_count") or 0, reverse=True)
           if not ((b.get("duration") or 0) < 600 and (b.get("view_count") or 0) > 1_000_000)
           and not _blocked(b) and not _embed_broken(b)][:24]
    titles = "".join(f'<a href="/audiolibro/{book_slug(b)}/">{e(display_title_of(b))}</a>' for b in top)
    parts = []
    if colls:
        parts.append(f'<h2>Raccolte</h2><div class="he-links">{colls}</div>')
    parts.append(f'<h2>Generi</h2><div class="he-links">{gens}</div>')
    parts.append(f'<h2>Titoli popolari</h2><div class="he-links">{titles}</div>')
    parts.append('<p class="he-all"><a href="/generi/">Tutti i generi</a> · '
                 '<a href="/autori/">Tutti gli autori</a> · '
                 '<a href="/raccolte/">Tutte le raccolte</a></p>')
    return "".join(parts)


def inject_home_explore(block):
    """Replace the content between the EXPLORE markers in index.html."""
    index_path = ROOT / "index.html"
    txt = index_path.read_text(encoding="utf-8")
    a, b = "<!-- EXPLORE:START -->", "<!-- EXPLORE:END -->"
    if a in txt and b in txt:
        txt = txt[:txt.index(a) + len(a)] + "\n" + block + "\n                " + txt[txt.index(b):]
        index_path.write_text(txt, encoding="utf-8")
        return True
    return False


GUIDE_CSS = """<style>
.bp-guide { max-width: 820px; }
.bp-guide h2 { font-family: var(--font-display); font-size: var(--text-xl); margin: 2.2rem 0 .7rem; color: var(--header-color); }
.bp-guide h3 { font-size: 1.08rem; margin: 1.3rem 0 .3rem; color: var(--header-color); }
.bp-guide p { line-height: 1.7; margin: 0 0 1rem; color: var(--text-color); }
.bp-guide ul { margin: 0 0 1rem 1.2rem; line-height: 1.7; color: var(--text-color); }
.bp-guide a { color: var(--primary-color); }
.guide-table-wrap { overflow-x: auto; margin: 1rem 0 1.5rem; }
.guide-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); min-width: 520px; }
.guide-table th, .guide-table td { text-align: left; padding: .55rem .6rem; border-bottom: 1px solid var(--border-color); }
.guide-table th { color: var(--header-color); }
</style>"""


def build_guide(valid, genre_entries, coll_entries):
    """Long-form editorial landing for the informational query set
    ('migliori audiolibri gratis', 'dove ascoltare ...'). Plays the same game as
    the aggregator blogs that outrank us, but from the site that actually owns the
    catalogue — with deep internal links into collections/genres/titles."""
    rel_dir = "migliori-audiolibri-gratis"
    canonical = f"{SITE}/{rel_dir}/"
    title = "Migliori audiolibri gratis in italiano (2026): dove ascoltarli | Audiolibri.org"
    h1 = "Migliori audiolibri gratis in italiano (2026)"
    description = ("Guida ai migliori audiolibri gratis in italiano: dove ascoltarli in streaming "
                   "senza registrazione, le piattaforme gratuite a confronto e i titoli da non perdere per ogni genere.")
    total = len(valid)

    by_genre = {}
    for b in valid:
        if not _blocked(b) and not _embed_broken(b):
            by_genre.setdefault(genre_of(b), []).append(b)
    colls = {slug: h1c for h1c, slug, _ in coll_entries}

    def rc(slug, fallback_label):
        return f'<a href="/raccolta/{slug}/">{e(colls[slug])}</a>' if slug in colls else e(fallback_label)

    def tt(genre_key, n=3):
        items = sorted(by_genre.get(genre_key, []), key=lambda x: x.get("view_count") or 0, reverse=True)[:n]
        return ", ".join(f'<a href="/audiolibro/{book_slug(b)}/">{e(display_title_of(b))}</a>' for b in items) or "i titoli del catalogo"

    breadcrumb = {"@context": "https://schema.org", "@type": "BreadcrumbList",
                  "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                                      {"@type": "ListItem", "position": 2, "name": h1, "item": canonical}]}
    article = {"@context": "https://schema.org", "@type": "Article", "headline": h1, "inLanguage": "it-IT",
               "description": description,
               "author": {"@type": "Organization", "name": "Audiolibri.org", "url": SITE},
               "publisher": {"@type": "Organization", "name": "Audiolibri.org",
                             "logo": {"@type": "ImageObject", "url": SITE + "/icons/android-chrome-512x512.png"}},
               "datePublished": "2026-08-10", "dateModified": TODAY, "mainEntityOfPage": canonical}

    body = f"""<div class="bp-wrap bp-guide">
    <nav class="bp-crumbs" aria-label="Breadcrumb"><a href="/">Home</a> › <span>{e(h1)}</span></nav>
    <p class="bp-eyebrow">Guida</p>
    <h1 class="bp-title">{e(h1)}</h1>
    <p class="bp-lead">Per ascoltare ottimi audiolibri in italiano non serve quasi mai pagare, e spesso nemmeno registrarsi. Ecco le piattaforme gratuite migliori, come funzionano davvero e i titoli da cui partire, genere per genere.</p>

    <p>Negli ultimi anni ascoltare libri è diventato un'abitudine quotidiana: in auto, mentre si cammina, prima di dormire. Il bello è che gran parte di questo tesoro è gratis. Le opere il cui diritto d'autore è scaduto — Verga, Pirandello, Dostoevskij, Poe, i fratelli Grimm — possono essere lette, registrate e diffuse liberamente, e progetti come questo le raccolgono in un unico posto.</p>
    <p>Abbiamo confrontato le principali fonti gratuite in italiano guardando a ciò che conta per chi ascolta: quanti titoli offrono, se richiedono un account e la qualità dell'esperienza. Partiamo da dove ascoltarli.</p>

    <h2>Dove ascoltare audiolibri gratis in italiano</h2>
    <h3>1. Audiolibri.org</h3>
    <p>Il modo più immediato: oltre {total} audiolibri in italiano, in streaming e <strong>senza registrazione</strong>. Apri una scheda, premi play e ascolti — da telefono, tablet o computer, anche a schermo spento. Nessun account, nessuna pubblicità invadente, nessun cookie di tracciamento. È un progetto open source e senza scopo di lucro: trovi <a href="/generi/">tutti i generi</a>, <a href="/autori/">gli autori</a> e le <a href="/raccolte/">raccolte curate</a>.</p>
    <h3>2. RaiPlay Sound (Ad alta voce)</h3>
    <p>Il servizio audio della Rai propone letture e sceneggiati di qualità professionale, con la sezione «Ad alta voce» dedicata agli audiolibri. È gratuito; per alcuni contenuti è consigliato l'accesso con un account Rai. Ottimo per produzioni curate e voci di attori.</p>
    <h3>3. Liber Liber</h3>
    <p>Storico progetto italiano della cultura libera: la biblioteca «Liber Liber» raccoglie classici della letteratura italiana in testo e audio, scaricabili gratuitamente. Una fonte preziosa per i grandi nomi della nostra tradizione.</p>
    <h3>4. LibriVox</h3>
    <p>Il più grande archivio internazionale di audiolibri di pubblico dominio, letti da volontari di tutto il mondo. Il catalogo in italiano è più limitato rispetto all'inglese, ma cresce ed è del tutto gratuito e senza registrazione.</p>
    <h3>5. Loyal Books</h3>
    <p>Ex «Books Should Be Free», raccoglie audiolibri ed e-book di pubblico dominio in molte lingue. Interfaccia essenziale, catalogo internazionale, tutto gratis.</p>
    <h3>6. YouTube</h3>
    <p>Cercando il titolo trovi moltissime letture integrali gratuite. La qualità però è molto variabile e i video sono spesso interrotti dalla pubblicità: conviene affidarsi a canali di lettori riconosciuti.</p>
    <h3>7. Spotify e podcast</h3>
    <p>Alcuni audiolibri e podcast narrativi sono disponibili gratuitamente con un account Spotify. Comodo se già usi l'app per la musica, meno completo per il catalogo classico in italiano.</p>

    <h2>Come funziona lo streaming gratis, senza registrazione</h2>
    <p>La differenza principale tra le piattaforme è tra <strong>streaming</strong> e <strong>download</strong>. Con lo streaming — come su audiolibri.org — apri e ascolti subito, senza occupare spazio sul dispositivo; con il download (LibriVox, Liber Liber) salvi il file per l'ascolto offline. Per la maggior parte delle persone lo streaming è la via più semplice: nessun account, nessuna installazione, si riprende da dove si era rimasti. E su smartphone l'audio continua anche con lo schermo spento.</p>

    <h2>I migliori audiolibri gratis per genere</h2>
    <p>Non sai da dove iniziare? Ecco i punti di partenza migliori, con le raccolte curate e alcuni tra i titoli più ascoltati.</p>
    <h3>Grandi classici</h3>
    <p>Le opere che hanno fatto la storia della letteratura, oggi libere da diritti. Parti da {rc('classici-della-scuola', 'i classici da ascoltare')} o da titoli come {tt('romanzo')}.</p>
    <h3>Gialli e thriller</h3>
    <p>Delitti, indagini e tensione. Vai alla raccolta {rc('audiolibri-gialli', 'gli audiolibri gialli')}; tra i più ascoltati: {tt('giallo')}.</p>
    <h3>Horror e mistero</h3>
    <p>Racconti del terrore e atmosfere gotiche. Scopri {rc('audiolibri-horror', 'gli audiolibri horror')} e titoli come {tt('horror')}.</p>
    <h3>Per bambini e fiabe</h3>
    <p>Storie della buonanotte e fiabe classiche, perfette da ascoltare insieme. Trovi tutto in {rc('audiolibri-per-bambini', 'gli audiolibri per bambini')}; ad esempio {tt('fiaba')}.</p>
    <h3>Racconti brevi</h3>
    <p>Ideali per una pausa: una storia intera in pochi minuti. Prova {rc('racconti-brevi', 'i racconti brevi')} o {tt('racconto')}.</p>
    <h3>Fantascienza e avventura</h3>
    <p>Mondi lontani e grandi viaggi. Esplora il genere <a href="/genere/fantascienza/">fantascienza</a> con {tt('fantascienza')}.</p>

    <h2>Le piattaforme gratuite a confronto</h2>
    <div class="guide-table-wrap"><table class="guide-table">
      <thead><tr><th>Piattaforma</th><th>Catalogo</th><th>Italiano</th><th>Registrazione</th><th>Costo</th></tr></thead>
      <tbody>
        <tr><td>Audiolibri.org</td><td>~{total} titoli</td><td>Sì</td><td>No</td><td>Gratis</td></tr>
        <tr><td>RaiPlay Sound</td><td>Ampio, curato</td><td>Sì</td><td>Consigliata</td><td>Gratis</td></tr>
        <tr><td>Liber Liber</td><td>Classici italiani</td><td>Sì</td><td>No</td><td>Gratis</td></tr>
        <tr><td>LibriVox</td><td>Pubblico dominio</td><td>Parziale</td><td>No</td><td>Gratis</td></tr>
        <tr><td>Loyal Books</td><td>Pubblico dominio</td><td>Parziale</td><td>No</td><td>Gratis</td></tr>
        <tr><td>Audible</td><td>Enorme</td><td>Sì</td><td>Sì</td><td>A pagamento (prova gratis)</td></tr>
      </tbody>
    </table></div>

    <h2>Perché scegliere audiolibri.org</h2>
    <p>Tra le opzioni gratuite, audiolibri.org ha tre vantaggi concreti: è il catalogo in italiano più ampio in <strong>streaming immediato</strong>, non chiede <strong>alcuna registrazione</strong>, e <strong>rispetta la privacy</strong> di chi ascolta (nessun tracciamento, nessuna terza parte contattata finché non premi play). Ed è open source: chiunque può vedere come funziona e contribuire.</p>

    <h2>Domande frequenti</h2>
    <h3>Qual è il miglior sito di audiolibri gratis in italiano?</h3>
    <p>Dipende da cosa cerchi: per ampiezza e immediatezza in streaming senza registrazione, audiolibri.org; per produzioni professionali, RaiPlay Sound «Ad alta voce»; per i classici scaricabili, Liber Liber.</p>
    <h3>Gli audiolibri gratis sono legali?</h3>
    <p>Sì, quando si tratta di opere di pubblico dominio (diritto d'autore scaduto) o di registrazioni condivise liberamente da chi le ha realizzate. Tutte le fonti citate qui operano su questa base.</p>
    <h3>Servono registrazione o carta di credito?</h3>
    <p>Su audiolibri.org, LibriVox, Liber Liber e Loyal Books no. Su RaiPlay Sound e Spotify può servire un account gratuito.</p>
    <h3>Posso ascoltarli offline?</h3>
    <p>Con lo streaming ascolti online; se ti serve l'offline, le piattaforme con download (LibriVox, Liber Liber) fanno al caso tuo.</p>
    <h3>Quanto costano?</h3>
    <p>Tutte le piattaforme di questa guida sono gratuite. Audible è a pagamento (con una prova gratuita) e la citiamo solo per completezza.</p>

    <p>Pronto ad ascoltare? Inizia dal <a href="/">catalogo completo</a>, scegli una <a href="/raccolte/">raccolta</a> e premi play: nessun account, nessun costo, solo storie.</p>
    <a class="bp-back" href="/">← Torna al catalogo</a>
  </div>"""
    head_html = head(title, description, canonical, f"{SITE}/og-cover.png", "article", (article, breadcrumb))
    return rel_dir, shell(head_html, GUIDE_CSS + body, with_fallback=True)


def build_about():
    """Chi siamo — E-E-A-T page. Deliberately names no people or third parties."""
    rel_dir = "chi-siamo"
    canonical = f"{SITE}/{rel_dir}/"
    title = "Chi siamo | Audiolibri.org"
    description = ("Audiolibri.org è il più grande catalogo di audiolibri gratis in italiano: la storia, "
                   "la missione e i principi del progetto — gratis, senza registrazione, open source, privacy-first.")
    breadcrumb = {"@context": "https://schema.org", "@type": "BreadcrumbList",
                  "itemListElement": [{"@type": "ListItem", "position": 1, "name": "Home", "item": SITE + "/"},
                                      {"@type": "ListItem", "position": 2, "name": "Chi siamo", "item": canonical}]}
    body = f"""<div class="bp-wrap bp-guide">
    <nav class="bp-crumbs" aria-label="Breadcrumb"><a href="/">Home</a> › <span>Chi siamo</span></nav>
    <p class="bp-eyebrow">Il progetto</p>
    <h1 class="bp-title">Chi siamo</h1>
    <p class="bp-lead">Audiolibri.org è il più grande catalogo di audiolibri gratis in italiano: oltre 2.800 opere da ascoltare in streaming, senza registrazione e senza installare nulla.</p>

    <h2>La storia</h2>
    <p>Il progetto nasce nel 2014 da un'idea semplice: rendere la lettura ad alta voce accessibile a chiunque, gratuitamente. Da una manciata di titoli condivisi per passione, negli anni è cresciuto fino a diventare la raccolta di audiolibri gratuiti in italiano più ampia del web.</p>

    <h2>La missione</h2>
    <p>Le storie e la cultura non dovrebbero avere barriere. Un buon audiolibro tiene compagnia in viaggio, aiuta chi fatica a leggere, accompagna il sonno dei bambini e fa scoprire un classico a chi non l'avrebbe mai aperto. L'obiettivo è uno solo: metterlo a portata di play, per tutti, gratis.</p>

    <h2>Come funziona</h2>
    <ul>
      <li><strong>Gratis e senza registrazione.</strong> Nessun account, nessun abbonamento, nessuna carta di credito: apri e ascolti.</li>
      <li><strong>Nel rispetto delle regole.</strong> Il catalogo raccoglie opere di pubblico dominio e registrazioni condivise liberamente.</li>
      <li><strong>Rispettoso della tua privacy.</strong> Nessun cookie di tracciamento e nessuna terza parte contattata finché non premi play: anche le copertine sono servite dal nostro dominio.</li>
      <li><strong>Aperto e trasparente.</strong> Un progetto open source e senza scopo di lucro: il codice è pubblico e chiunque può contribuire.</li>
    </ul>

    <h2>Contribuisci</h2>
    <p>Ti piace il progetto? Puoi aiutarlo a crescere: segnala un titolo, migliora il codice o semplicemente condividilo con chi ama i libri. Trovi tutto su <a href="https://github.com/fabriziosalmi/audiolibri" target="_blank" rel="noopener noreferrer">GitHub</a>.</p>

    <a class="bp-back" href="/">← Torna al catalogo</a>
  </div>"""
    head_html = head(title, description, canonical, f"{SITE}/og-cover.png", "website", (breadcrumb,))
    return rel_dir, shell(head_html, GUIDE_CSS + body, with_fallback=True)


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
        w = write(rel_dir, page)
        if not _embed_dead(b):
            paths.append((w, iso_date(b.get("upload_date", "")) or TODAY))

    genre_entries = []
    for g, items in sorted(genres.items(), key=lambda kv: len(kv[1]), reverse=True):
        items.sort(key=lambda b: b.get("view_count") or 0, reverse=True)
        rel_dir, page = build_hub("genere", g.capitalize(), items, slugify(g))
        paths.append((write(rel_dir, page), _lastmod(items)))
        genre_entries.append((g.capitalize(), slugify(g), len(items)))

    author_entries = []
    for a, items in sorted(authors.items(), key=lambda kv: len(kv[1]), reverse=True):
        if len(items) < 2 or a == "Autore sconosciuto":
            continue
        items.sort(key=lambda b: b.get("view_count") or 0, reverse=True)
        rel_dir, page = build_hub("autore", a, items, slugify(a))
        paths.append((write(rel_dir, page), _lastmod(items)))
        author_entries.append((a, slugify(a), len(items)))

    series_entries = []
    for sl, g in sorted(series_groups.items(), key=lambda kv: len(kv[1]["chapters"]), reverse=True):
        name = series_name_by_slug[sl]
        rel_dir, page = build_series(name, g["chapters"])
        paths.append((write(rel_dir, page), _lastmod(g["chapters"])))
        series_entries.append((name, sl, len(g["chapters"])))

    # Thematic collections: curated landing pages for informational queries.
    coll_entries = []
    for c in COLLECTIONS:
        items = [b for b in valid if c["match"](b) and not _blocked(b)]
        if len(items) < 8:
            continue
        items.sort(key=lambda b: b.get("view_count") or 0, reverse=True)
        rel_dir, page = build_collection(c, items)
        paths.append((write(rel_dir, page), _lastmod(items)))
        coll_entries.append((c["h1"], c["slug"], len(items)))

    paths.append((write(*build_index("generi", genre_entries)), TODAY))
    paths.append((write(*build_index("autori", sorted(author_entries, key=lambda x: x[0].lower()))), TODAY))
    if series_entries:
        paths.append((write(*build_index("serie", sorted(series_entries, key=lambda x: x[0].lower()))), TODAY))
    if coll_entries:
        paths.append((write(*build_index("raccolte", coll_entries)), TODAY))

    paths.append((write(*build_guide(valid, genre_entries, coll_entries)), TODAY))
    paths.append((write(*build_about()), TODAY))

    (ROOT / "sitemap.xml").write_text(build_sitemap(paths), encoding="utf-8")
    (ROOT / "robots.txt").write_text(
        "User-agent: *\nAllow: /\n\n"
        "# Build scripts and internal tooling (served by GitHub Pages, but not content)\n"
        "Disallow: /*.py$\nDisallow: /deploy/\n\n"
        f"Sitemap: {SITE}/sitemap.xml\n", encoding="utf-8")

    inject_home_explore(build_home_explore(valid, genre_entries, coll_entries))

    print(f"books={len(valid)}  genre_hubs={len(genre_entries)}  author_hubs={len(author_entries)}  "
          f"series={len(series_entries)}  collections={len(coll_entries)}  sitemap_urls={len(paths) + 1}")


if __name__ == "__main__":
    main()
