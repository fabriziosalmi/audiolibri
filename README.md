# Audiolibri.org

**The largest collection of free Italian audiobooks** — 2,800+ titles, streaming, no signup, no app, no ads.

🔊 **[audiolibri.org](https://audiolibri.org)**

![audiolibri.org](https://github.com/fabriziosalmi/audiolibri/blob/main/screenshot.png?raw=true)

## What it is

Audiolibri.org is a curated catalogue of public-domain and freely listenable audiobooks in Italian — novels, short stories, fairy tales, mysteries, horror, poetry, school classics. Every title plays straight from the browser. The project is open source and non-profit.

- **~2,800 audiobooks** in Italian, free and streaming
- Browse by **genre**, **author**, **themed collection** and **series**
- **Search** by title, author or narrator
- A **dedicated page** per title with synopsis, a data sheet (duration, narrator, year) and player
- **No signup, no app, no ads**

## Architecture

A **static site** served by **GitHub Pages**, generated from a JSON dataset:

- **Frontend** — vanilla HTML/CSS/JavaScript (no framework). The home loads a lightweight index (`index.min.json`) and renders dynamically; every detail page is pre-generated static HTML.
- **Static pages** — `generate_pages.py` builds the ~2,800 title pages (with schema.org `Audiobook` + `BreadcrumbList` + `FAQPage` structured data), the genre / author / series hubs, the themed collections, the sitemap and robots.txt.
- **Home index** — `build_index.py` produces `index.min.json`, a slimmed dataset with only the fields the home needs, for a fast first load.
- **Deploy** — every push to `main` builds and publishes via GitHub Actions (`.github/workflows/deploy.yml`), so the live site can never drift from the source data.

### URL structure

```
/                      Home — search + themed rows + collections
/audiolibro/<slug>/    A single title (player, synopsis, data sheet, related)
/genere/<slug>/        All titles in a genre
/autore/<slug>/        All titles by an author (with a bio for the classics)
/raccolta/<slug>/      Themed collections (kids, classics, horror, mystery…)
/generi/  /autori/  /raccolte/  /serie/    Navigation indexes
```

## Data pipeline (Python)

Scripts collect and enrich the audiobook metadata:

| Script | Purpose |
|---|---|
| `audiobook_scraper.py` | Collect metadata from sources |
| `augment.py` | Enrich entries (title, author, synopsis, genre) via an LLM |
| `build_index.py` | Build the lightweight home index (`index.min.json`) |
| `generate_pages.py` | Generate all static pages, sitemap and robots.txt |
| `stats.py`, `author_cleaner.py`, `genre_manager.py`, `title_cleaner_v2.py` | Data-cleaning utilities |

### Regenerate the site locally

The site build uses only the Python 3 standard library — no dependencies:

```bash
python3 build_index.py         # -> index.min.json
python3 generate_pages.py all  # -> pages, sitemap, robots.txt
```

### Scraper / enrichment setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

Key environment variables:

- `augment.py`: `LLM_API_URL` (default `http://localhost:1234/v1/chat/completions`)
- `audiobook_scraper.py`: `MAX_WORKERS` (default 5), `RATE_LIMIT` in seconds (default 0.5)

## Contributing

Contributions welcome — bug reports, suggested audiobooks, code improvements. Open an issue or a pull request.

## License

Code is released under a Creative Commons license. Rights to the audio content belong to their respective authors and narrators; audiolibri.org is a catalogue that links to freely accessible content.

## Acknowledgments

Thanks to all the narrators and voices who make literature accessible in audio.

---

🔊 **[audiolibri.org](https://audiolibri.org)**
