# Data enrichment plan

Two sprints to deepen and broaden the catalog. Current data (`augmented.json`,
1793 records) is already high quality — see the baseline before the work items.

## Baseline (audit, 2026-06-01)

- **1793** records, keyed by YouTube video id (single source of truth; used by
  both `app.js` and `generate_pages.py`).
- Coverage: title 100%, **real_genre 100%** (21 genres), **real_synopsis 100%**
  (only 7 under 60 chars), duration 100%, author 99.8% (4 missing → "Autore
  sconosciuto").
- **Headline issue — duplicate titles: 771 records across 119 groups.** These
  are multi-part series whose chapters all share one `real_title`
  ("Figlia del mare" ×234, "Delitto e castigo" ×43, "Le avventure di Pinocchio"
  ×36). The chapter number lives in the raw `title`
  ("Capitolo 220 - Figlia del mare - Audiolibro") but was stripped from
  `real_title`. Impact: indistinguishable cards (UX) and duplicate
  `<title>`/`<h1>`/breadcrumbs across hundreds of static pages (SEO).
- `real_narrator` is populated on only 5 records (readers currently inferred
  from `channel`).

---

## Sprint A — YouTube (deepen what we have)

1. **De-duplicate series titles** *(highest priority — fixes 771 records).*
   Parse the raw `title` for part markers (`Capitolo N`, `Parte N`, `N -`,
   `#N`, `Ep. N`) and derive `series` + `part` + a disambiguated display title
   (e.g. `Figlia del mare — Capitolo 12`). Keep a confidence flag; leave
   ambiguous cases on the cleaned title. Re-run the static regen after.
2. **Series modeling.** Promote a series to a first-class entity: one
   `/serie/<slug>/` page listing chapters in order (reuses the results grid),
   and on each chapter page a "prossimo capitolo" link + breadcrumb
   `Home › Serie › Capitolo N`. schema.org: `Audiobook` with `hasPart`, or
   `BookSeries`. Collapses the 234 scattered "Figlia del mare" cards into one
   discoverable work.
3. **Narrator extraction.** Populate `real_narrator` from `channel` +
   description heuristics (currently 5/1793) → richer `readBy` schema and a
   real "Voci/Lettori" facet.
4. **Author normalization.** Canonicalize variants ("F. Dostoevskij" /
   "Fëdor Dostoevskij" / "Fyodor Dostoevsky") to one entity; fixes the 4
   missing authors and merges duplicate author hubs → stronger internal links.
5. **Synopsis quality pass.** Regenerate the 7 ultra-short synopses and any
   generic ones from transcript/description; keep ≥ ~160 chars for AI snippets.
6. **Availability sweep.** Detect deleted/private videos (the grey 120×90
   thumbnail) and flag/prune so no dead cards or pages ship.
7. **Tags & language.** Validate `real_language`; enrich `tags` to improve
   search recall and the "related" picker.

## Sprint B — Other platforms (broaden sources)

1. **Platform-agnostic data model first.** Add `source` ("youtube" | "librivox"
   | "archive" | …), `source_url`, `embed_type` ("youtube" | "audio" | "link"),
   and an `audio_url` for direct files. Make `video_id` optional; route the
   player by `embed_type` (YouTube iframe vs native `<audio>` vs external link).
2. **LibriVox** — large public-domain Italian catalog with clean metadata
   (reader, chapters, source text, license). Best first non-YouTube source;
   maps directly onto the series model from Sprint A.
3. **Internet Archive (archive.org)** — public-domain audio collections; good
   for classics not on LibriVox.
4. **RAI "Ad alta voce" / Spreaker / Spotify** — assess embeddability and
   licensing before ingest (link-out where embedding isn't permitted).
5. **Cross-platform dedup** — same work from multiple sources: merge into one
   entity with alternate `sources[]`, or link.
6. **License/attribution tracking** — store license per record (public domain
   vs platform ToS) for compliance and to surface "pubblico dominio" badges.

---

## Sequencing

- **A1 (title de-dup) + A2 (series)** unblock the biggest UX/SEO win and should
  ship together (the regen touches the same pages).
- Land the **Sprint-B data model** (source/embed_type) before ingesting any new
  platform so the generator and SPA stay source-agnostic.
- Every data change ends with `python3 generate_pages.py all` + a sitemap
  refresh; validate `git diff --stat` shows only intended changes.
