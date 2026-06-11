#!/usr/bin/env python3
import os
import sys
import json
import re
import time
import argparse
from datetime import datetime
import yt_dlp
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table

# Try importing validation logic from existing scraper to ensure consistency
try:
    from audiobook_scraper import is_valid_audiobook, BLACKLIST_CHANNELS, BLACKLIST_IDS
except ImportError:
    # Fallback to copy of rules if import fails
    BLACKLIST_CHANNELS = {
        'iaraculonna', 'LaraBellyDance', 'giuliomania', 'I film di Mondo TV',
        'Jason Stephenson - Sleep Meditation Music', 'Nigel John Stanford', 'Jason Headley',
        'TheVideoCellar', 'Warner Bros. Italia', 'Veronicartoon', 'Film&Clips', 'Audio Books',
        'Incredible Librivox Audiobooks', 'Bardic Knowledge', 'Fab Audio Books', 'English Audio Books',
        'AudioLibros: MaginBooks', 'AMA Audiolibros', 'EducaBabyTV', 'Enrico Brignano Ufficiale',
        'Greatest AudioBooks', 'Art and Design', 'giuseppe pugliese'
    }
    BLACKLIST_IDS = {
        'IsvALeok750', 'CrEtgLpoWgE', 'GE8Dj701Q0M', 'xyx-RMoPyZo', 'FTkXdSKljOI', 'pKSVywHXd8Y',
        'f199fI0jG6Q', 'Mv8EFsjKMow', 'nWRYL_XuJtE', 'xFUkkzAQyXU', 'JCLzc7S5xSY', 'fUbl5wiRtR8',
        'es36GaQeAKk'
    }
    
    def is_valid_audiobook(video_id, title, channel):
        if video_id in BLACKLIST_IDS:
            return False, "Blacklisted video ID"
        if channel.strip().lower() in [c.lower() for c in BLACKLIST_CHANNELS]:
            return False, f"Blacklisted channel: {channel}"
        title_lower = title.lower()
        if ('fiorello' in title_lower and 'baldini' in title_lower) or \
           ('fiorello' in title_lower and 'bongiorno' in title_lower) or \
           ('fiorello imita' in title_lower) or \
           ('viva radio' in title_lower):
            return False, "Fiorello comedy parody pattern"
        if any(w in title_lower for w in ['audiobook', 'full audiobook', 'unabridged', 'translated by', 'read by']) and \
           not any(w in title_lower for w in ['italiano', 'ita', 'tradotto']):
            return False, "English audiobook title pattern"
        return True, ""

console = Console()

# Standard list of vetted Italian audiobook channels
VETTED_CHANNELS = {
    "Ménéstrandise Audiolibri": "https://www.youtube.com/@MenestrandiseAudiolibri/videos",
    "Beneinst": "https://www.youtube.com/@Beneinst/videos",
    "Storie da Grammofono": "https://www.youtube.com/@StoriedaGrammofono/videos",
    "AUDIUM Audiolibri": "https://www.youtube.com/@AUDIUMAudiolibri/videos",
    "Il Rugo Audiolibri": "https://www.youtube.com/@ilrugoaudiolibri/videos",
    "La Locanda della Tormenta": "https://www.youtube.com/@LaLocandadellaTormenta/videos",
    "Audiolibri Italiano by AC": "https://www.youtube.com/@AudiolibriItalianobyAC/videos",
    "DAGON Audiolibri": "https://www.youtube.com/@DAGONAudiolibri/videos",
    "La biblioteca che non c'è": "https://www.youtube.com/@Labibliotecachenonce/videos",
    "VALTER ZANARDI letture": "https://www.youtube.com/@leggopervoi/videos",
    "Audiolibri Lorenzo Pieri": "https://www.youtube.com/@LorenzoPieriAudiolibri/videos",
    "Luigi Bellanca - Audiolibri e audioracconti": "https://www.youtube.com/@LuigiBellanca_audiolibri/videos",
    "Luigi Loperfido audiolibri": "https://www.youtube.com/@lavocedeltesto50/videos"
}

# Standard Italian keywords that should be present in titles or descriptions
ITALIAN_KEYWORDS = [
    "audiolibro", "audiolibri", "lettura", "integrale", "romanzo", "racconto", 
    "poesia", "capitolo", "fiaba", "fiabe", "favola", "favole", "voce", "leggo",
    "italiano", "letteratura", "classico", "giallo", "horror"
]

def load_databases():
    """Load both audiobooks.json and augmented.json"""
    audiobooks = {}
    augmented = {}
    
    if os.path.exists("audiobooks.json"):
        try:
            with open("audiobooks.json", "r", encoding="utf-8") as f:
                audiobooks = json.load(f)
        except Exception as e:
            console.log(f"[bold red]Error loading audiobooks.json:[/bold red] {e}")
            
    if os.path.exists("augmented.json"):
        try:
            with open("augmented.json", "r", encoding="utf-8") as f:
                augmented = json.load(f)
        except Exception as e:
            console.log(f"[bold red]Error loading augmented.json:[/bold red] {e}")
            
    return audiobooks, augmented

def save_databases(audiobooks, augmented):
    """Save both audiobooks.json and augmented.json with backups"""
    for filepath, data in [("audiobooks.json", audiobooks), ("augmented.json", augmented)]:
        if os.path.exists(filepath):
            backup_path = f"{filepath}.bak"
            try:
                import shutil
                shutil.copy2(filepath, backup_path)
            except Exception as e:
                console.log(f"[bold yellow]Warning:[/bold yellow] Failed to create backup for {filepath}: {e}")
        try:
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            console.log(f"✅ Saved database: [green]{filepath}[/green] ({len(data)} total books)")
        except Exception as e:
            console.log(f"[bold red]Error saving {filepath}:[/bold red] {e}")

def clean_html(text):
    if not text:
        return ""
    clean = re.compile('<.*?>')
    clean_text = re.sub(clean, '', text)
    return re.sub(r'\s+', ' ', clean_text).strip()

def load_known_authors(augmented_data):
    """Extract all unique author names from existing database to use as lookup clues"""
    authors = set()
    for book in augmented_data.values():
        author = book.get("real_author")
        if author and author != "Autore Sconosciuto" and "Lettore" not in author:
            author_clean = author.strip()
            # Only use full names with spaces, and avoid short/generic words
            if ' ' in author_clean and len(author_clean) > 5:
                author_lower = author_clean.lower()
                # Skip garbage words
                garbage = ['capitolo', 'parte', 'volume', 'sezione', 'italia', 'audiolibro', 'romanzo', 'racconto', 'lettura']
                if not any(w in garbage for w in author_lower.split()):
                    authors.add(author_lower)
    return authors

def guess_genre(title, description):
    content = f"{title} {description}".lower()
    
    # Use word boundary searches to avoid substring matching bugs (like 'versi' in 'versione')
    if re.search(r'\b(poesia|poesie|lirica|liriche|versi|canti|poema|poemi)\b', content):
        return 'poesia'
    if re.search(r'\b(racconto|racconti|novella|novelle|aneddoto|aneddoti)\b', content):
        return 'racconto'
    if re.search(r'\b(saggio|saggi|filosofia|filosofico|trattato|trattati|critica|divulgazione)\b', content):
        return 'saggio'
    if re.search(r'\b(fiaba|fiabe|favola|favole|fiabesco|storytelling)\b', content):
        return 'fiaba'
    if re.search(r'\b(fantascienza|fantascietifico|sci-fi|distopia|distopico|cyberpunk)\b', content):
        return 'fantascienza'
    if re.search(r'\b(giallo|gialli|thriller|noir|poliziesco|polizieschi|investigatore|sherlock|grisham|christie|doyle)\b', content):
        return 'giallo'
    if re.search(r'\b(horror|terrore|gotico|gotica|splatter|fantasmi|lovecraft|dracula|frankenstein)\b', content):
        return 'horror'
    if re.search(r'\b(avventura|avventure|pirati|salgari|verne|dumas|corsaro)\b', content):
        return 'avventura'
    return 'romanzo' # Default fallback

def guess_author_and_title(title, channel, known_authors=None):
    """Programmatic heuristic to parse author and book title from YouTube titles"""
    # Common classic authors fallback
    classic_authors = {
        'dante alighieri', 'dante', 'giovanni verga', 'verga', 'fedor dostoevskij', 'dostoevskij', 
        'dostoevsky', 'alessandro manzoni', 'manzoni', 'luigi pirandello', 'pirandello', 
        'italo svevo', 'svevo', 'giovanni boccaccio', 'boccaccio', 'carlo collodi', 'collodi', 
        'emilio salgari', 'salgari', 'giacomo leopardi', 'leopardi', 'ugo foscolo', 'foscolo', 
        'gabriele d\'annunzio', 'd\'annunzio', 'edgar allan poe', 'poe', 'howard phillips lovecraft', 
        'lovecraft', 'h.p. lovecraft', 'franz kafka', 'kafka', 'william shakespeare', 'shakespeare', 
        'arthur conan doyle', 'conan doyle', 'agatha christie', 'christie', 'jules verne', 'verne', 
        'guy de maupassant', 'maupassant', 'anton cechov', 'cechov', 'chekhov', 'lev tolstoj', 
        'tolstoj', 'tolstoy', 'oscar wilde', 'wilde', 'george orwell', 'orwell', 'charles dickens', 
        'dickens', 'homero', 'omero', 'virginia woolf', 'woolf', 'jane austen', 'austen', 
        'giovanni pascoli', 'pascoli', 'giorgio bassani', 'bassani', 'italo calvino', 'calvino', 
        'elsa morante', 'morante', 'natalia ginzburg', 'ginzburg', 'gianni rodari', 'rodari', 
        'umberto eco', 'eco', 'primo levi', 'levi', 'dino buzzati', 'buzzati', 'cesare pavese', 'pavese',
        'augusto de angelis', 'de angelis', 'willa cather', 'cather'
    }
    
    all_known_authors = classic_authors
    if known_authors:
        all_known_authors = all_known_authors.union(known_authors)

    # 1. First, check if the raw title contains a pipe '|'
    clean_title = title
    found_author = None
    
    if '|' in clean_title:
        pipe_parts = [p.strip() for p in clean_title.split('|') if p.strip()]
        # Check if any part (except the first one, which is usually the title) has a known author name
        for part in pipe_parts[1:]:
            for name in sorted(all_known_authors, key=len, reverse=True):
                if len(name) > 4 and name in part.lower():
                    idx = part.lower().find(name)
                    found_author = part[idx:idx+len(name)].title()
                    break
            if found_author:
                break
        
        # If author was found in a pipe tag, the first part is the title
        if found_author:
            if known_authors:
                for orig in known_authors:
                    if orig.lower() == found_author.lower():
                        found_author = orig
                        break
            
            real_title = pipe_parts[0]
            real_title = re.sub(r'\[.*?\]|\(.*?\)', '', real_title)
            real_title = re.sub(r'(?i)\baudiolibro\b|\bcompleto\b|\bintegrale\b|\bletto da\b.*', '', real_title)
            real_title = re.sub(r'\s+', ' ', real_title).strip().strip('-,:–—|').strip()
            
            for name in all_known_authors:
                if found_author.lower() == name:
                    if name == 'guy de maupassant': found_author = 'Guy de Maupassant'
                    elif name == 'augusto de angelis': found_author = 'Augusto De Angelis'
                    elif name == 'giovanni verga': found_author = 'Giovanni Verga'
                    elif name == 'willa cather': found_author = 'Willa Cather'
                    break
            return found_author, real_title

    # 2. If not found in pipes, clean brackets/tags/pipes, then look for known author in clean_title
    clean_title = re.sub(r'\[.*?\]|\(.*?\)', '', title)
    clean_title = re.sub(r'(?i)\baudiolibro\b|\bcompleto\b|\bintegrale\b|\bletto da\b.*', '', clean_title)
    clean_title = re.sub(r'\|.*', '', clean_title).strip()
    
    for name in sorted(all_known_authors, key=len, reverse=True):
        if len(name) > 4 and name in clean_title.lower():
            idx = clean_title.lower().find(name)
            start_boundary = idx == 0 or not clean_title[idx-1].isalnum()
            end_boundary = idx + len(name) == len(clean_title) or not clean_title[idx + len(name)].isalnum()
            if start_boundary and end_boundary:
                found_author = clean_title[idx:idx+len(name)].title()
                if known_authors:
                    for orig in known_authors:
                        if orig.lower() == name:
                            found_author = orig
                            break
                            
                author_regex = re.compile(re.escape(found_author), re.IGNORECASE)
                real_title = author_regex.sub('', clean_title).strip().strip('-,:–—|').strip()
                real_title = re.sub(r'\s+', ' ', real_title).strip()
                
                for n in all_known_authors:
                    if found_author.lower() == n:
                        if n == 'guy de maupassant': found_author = 'Guy de Maupassant'
                        elif n == 'augusto de angelis': found_author = 'Augusto De Angelis'
                        elif n == 'giovanni verga': found_author = 'Giovanni Verga'
                        elif n == 'willa cather': found_author = 'Willa Cather'
                        break
                return found_author, real_title

    # 3. Fallback to splitting by separators if still not found
    seps = [' – ', ' — ', ' - ', ' : ']
    split_parts = []
    for sep in seps:
        if sep in clean_title:
            split_parts = [p.strip() for p in clean_title.split(sep)]
            break
            
    author = "Autore Sconosciuto"
    real_title = clean_title
    
    if len(split_parts) >= 2:
        part1 = split_parts[0]
        part2 = split_parts[1]
        
        title_words = ['capitolo', 'parte', 'ep.', 'episodio', 'sezione', 'vol.', 'volume', 'cap.']
        p1_has_title_word = any(w in part1.lower() for w in title_words)
        p2_has_title_word = any(w in part2.lower() for w in title_words)
        
        is_p1_author = False
        
        if p1_has_title_word and not p2_has_title_word:
            is_p1_author = False
        elif p2_has_title_word and not p1_has_title_word:
            is_p1_author = True
        else:
            p1_words = len(part1.split())
            p2_words = len(part2.split())
            if p2_words > p1_words:
                is_p1_author = True
            else:
                is_p1_author = False
                
        if is_p1_author:
            author = part1
            real_title = part2
        else:
            author = part2
            real_title = part1
    else:
        channel_clean = channel.lower()
        if "lorenzo pieri" in channel_clean:
            author = "Lorenzo Pieri (Lettore)"
        elif "valter zanardi" in channel_clean:
            author = "Valter Zanardi (Lettore)"
            
    author = re.sub(r'\s+', ' ', author).strip().strip('-,:–—|').strip()
    real_title = re.sub(r'\s+', ' ', real_title).strip().strip('-,:–—|').strip()
    
    if author.isupper() and len(author) > 3:
        author = author.title()
    if real_title.isupper() and len(real_title) > 3:
        real_title = real_title.capitalize()
        
    return author, real_title

def guess_narrator(channel, description):
    """Parse narrator/reader from channel or description"""
    channel_lower = channel.lower()
    if "valter zanardi" in channel_lower:
        return "Valter Zanardi"
    if "lorenzo pieri" in channel_lower:
        return "Lorenzo Pieri"
    if "faustino stigliani" in channel_lower:
        return "Faustino Stigliani"
    if "martina sollazzi" in channel_lower:
        return "Martina Sollazzi"
        
    m = re.search(r'(?i)legge\s+([A-Z][a-z]+\s+[A-Z][a-z]+)', description)
    if m:
        return m.group(1)
    m = re.search(r'(?i)voce\s+di\s+([A-Z][a-z]+\s+[A-Z][a-z]+)', description)
    if m:
        return m.group(1)
    m = re.search(r'(?i)letto\s+da\s+([A-Z][a-z]+\s+[A-Z][a-z]+)', description)
    if m:
        return m.group(1)
        
    return channel

def search_youtube_candidates(queries, limit=100, min_duration=1200):
    """Use yt-dlp in flat mode to fetch candidates from search queries"""
    candidates = {}
    
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'skip_download': True,
        'no_warnings': True,
        'playlistend': limit
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for q in queries:
            query_str = f"ytsearch{limit}:{q}"
            console.log(f"🔍 Executing search query: [cyan]'{q}'[/cyan]...")
            try:
                results = ydl.extract_info(query_str, download=False)
                entries = results.get("entries", [])
                console.log(f"   Found {len(entries)} raw search entries.")
                
                for entry in entries:
                    if not entry:
                        continue
                    video_id = entry.get("id")
                    title = entry.get("title", "")
                    uploader = entry.get("uploader", "")
                    duration = entry.get("duration")
                    
                    if not video_id:
                        continue
                        
                    # Basic filters in Pass 1
                    if duration is not None and duration < min_duration:
                        continue # Skip short clips
                        
                    # Check channel and ID blacklist
                    valid, reason = is_valid_audiobook(video_id, title, uploader)
                    if not valid:
                        continue
                        
                    # Check Italian language heuristics in title
                    title_lower = title.lower()
                    if not any(w in title_lower for w in ITALIAN_KEYWORDS):
                        continue # Skip if no Italian audiobook indicator
                        
                    candidates[video_id] = {
                        'id': video_id,
                        'title': title,
                        'channel': uploader,
                        'duration': duration,
                        'url': f"https://www.youtube.com/watch?v={video_id}"
                    }
            except Exception as e:
                console.log(f"[bold red]Error during query '{q}':[/bold red] {e}")
                
    return candidates

def crawl_channel_candidates(channel_urls, limit=100, min_duration=1200):
    """Use yt-dlp in flat mode to fetch candidates from specific channel pages/handles"""
    candidates = {}
    
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'skip_download': True,
        'no_warnings': True,
        'playlist_items': f'1-{limit}' # Crawl only the recent uploads (typically limit = 100)
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        for name, url in channel_urls.items():
            console.log(f"📡 Indexing channel: [cyan]{name}[/cyan] ({url})...")
            try:
                # Resolve uploads playlist to make it extremely fast
                results = ydl.extract_info(url, download=False)
                
                # Check for playlist entries
                entries = []
                if results.get('_type') == 'playlist' or 'entries' in results:
                    entries = results.get('entries', [])
                else:
                    entries = [results]
                    
                console.log(f"   Fetched {len(entries)} recent uploads.")
                
                for entry in entries:
                    if not entry:
                        continue
                    video_id = entry.get("id")
                    title = entry.get("title", "")
                    uploader = entry.get("uploader", name)
                    duration = entry.get("duration")
                    
                    if not video_id:
                        continue
                        
                    if duration is not None and duration < min_duration:
                        continue
                        
                    valid, reason = is_valid_audiobook(video_id, title, uploader)
                    if not valid:
                        continue
                        
                    candidates[video_id] = {
                        'id': video_id,
                        'title': title,
                        'channel': uploader,
                        'duration': duration,
                        'url': f"https://www.youtube.com/watch?v={video_id}"
                    }
            except Exception as e:
                console.log(f"[bold red]Error crawling channel '{name}':[/bold red] {e}")
                
    return candidates

def extract_candidate_metadata(video_id):
    """Fetch rich metadata for a single video ID"""
    ydl_opts = {
        'format': 'bestaudio',
        'quiet': True,
        'skip_download': True,
        'no_warnings': True,
        'socket_timeout': 15,
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
        return info

def run_discovery(queries=None, channels=None, limit=100, min_duration=1200, ingest=False):
    console.print(Panel("[bold green]YouTube Audiobook Discovery Tool[/bold green]"))
    
    # Load databases to de-duplicate
    audiobooks, augmented = load_databases()
    console.log(f"Loaded database with {len(audiobooks)} existing audiobooks.")
    
    # Extract known authors from database for title-author splitting
    known_authors = load_known_authors(augmented)
    
    # 1. Discover candidates
    raw_candidates = {}
    
    if channels:
        # Index specific vetted channels
        channel_map = {name: url for name, url in VETTED_CHANNELS.items() if name in channels or not channels}
        if channels == ['all']:
            channel_map = VETTED_CHANNELS
        raw_candidates.update(crawl_channel_candidates(channel_map, limit, min_duration))
        
    if queries:
        # Index search queries
        raw_candidates.update(search_youtube_candidates(queries, limit, min_duration))
        
    if not raw_candidates:
        console.log("[yellow]No candidates found. Exiting.[/yellow]")
        return
        
    # Filter out duplicates already in DB
    new_candidates = {vid: c for vid, c in raw_candidates.items() if vid not in audiobooks}
    
    console.print(Panel(f"Discovered [bold green]{len(raw_candidates)}[/bold green] total candidates.\n"
                        f"Already in library: [cyan]{len(raw_candidates) - len(new_candidates)}[/cyan]\n"
                        f"New candidates to evaluate: [bold magenta]{len(new_candidates)}[/bold magenta]"))
                        
    if not new_candidates:
        console.log("[yellow]No new candidates to ingest. Done.[/yellow]")
        return
        
    # Limit number of rich extractions to process to avoid rate limits
    candidate_list = list(new_candidates.values())
    
    # Let's perform Pass 2: Extract rich details and save
    ingested_count = 0
    
    table = Table(title="New Ingestion Candidates", show_header=True, header_style="bold magenta")
    table.add_column("Video ID", style="dim")
    table.add_column("Title", style="cyan")
    table.add_column("Channel", style="green")
    table.add_column("Duration", justify="right")
    
    for c in candidate_list[:30]: # Print sample table
        dur_str = f"{int(c['duration']//3600)}h {int((c['duration']%3600)//60)}m" if c.get('duration') else "Unknown"
        table.add_row(c['id'], c['title'][:50], c['channel'][:25], dur_str)
    console.print(table)
    if len(candidate_list) > 30:
        console.print(f"... and {len(candidate_list) - 30} more candidates.")
        
    if not ingest:
        console.print("\n[bold yellow]DRY-RUN COMPLETE[/bold yellow]. Run with [bold green]--ingest[/bold green] to save them to the database.")
        # Save candidates list to JSON file for manual inspection
        with open("discovered_candidates.json", "w", encoding="utf-8") as f:
            json.dump(candidate_list, f, indent=2, ensure_ascii=False)
        console.log("Saved candidates to [green]discovered_candidates.json[/green].")
        return
        
    # Process and Ingest
    console.print(f"\n🚀 Ingesting metadata for {len(candidate_list)} new audiobooks...")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("[cyan]Ingesting...", total=len(candidate_list))
        
        for idx, candidate in enumerate(candidate_list):
            video_id = candidate['id']
            progress.update(task, description=f"[{idx+1}/{len(candidate_list)}] Fetching {video_id}...")
            
            try:
                info = extract_candidate_metadata(video_id)
                if not info:
                    continue
                    
                title = info.get('title', candidate['title'])
                channel = info.get('channel', info.get('uploader', candidate['channel']))
                channel_url = info.get('channel_url', info.get('uploader_url', ''))
                duration = float(info.get('duration') or candidate.get('duration') or 0)
                description = clean_html(info.get('description', ''))
                
                # Check is_valid_audiobook again with description info if needed
                valid, reason = is_valid_audiobook(video_id, title, channel)
                if not valid:
                    console.log(f"⚠️ Skipped {video_id} during detailed validation: {reason}")
                    progress.update(task, advance=1)
                    continue
                    
                # Programmatically guess fields
                author, real_title = guess_author_and_title(title, channel, known_authors=known_authors)
                genre = guess_genre(title, description)
                narrator = guess_narrator(channel, description)
                
                # Create main database entry
                audiobooks[video_id] = {
                    'title': title,
                    'channel': channel,
                    'channel_url': channel_url,
                    'duration': duration,
                    'upload_date': info.get('upload_date', 'Unknown'),
                    'description': info.get('description', ''),
                    'transcript': "",
                    'view_count': info.get('view_count', 0),
                    'like_count': info.get('like_count', 0),
                    'download_date': datetime.now().isoformat(),
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'audio_file': '',
                    'processed': False,
                    'summary': description[:200] + '...' if len(description) > 200 else description,
                    'thumbnail': info.get('thumbnail', f"https://i.ytimg.com/vi/{video_id}/sddefault.jpg"),
                    'tags': info.get('tags', ['YouTube', 'Italiano']),
                    'categories': info.get('categories', ['People & Blogs'])
                }
                
                # Create augmented database entry
                augmented[video_id] = {
                    **audiobooks[video_id],
                    'source': 'youtube',
                    'source_url': f"https://www.youtube.com/watch?v={video_id}",
                    'embed_type': 'youtube',
                    'embed_url': f"https://www.youtube-nocookie.com/embed/{video_id}",
                    'audio_url': '',
                    'audio_chapters': [],
                    'license': 'platform_tos',
                    'real_title': real_title,
                    'real_author': author,
                    'real_genre': genre,
                    'real_synopsis': description,
                    'content_type': 'audiobook',
                    'real_language': 'it',
                    'real_narrator': narrator
                }
                
                ingested_count += 1
                progress.update(task, advance=1)
                
                # Be polite to YouTube servers
                time.sleep(0.5)
                
            except Exception as e:
                console.log(f"[bold red]Failed to extract rich metadata for {video_id}:[/bold red] {e}")
                progress.update(task, advance=1)
                
    if ingested_count > 0:
        save_databases(audiobooks, augmented)
        console.print(Panel(f"🎉 Successfully ingested [bold green]{ingested_count}[/bold green] new YouTube audiobooks!"))
    else:
        console.print("[yellow]No new audiobooks were successfully ingested.[/yellow]")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='YouTube Audiobook Discovery and Ingestion Tool')
    parser.add_argument('--queries', help='Comma-separated search queries (e.g. "audiolibro completo italiano, romanzo integrale")')
    parser.add_argument('--channels', help='Comma-separated vetted channel names to index (or "all" for all vetted channels)')
    parser.add_argument('--limit', type=int, default=100, help='Max results to crawl per query/channel (default 100)')
    parser.add_argument('--min-duration', type=int, default=1200, help='Min video duration in seconds (default 1200 = 20 mins)')
    parser.add_argument('--ingest', action='store_true', help='Ingest discovered candidates into databases')
    
    args = parser.parse_args()
    
    # Parse list parameters
    query_list = [q.strip() for q in args.queries.split(',')] if args.queries else []
    channel_list = [c.strip() for c in args.channels.split(',')] if args.channels else []
    
    # If no parameters provided, default to dry-run channel index for all vetted channels
    if not query_list and not channel_list:
        console.log("No inputs provided. Running discovery on all vetted channels by default...")
        channel_list = ['all']
        
    run_discovery(
        queries=query_list,
        channels=channel_list,
        limit=args.limit,
        min_duration=args.min_duration,
        ingest=args.ingest
    )
