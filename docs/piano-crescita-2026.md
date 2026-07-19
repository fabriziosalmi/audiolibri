---
title: "audiolibri.org"
subtitle: "Piano di Crescita 2026 — SEO, Performance, Contenuto & Lancio"
author: "Analisi competitiva e roadmap operativa · documento interno"
date: "19 luglio 2026"
lang: it
---

# Sintesi esecutiva

**La fotografia.** audiolibri.org non è un progetto da riparare: è un asset che già funziona e che va **scalato con disciplina**. Oggi il sito è di nuovo indicizzato, è **1º risultato Google** per «audiolibri italiani gratuiti», è **citato dagli aggregatori** tra le 3 migliori fonti gratuite italiane insieme a Liber Liber e LibriVox, e poggia su un lavoro SEO on-page **di livello raro per un progetto indipendente**: 2.806 pagine-titolo statiche con dati strutturati completi, hub per genere e autore, sitemap da 3.064 URL, `llms.txt`. Chi arriva trova un catalogo con **54,8 milioni di visualizzazioni cumulate** alle spalle.

**La tesi (in una riga).** Le fonti del gratuito (YouTube, LibriVox, Liber Liber, RaiPlay) hanno i *contenuti* ma UX pessima; gli aggregatori (Aranzulla, audiolibrigratis.it) hanno la *SEO* ma non hanno il *catalogo*. **audiolibri.org occupa il centro vuoto: diventa il "motore di ricerca curato del gratuito italiano" e si prende la long-tail per titolo / autore / genere che oggi nessuno presidia in modo sistematico.**

**Cosa frena, in ordine di impatto.**

1. **La home spedisce l'intero catalogo al browser** (`augmented.json`, 8 MB grezzi / 1,4 MB gzip) con `cache: 'no-cache'`: ri-scaricato a ogni visita, parse bloccante sul main thread → **INP e LCP mobile a rischio**. E per i crawler AI (che non eseguono JS) la home è **vuota di catalogo**.
2. **Cloudflare è solo DNS, non proxy**: nessun WAF, Brotli, edge-cache o analytics. "CF davanti" oggi è vero solo per la risoluzione dei nomi.
3. **File tecnici indicizzabili** serviti pubblicamente (`fb_test.html`, `augmented.json`, manifest vuoto): rumore da rimuovere.
4. **Il gap di crescita è il contenuto editoriale**: il 30% delle pagine è *thin* e non esistono pagine-collezione per intercettare le query informazionali dove oggi vincono i blog.

**Le 3 mosse a più alto ritorno.**

- **① Home statica-first + indice leggero** (~90 KB gzip invece di 1,4 MB): sblocca performance, indicizzazione e crawler AI in un colpo solo.
- **② Pagine-collezione tematiche** (bambini, classici della scuola, gialli, horror): trasformano un catalogo esistente in decine di landing che catturano traffico informazionale.
- **③ Il lancio Telegram 8k + FB 5k come volano di *brand search*** — non un burst di click, ma migliaia di persone che poi cercano "audiolibri.org" su Google: il segnale di autorità più forte e più economico che tu possa generare.

> **Regola di questo piano.** Prima si mette a posto la *casa* (performance + igiene + strumenti), poi si accende il *traffico* (il post). Sparare il post su una home lenta è l'unico errore irreversibile: la prima impressione a 13.000 persone si spende una volta sola.

# 1. Dove sei oggi — Diagnosi

## Il semaforo

| Area | Stato | Sintesi |
|---|---|---|
| SEO on-page (pagine-titolo) | 🟢 | Statiche, schema completo, canonical, OG, breadcrumb, related. Eccellente. |
| Architettura crawl | 🟢 | Hub genere/autore statici linkano centinaia di titoli; sitemap 3.064 URL. |
| Indicizzazione | 🟢 | Reindicizzato, 1º su query brand di categoria, citato dagli aggregatori. |
| Performance home | 🔴 | Catalogo intero (1,4 MB gzip) `no-cache` a ogni visita, parse bloccante. |
| Crawlabilità home / AI | 🟡 | Contenuto client-side: OK per Google (2ª onda), **vuoto per crawler AI**. |
| Infrastruttura / CDN | 🟡 | GitHub Pages + Fastly diretto; Cloudflare non in proxy → niente WAF/Brotli/analytics. |
| Igiene tecnica | 🟡 | File di test e backup serviti pubblici (200 OK); manifest root vuoto. |
| Contenuto pagine | 🟡 | 30% *thin* (<200 caratteri); tassonomia generi squilibrata e duplice. |
| Contenuto editoriale | 🔴 | Nessuna pagina-collezione/guida: traffico informazionale non intercettato. |

## 1.1 Infrastruttura & hosting

Header live dell'apex: `server: GitHub.com`, `via: 1.1 varnish`, `x-fastly-request-id`. Traduzione: **GitHub Pages servito direttamente dalla CDN Fastly**. Nessun `cf-ray`, nessun `server: cloudflare` → **Cloudflare è in modalità DNS-only** (nuvola grigia). Il DNS è su Cloudflare, ma il traffico HTTP **non attraversa** Cloudflare: niente edge-cache CF, niente WAF, niente Brotli, niente regole, niente analytics server-side. `www → apex` con 301 corretto; HTTPS + HTTP/2 attivi. Deploy = push su `main`.

## 1.2 Performance — il collo di bottiglia è uno solo

`app.js` carica la home con `fetch('augmented.json', { cache: 'no-cache' })` (fallback `audiobooks.json`). Misure reali:

- `augmented.json` = **8,07 MB grezzi**, **1,4 MB gzip** (servito gzip, **non** Brotli).
- `cache: 'no-cache'` → il browser **rivalida/ri-scarica a ogni navigazione**: nessun beneficio di cache tra visite.
- Il file contiene **tutti i 2.806 record completi** (descrizioni, trascrizioni, tag, statistiche): `JSON.parse()` è **sincrono e blocca il main thread** → *long task* da centinaia di ms su mobile mid-range → peggiora **INP** e ritarda **LCP** (il catalogo appare solo dopo download + parse + render).
- Un **indice leggero** (`slug, titolo, autore, genere, thumbnail, durata, view`) pesa **~330 KB grezzi / ~90 KB gzip**: **‑94%**.

**Soglie Core Web Vitals di riferimento (2026, 75º percentile mobile):**

| Metrica | Buono | Da migliorare | Scarso |
|---|---|---|---|
| LCP | ≤ 2,5 s | 2,5–4,0 s | > 4,0 s |
| INP *(sostituisce FID da mar. 2024)* | ≤ 200 ms | 200–500 ms | > 500 ms |
| CLS | ≤ 0,1 | 0,1–0,25 | > 0,25 |

## 1.3 SEO on-page — già forte (non toccare ciò che funziona)

Le pagine `/audiolibro/<slug>/` sono **statiche e pre-renderizzate**, con: `title` ottimizzato («TITOLO — audiolibro gratis di AUTORE | Audiolibri.org»), meta description, canonical, Open Graph `article`, Twitter card, immagine da YouTube, **H1**, trama, player `youtube-nocookie`, breadcrumb visibile, blocco "Da ascoltare dopo" (≈12 link correlati), search che funziona **anche senza JS** (`GET /?search=`). Dati strutturati per pagina: `Audiobook` (con `author`, `duration`, `readBy`, `publisher`, `datePublished`, `associatedMedia`/`AudioObject`, `isAccessibleForFree`, `interactionStatistic`) + `BreadcrumbList` + `FAQPage`. Gli hub `/generi/` e `/autori/` espongono `ItemList`. **Internal linking hub-and-spoke corretto; nessuna pagina orfana.**

## 1.4 Igiene tecnica — rumore da eliminare

Serviti pubblicamente con **200 OK** (verificato live):

- `/fb_test.html` (50 KB) e `/fb_embed_test.html` (50 KB) — artefatti di test.
- `/augmented.json` (8 MB) e `/changelog.json` — dati interni esposti.
- `/site.webmanifest` alla root **con `name`/`short_name` vuoti** e icone a percorsi errati (il manifest valido è `/icons/site.webmanifest`, correttamente linkato).
- `/offline.html` (pagina PWA) indicizzabile.

Nessuno è linkato, ma tutti sono raggiungibili/indicizzabili: **rumore SEO e superficie inutile**.

## 1.5 Contenuto — l'asset sottosfruttato

Statistiche reali del catalogo (2.806 titoli):

- **Descrizioni:** 30% *thin* (<200 caratteri, **868 pagine**), 41% ricche (>400), media 641. **46% ha una trascrizione** (1.300 titoli) — materiale testuale **non sfruttato on-page**.
- **Durate:** 557 brevi (<10 min), 1.611 medie, 638 lunghe (>1 h); mediana **26 min**. → segmenti naturali ("in pausa pranzo", "opere integrali").
- **Popolarità reale:** **54,8 M** di visualizzazioni cumulate; **739 titoli oltre 10.000 view**; top a **1,9 M**. → social proof autentico, già in `InteractionCounter`.
- **Voci/lettori ricorrenti:** Valter Zanardi (312), La Melodia delle Parole (270), A. L. Knorr (236), Audioraccontando (202), Liber Liber (101), LibriVox (87), Ad alta voce/Rai (67). → base per pagine-lettore (`readBy`).
- **Tassonomia duplice:** il campo `categories` del JSON è ancora **grezzo da YouTube** (entertainment 1.037, education 633, music 277); i 23 generi "puliti" mostrati dal sito sono un layer separato, con **copertura squilibrata** (romanzo 666, molti generi a due cifre).


# 2. Il campo di battaglia — Analisi competitiva

## 2.1 Il mercato (dati di settore 2025–2026)

- **11,4 milioni** di ascoltatori in Italia nel 2025 (+3% sul 2024, +14% in 4 anni); proiezione **11,6 M nel 2026**, pubblico più giovane.
- Ricavi da abbonamenti **34 M€** (+13,3%); consumo medio **3,2 audiolibri/mese**; sessione media ~30 min.
- Generi trainanti: **narrativa, thriller, giallo, fantasy** (giallo/thriller fino al 46% su Audible).
- Segnale strategico: **il 48% legge un libro dopo averlo ascoltato** → forte complementarità con lettori e studenti.

**Implicazione:** il denaro è nell'abbonamento (non attaccabile), ma il **volume di ricerca sul "gratis" è enorme e servito male**. È lì che si gioca.

## 2.2 I veri rivali non sono Audible — sono i blog

| Categoria | Chi | Perché conta per te |
|---|---|---|
| **Aggregatori SEO** | Aranzulla, **audiolibrigratis.it**, navigaweb, informarea | Presidiano le query informazionali "audiolibri gratis". Hanno la SEO, **non il catalogo**. Da questi vuoi **essere citato** (link), non batterli sull'head. |
| **Concorrenti diretti long-tail** | classiciaudiolibri.it, classicipodcast.it, larivistadeilibri.it | Fanno landing per singolo titolo/opera. **Sono questi da superare** per qualità dati, UX e velocità. |
| **Fonti-serbatoio gratuite** | YouTube, LibriVox, Liber Liber, RaiPlay/Ad Alta Voce | Hanno i contenuti (li aggreghi già), UX di scoperta pessima. **Il tuo vantaggio strutturale: curarli meglio di loro.** |
| **A pagamento** | Audible (9,99 €/mese), Storytel, Emons, Nextory | Paywall/registrazione. Intercetti chi **non vuole pagare né iscriversi**. Non competere: **differenziati**. |

## 2.3 Mappa keyword — dove NON giocare, dove vincere

- 🔴 **Head informazionale** («audiolibri gratis», «app audiolibri gratis»): dominata da Aranzulla & co. **Non sprecare energie** in articoli-lista per batterli. Obiettivo qui = **backlink e citazioni**.
- 🟡 **Brand altrui** («raiplay sound audiolibri», «librivox italiano», «audible alternativa gratis»): presidiabili con **pagine-confronto** ("le alternative gratuite a X") — ma solo perché **hai un catalogo vero dietro** (loro no).
- 🟢 **Long-tail per titolo/autore** («i promessi sposi audiolibro gratis», «racconti di Poe da ascoltare», «[autore] audiolibri»): **SERP frammentata = spazio libero**. È la tua miniera: 2.806 pagine già pronte, migliaia di query a bassa concorrenza.
- 🟢 **Mid-tail per genere/verticale** («audiolibri gialli gratis», «favole per bambini da ascoltare», «classici della letteratura da ascoltare»): poco presidiato, allineato ai generi di mercato. **Oggi non hai queste pagine.**


# 3. La strategia — "Il motore di ricerca del gratuito italiano"

**Posizionamento (UVP), da ripetere ovunque in title/H1/description:**

> **Ascolta subito, gratis, senza registrazione e senza app.** Migliaia di audiolibri in italiano, in streaming.

È il gap netto verso **tutti**: Audible/Storytel (paywall), RaiPlay/Spotify (registrazione/app), Google/Emons (acquisto). Nessuno può copiarlo senza cambiare modello.

**I 4 pilastri.**

1. **Catalogo curato** — metadati puliti (durata, lettore, anno, genere), qualità segnalata, opere integrali vs estratti. Risolve il dolore #1 dell'utente su YouTube/LibriVox.
2. **Long-tail industrializzata** — ogni titolo e ogni autore è una porta d'ingresso da Google. Il valore non è la home: è la somma di migliaia di pagine.
3. **Hub tematici editoriali** — collezioni per genere, età, occasione, scuola: catturano la mid-tail e distribuiscono autorità interna verso i titoli.
4. **Velocità e apertura come marchio** — sito statico velocissimo, open source, senza pubblicità: E-E-A-T e Core Web Vitals come armi competitive contro portali lenti e pieni di ad.


# 4. Piano operativo prioritizzato

Legenda priorità: **P0** = fai subito · **P1** = alto valore · **P2** = quando puoi. Effort: S (ore) · M (1–3 gg) · L (settimana+).

## FASE 0 — Igiene & fondamenta · *settimana 1* (quasi tutto S)

| # | Azione | Prio | Effort |
|---|---|---|---|
| 0.1 | Verifica il dominio in **Google Search Console** e invia `sitemap.xml`; per le pagine chiave usa *URL Inspection → Request Indexing*. | P0 | S |
| 0.2 | Attiva **Bing Webmaster Tools** (alimenta anche le risposte AI di Copilot/ChatGPT search) e invia la sitemap. | P0 | S |
| 0.3 | Rimuovi dal deploy `fb_test.html`, `fb_embed_test.html`, `changelog.json`; correggi o elimina `/site.webmanifest` root vuoto. | P0 | S |
| 0.4 | `offline.html` → `<meta name="robots" content="noindex">`. | P1 | S |
| 0.5 | Arricchisci `robots.txt`: `Disallow` per file tecnici, conferma `Sitemap:`; aggiungi la chiave **IndexNow** (`<chiave>.txt` alla root) per il ping a Bing/Yandex. | P1 | S |
| 0.6 | Verifica che i `<lastmod>` in sitemap riflettano modifiche **reali** (lastmod affidabile = ricrawl efficiente; falso = degrada). | P2 | S |

**Risultato Fase 0:** discovery aperta su tutti i motori, superficie pulita. *Nessun rischio, tutto reversibile.*

## FASE 1 — Performance & crawlabilità · *settimane 2–4* (la fase che sblocca tutto)

| # | Azione | Prio | Effort |
|---|---|---|---|
| 1.1 | **Genera in build un indice leggero** (`index.min.json`: `slug,title,author,genre,thumb,duration,views`) — riusa `generate_pages.py`. La home carica **quello** (~90 KB gzip), non il catalogo intero. | P0 | M |
| 1.2 | Rimuovi `cache: 'no-cache'`: lascia che l'indice sia **cacheabile** (versionato con hash nel nome per il cache-busting). | P0 | S |
| 1.3 | **Home crawlabile senza JS:** inserisci nell'HTML iniziale link statici reali (`<a href>`) a `/generi/`, `/autori/` e a un set curato di 50–100 titoli in evidenza. Il JSON resta *solo* per l'interattività, **non** per la discovery. | P0 | M |
| 1.4 | Se in futuro servisse parsare payload grandi lato client, sposta `fetch`+`JSON.parse` in un **Web Worker** (protegge INP). Con l'indice leggero, spesso non serve. | P2 | M |
| 1.5 | Rimuovi `augmented.json`/`audiobooks.json` dalla superficie pubblica una volta che la home usa l'indice (o servili solo come dataset dichiarato, non come dipendenza runtime). | P1 | S |
| 1.6 | Previeni **CLS**: `width`/`height` espliciti su tutte le copertine e i contenitori iniettati via JS. | P1 | S |
| 1.7 | Misura prima/dopo con PageSpeed Insights (campo + lab) su home e pagina-titolo; obiettivo **tutti e tre i CWV "Buono"**. | P0 | S |

**Risultato Fase 1:** home leggera e istantanea, indicizzabile anche dai crawler AI, CWV verdi. **È il prerequisito del lancio.**

## FASE 2 — Contenuto & long-tail · *mese 2–3* (dove si costruisce il traffico)

| # | Azione | Prio | Effort |
|---|---|---|---|
| 2.1 | **Pagine-collezione editoriali** (nuovo tipo di pagina statica, generata dai dati): *Audiolibri per bambini e fiabe* (~262 titoli), *Classici della scuola* (~156), *Gialli e thriller*, *Horror: Poe, Lovecraft & co.* (~294), *Da ascoltare in pausa pranzo* (<10 min, 557), *Opere integrali* (>1 h, 638). Ogni collezione = H1 + introduzione unica + griglia linkata + `ItemList`. | P0 | L |
| 2.2 | **Sconfiggi il thin content:** arricchisci le 868 pagine *thin* (<200 char) con contesto su autore/opera, durata, lettore, estratto dalla trascrizione (ne hai 1.300). Obiettivo: contenuto **unico** ben oltre le ~267 parole attuali. | P0 | L |
| 2.3 | **Pagine autore ricche:** aggiungi una breve bio/contesto (E-E-A-T) oltre alla lista titoli; parti dai top per volume (A. L. Knorr, e i grandi classici). | P1 | M |
| 2.4 | **Pagine-lettore/voce** (`readBy`): valorizza le voci ricorrenti (Zanardi, La Melodia delle Parole, Ad Alta Voce/Rai) — query di nicchia fedeli. | P2 | M |
| 2.5 | **Pulisci la tassonomia:** non esporre le categorie grezze YouTube; consolida i 23 generi, riequilibra la copertura, aggiungi testo introduttivo unico agli hub di genere. | P1 | M |
| 2.6 | **Pagine-confronto** ("alternative gratuite ad Audible", "RaiPlay Sound: catalogo e alternative"): catturano keyword di brand altrui, con il catalogo vero come prova. | P2 | M |

## FASE 3 — Autorità, scala & lancio · *mese 3–6*

| # | Azione | Prio | Effort |
|---|---|---|---|
| 3.1 | **Lancio social** Telegram + FB (vedi §5) — **solo dopo** che la Fase 1 è live. | P0 | S |
| 3.2 | **Link building mirato:** fatti (ri)citare dagli aggregatori che già ti menzionano (navigaweb) e da chi non lo fa ancora; proponiti come fonte gratuita nelle liste "audiolibri gratis 2026". | P1 | M |
| 3.3 | **Freschezza:** indicizza i nuovi caricamenti più rapidamente degli archivi statici — è un vantaggio competitivo verso LibriVox/Liber Liber. Ping IndexNow ad ogni deploy. | P1 | S |
| 3.4 | **Espansione catalogo mirata** verso i buchi di mercato (classici scolastici, giallo/thriller, bambini): sono domanda alta con offerta gratuita frammentata. | P2 | L |
| 3.5 | **Cloudflare in proxy** (vedi §6) per Brotli/HTTP-3/WAF/analytics + IndexNow integrato. | P1 | M |


# 5. Il lancio — sfruttare Telegram 8k + FB 5k (un colpo solo)

Hai **~13.000 persone** raggiungibili con un post. È munizione da spendere **una volta**. Tre principi:

1. **Timing.** Spara **dopo la Fase 1**, non prima. Una home istantanea converte e trattiene; una lenta brucia la prima impressione.
2. **Il vero premio è la *brand search*.** Il valore SEO di un burst social non sono i click (che Google non conta direttamente), ma le persone che nei giorni successivi **cercano "audiolibri.org" su Google**: è uno dei segnali di autorità più forti. Quindi il post deve spingere il **nome**, non solo il link.
3. **Un gancio, non un annuncio.** Non "ecco il mio sito", ma un **valore preciso** con una micro-call-to-action ripetibile.

**Bozza post (Telegram — adattare tono):**

> 🎧 **2.806 audiolibri in italiano, gratis. Senza registrazione, senza app, senza pubblicità.**
>
> Ho passato mesi a costruire **audiolibri.org**: un catalogo curato di audiolibri liberi — romanzi, racconti, fiabe, classici, gialli, horror — che ascolti **subito** dal browser. Cerchi un titolo o un autore e parte.
>
> 👉 **audiolibri.org**
>
> Se ti è utile: **salvalo tra i preferiti**, mandalo a chi ama leggere, e — se lo cerchi su Google come *"audiolibri.org"* — mi dai una mano più di mille like. 🙏
>
> Open source, per chi ama la letteratura italiana. ❤️

**Per Facebook:** stessa sostanza, aggiungi **1 immagine forte** (screenshot della home o una copertina d'autore) — il post con immagine gira di più. Includi 2–3 titoli-esca famosi ("*I Promessi Sposi*, *L'Imbecille* di Pirandello, i racconti di Poe…").

> **STOP — cosa NON fare al lancio.** ❌ Non lanciare prima della Fase 1. ❌ Non linkare una pagina-titolo a caso: manda alla **home** (o a una **collezione** curata, ancora meglio). ❌ Non chiedere solo "like": chiedi **salvataggio + ricerca del nome**. ❌ Non ripetere il post a raffica: **un colpo, fatto bene**, poi follow-up solo su novità concrete.


# 6. Cloudflare — la decisione

**Verdetto: attiva il proxy, ma con la consapevolezza che il ROI è *incrementale* (Fastly è già veloce), non trasformativo.** I guadagni reali stanno in ciò che GitHub Pages **non** ti dà: Brotli end-to-end, HTTP/3, edge-cache dell'HTML sotto tuo controllo, header di sicurezza, **WAF/rate-limiting**, **analytics server-side** privacy-friendly, e **IndexNow integrato**.

**Configurazione sicura (per evitare l'unico rischio serio, il redirect-loop SSL):**

1. Conferma che GitHub Pages abbia emesso il certificato Let's Encrypt e che *Enforce HTTPS* sia attivo.
2. In Cloudflare: **SSL/TLS = Full (strict)**, **Always Use HTTPS = ON**, **HTTP/3 = ON**, **Brotli = ON**. *(Mai "Flexible": è la causa classica del loop.)*
3. **Cache Rules** aggressive su `*.css`, `*.js`, `*.json`, immagini, `/audiolibro/*` — con **purge automatico nel workflow di deploy** (GitHub Action → Cloudflare purge API), altrimenti servi versioni stale.
4. **Transform/Response Header Rules** per HSTS e `X-Content-Type-Options` (impossibili su GH Pages).
5. Attiva **Web Analytics** (senza cookie) per dati di traffico reali.

> **Nota:** questa è un'operazione di **Fase 3**. Prima l'indice leggero e la home statica (Fase 1) — quelli valgono molto più di qualsiasi tuning di CDN.


# 7. Misurazione — KPI e strumenti

**Strumenti da attivare subito:** Google Search Console, Bing Webmaster Tools, PageSpeed Insights / CrUX, (in Fase 3) Cloudflare Web Analytics. Il rich-results monitoring vale solo per `BreadcrumbList` (vedi §8).

| KPI | Dove | Obiettivo 90 giorni |
|---|---|---|
| Pagine **indexed** (vs discovered/crawled-not-indexed) | GSC → Pages | Ridurre a zero i "thin" non indicizzati; ≥ 95% del catalogo indexed |
| **Impressioni & click** organici | GSC → Performance | Crescita costante; monitorare query long-tail titolo/autore |
| Query in **brand search** ("audiolibri.org") | GSC | Picco misurabile dopo il lancio, poi *plateau più alto* del pre-lancio |
| **Core Web Vitals** (home + titolo) | PSI / CrUX | Tutti e tre **Buono** su mobile |
| Posizione media su **cluster long-tail** | GSC | Scalata su titoli/autori/collezioni |
| **Backlink / citazioni** dagli aggregatori | GSC → Links | +N nuovi domini referenti |


# 8. Stop doing — la parte senza pietà

Cose su cui **non** spendere un minuto (o da smettere):

- ❌ **Non aggiungere `Review`/`AggregateRating` self-serve.** Google li considera non idonei ai rich snippet e, se gonfiati, sono a **rischio azione manuale** (perdita di *tutti* i rich result). Solo recensioni utente reali e moderate, un giorno, andrebbero marcate.
- ❌ **Non contare sui `FAQPage` per i rich result:** Google li **ha ritirati il 7 maggio 2026**. Il markup non fa male, ma non porta più snippet → valuta di **rimuoverlo per alleggerire l'HTML** e converti le FAQ in testo utile.
- ❌ **Non inseguire un "rich result Audiobook":** non esiste in Google. I *Book Actions* sono riservati a grandi provider con feed dedicati: non per te. Il markup `Audiobook` serve per **comprensione dell'entità e crawler AI**, ed è già a posto.
- ❌ **Non affidarti a IndexNow per Google:** Google **non lo usa**. IndexNow spinge su Bing/Yandex/Naver/Seznam (utile, gratis, fallo) — ma per Google la leva resta **sitemap + GSC + lastmod affidabili + link interni**.
- ❌ **Non preoccuparti del crawl budget:** a 2.806 pagine non è un tuo problema. Il nemico è il **thin content**, non il numero di pagine.
- ❌ **Non riscrivere ciò che già funziona:** le pagine-titolo statiche sono un asset. L'intervento è **additivo** (indice leggero, collezioni, arricchimento), non una rifattorizzazione.


# Appendice A — Checklist tecnica SEO

**Fondamenta (Fase 0)**

- [ ] GSC verificato + sitemap inviata + request indexing sulle pagine chiave
- [ ] Bing Webmaster verificato + sitemap
- [ ] `fb_test.html`, `fb_embed_test.html`, `changelog.json` rimossi dal deploy
- [ ] `/site.webmanifest` root corretto o rimosso (resta `/icons/site.webmanifest`)
- [ ] `offline.html` → `noindex`
- [ ] `robots.txt` con `Disallow` file tecnici + chiave IndexNow alla root

**Performance & rendering (Fase 1)**

- [ ] `index.min.json` leggero generato in build (~90 KB gzip)
- [ ] Home carica l'indice, non il catalogo intero; `no-cache` rimosso; asset versionati
- [ ] Home con link statici (`<a href>`) a hub + titoli in evidenza (crawlabile senza JS)
- [ ] `width`/`height` su tutte le copertine (anti-CLS)
- [ ] CWV mobile: LCP ≤ 2,5 s · INP ≤ 200 ms · CLS ≤ 0,1 (verificati su PSI/CrUX)

**Contenuto (Fase 2)**

- [ ] Pagine-collezione: bambini, scuola, giallo, horror, brevi, integrali
- [ ] 868 pagine *thin* arricchite con contenuto unico
- [ ] Pagine autore con bio/contesto; tassonomia generi consolidata
- [ ] `title`/description unici su ogni pagina; canonical corretti

**Infrastruttura & autorità (Fase 3)**

- [ ] Cloudflare proxy: Full(strict) + HTTP/3 + Brotli + Cache Rules + purge automatico
- [ ] Header di sicurezza (HSTS, X-Content-Type-Options)
- [ ] Ping IndexNow automatico ad ogni deploy
- [ ] Lancio social eseguito **dopo** Fase 1
- [ ] Campagna citazioni/backlink verso gli aggregatori

# Appendice B — Riferimenti

Dati strutturati e rich results: Google Search Central (Book, Review snippet, FAQPage), schema.org/Audiobook. · Ritiro FAQ rich results (7 mag 2026): Search Engine Journal. · JavaScript SEO e rendering a due onde: Google Search Central (JavaScript SEO basics). · Core Web Vitals: web.dev (defining CWV thresholds), Google Search (CWV & Search). · Crawl budget e siti grandi: Google Search Central (large-site crawl budget). · Programmatic SEO / thin content e internal linking: digitalapplied.com. · Cloudflare + GitHub Pages e redirect-loop SSL: blog.cloudflare.com, miliucci.org. · IndexNow: bing.com/indexnow. · Dati di mercato audiolibri Italia 2025–2026: ilLibraio, il Narratore, Giornale della Libreria, editoria-digitale.com.

*Documento redatto il 19 luglio 2026 sulla base di analisi tecnica diretta del sito e del repository, ricerca competitiva e verifica delle linee guida SEO aggiornate.*
