#!/usr/bin/env python3
import os
import re
import sys
import json
import time
import html
import requests
import subprocess
import argparse
from urllib.parse import urlparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Vetted genre taxonomy logic
def guess_genre(title, description):
    content = f"{title} {description}".lower()
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
    if re.search(r'\b(teatro|tragedia|commedia|dramma|recita|atto|drammatico)\b', content):
        return 'teatro'
    return 'romanzo' # Default fallback

def clean_html(text):
    if not text:
        return ""
    clean = re.compile('<.*?>')
    clean_text = re.sub(clean, ' ', text)
    clean_text = html.unescape(clean_text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text

def clean_person_name(name):
    name = name.strip()
    if ',' in name:
        parts = [p.strip() for p in name.split(',')]
        if len(parts) == 2:
            return f"{parts[1]} {parts[0]}"
    return name

def get_mp3_duration(url):
    """Call ffprobe to get exact duration of a remote MP3 file"""
    cmd = [
        "ffprobe", "-v", "quiet", 
        "-show_entries", "format=duration", 
        "-of", "default=noprint_wrappers=1:nokey=1", 
        url
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
        if res.returncode == 0 and res.stdout.strip():
            return float(res.stdout.strip())
    except Exception as e:
        print(f"    ffprobe failed for {url}: {e}")
    return 0.0

def scrape_liberliber(limit=20, dry_run=False, verbose=False):
    print("=" * 60)
    print("📚 Liber Liber Audiobook Ingestor & Scraper")
    print("=" * 60)
    
    # Paths to database files
    audiobooks_path = 'audiobooks.json'
    augmented_path = 'augmented.json'
    
    # Load database
    audiobooks = {}
    augmented = {}
    if os.path.exists(audiobooks_path):
        with open(audiobooks_path, 'r', encoding='utf-8') as f:
            audiobooks = json.load(f)
    if os.path.exists(augmented_path):
        with open(augmented_path, 'r', encoding='utf-8') as f:
            augmented = json.load(f)
            
    print(f"Loaded {len(audiobooks)} existing books from database.")
    
    # Fetch index list
    index_url = "https://liberliber.it/opere/audiolibri/elenco-per-opere/"
    print(f"Fetching index page: {index_url}...")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        r = requests.get(index_url, headers=headers, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"❌ Failed to fetch index page: {e}")
        return
        
    # Extract <li> blocks
    li_blocks = re.findall(r'<li>(.*?)</li>', r.text, re.DOTALL | re.IGNORECASE)
    print(f"Found {len(li_blocks)} raw list items on page.")
    
    candidates = []
    for li in li_blocks:
        if "autori/autori-" not in li:
            continue
            
        work_match = re.search(r'<em>\s*<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>\s*</em>', li, re.DOTALL | re.IGNORECASE)
        author_match = re.search(r'di\s*<a\s+[^>]*href="([^"]+)"[^>]*>(.*?)</a>', li, re.DOTALL | re.IGNORECASE)
        
        if work_match and author_match:
            work_url = work_match.group(1).strip()
            work_title = clean_html(work_match.group(2))
            author_url = author_match.group(1).strip()
            author_name = clean_html(author_match.group(2))
            
            subtitle = ""
            sub_match = re.search(r'<span\s+class="ll_libro_sottotitolo"\s*>(.*?)</span>', li, re.DOTALL | re.IGNORECASE)
            if sub_match:
                subtitle = clean_html(sub_match.group(1))
                
            # Parse slug
            parsed_url = urlparse(work_url)
            slug = parsed_url.path.strip('/').split('/')[-1]
            if not slug:
                continue
                
            key = f"liberliber_{slug}"
            
            # De-duplicate
            if key in audiobooks:
                continue
                
            candidates.append({
                'key': key,
                'slug': slug,
                'work_url': work_url,
                'work_title': work_title,
                'author_url': author_url,
                'author_name': author_name,
                'subtitle': subtitle
            })
            
    print(f"Found {len(candidates)} new candidates to ingest (already skipped duplicates).")
    
    if not candidates:
        print("No new candidates. Done.")
        return
        
    # Process candidates up to limit
    ingested_count = 0
    
    for idx, c in enumerate(candidates):
        if ingested_count >= limit:
            print(f"Reached ingestion limit of {limit} books.")
            break
            
        print(f"\nProcessing [{idx+1}/{len(candidates)}]: [cyan]{c['work_title']}[/cyan] by {c['author_name']}...")
        print(f"  URL: {c['work_url']}")
        
        # Fetch work page
        try:
            time.sleep(1.0) # Be nice to Liber Liber
            work_resp = requests.get(c['work_url'], headers=headers, timeout=20)
            work_resp.raise_for_status()
            work_html = work_resp.text
        except Exception as e:
            print(f"  ❌ Failed to fetch page for {c['work_title']}: {e}")
            continue
            
        # Extract cover image
        cover_image = ""
        cover_match = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', work_html, re.IGNORECASE)
        if cover_match:
            cover_image = cover_match.group(1).strip()
            
        # Extract synopsis
        synopsis = ""
        post_match = re.search(r'<div class="post-content">(.*?)</div>\s*<div', work_html, re.DOTALL | re.IGNORECASE)
        if not post_match:
            post_match = re.search(r'<div class="post-content">(.*)', work_html, re.DOTALL | re.IGNORECASE)
            
        if post_match:
            post_content = post_match.group(1)
            # Split off list and tags
            synopsis_html = post_content
            for kw in ["Istruzioni", "Formato MP3", "Formato FLAC", "Formato Ogg", "class=\"ll_metadati_etichetta\""]:
                if kw in synopsis_html:
                    synopsis_html = synopsis_html.split(kw)[0]
            synopsis = clean_html(synopsis_html)
            
        # Extract narrator(s)
        narrators = []
        for match in re.finditer(r'<li>\s*([^<]+?)\s*\(ruolo:\s*Voce\)\s*</li>', work_html, re.IGNORECASE):
            name = clean_person_name(match.group(1))
            if name and name not in narrators:
                narrators.append(name)
                
        narrator_str = ", ".join(narrators) if narrators else "Liber Liber lettori"
        
        # Extract MP3 download links
        # Find all <a href="...mp3">TEXT</a>
        pattern = r'<a\s+[^>]*href="([^"]+?\.mp3)"[^>]*>(.*?)</a>'
        mp3_matches = re.findall(pattern, work_html, re.DOTALL | re.IGNORECASE)
        
        raw_chapters = []
        for m_url, m_title in mp3_matches:
            ch_url = m_url.strip()
            # If relative URL, make it absolute (though Liber Liber usually has absolute links)
            if ch_url.startswith('/'):
                ch_url = "https://www.liberliber.it" + ch_url
            elif not ch_url.startswith('http'):
                ch_url = "https://www.liberliber.it/" + ch_url
                
            ch_title = clean_html(m_title)
            # Avoid duplicate URLs
            if not any(ch['audio_url'] == ch_url for ch in raw_chapters):
                raw_chapters.append({
                    'title': ch_title,
                    'audio_url': ch_url
                })
                
        if not raw_chapters:
            print(f"  ⚠️  No MP3 tracks found on this page. Skipping.")
            continue
            
        # Clean chapter titles
        cleaned_chapters = []
        for ch in raw_chapters:
            t = ch['title']
            # Clean label
            t = re.sub(r'(?i)Copertina|Incipit', 'Copertina', t)
            t = re.sub(r'\s*\[.*?\]|\(.*?\)', '', t)
            t = re.sub(r'\s+', ' ', t).strip()
            if not t:
                # Fallback to filename
                filename = ch['audio_url'].split('/')[-1].replace('.mp3', '').replace('_', ' ')
                t = filename.title()
            cleaned_chapters.append({
                'title': t,
                'audio_url': ch['audio_url'],
                'duration': 0.0
            })
            
        print(f"  Found {len(cleaned_chapters)} MP3 chapters.")
        
        # Parallel query of durations via ffprobe
        print("  Querying chapter durations using ffprobe...")
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(get_mp3_duration, ch['audio_url']): idx for idx, ch in enumerate(cleaned_chapters)}
            for fut in futures:
                idx = futures[fut]
                dur = fut.result()
                cleaned_chapters[idx]['duration'] = dur
                if verbose:
                    print(f"    - Chapter {idx+1}: {cleaned_chapters[idx]['title']} ({dur:.1f}s)")
                    
        total_duration = sum(ch['duration'] for ch in cleaned_chapters)
        print(f"  Total Duration: {total_duration/3600:.2f} hours ({total_duration:.1f} seconds)")
        
        # Genre guessing
        genre = guess_genre(c['work_title'] + " " + c['subtitle'], synopsis)
        
        # Cleanup real title
        real_title = re.sub(r'\s*\[audiolibro\]', '', c['work_title'], flags=re.IGNORECASE).strip()
        if c['subtitle']:
            real_title = f"{real_title} - {c['subtitle']}"
            
        # Standardize author name
        real_author = c['author_name']
        if ',' in real_author:
            real_author = clean_person_name(real_author)
            
        # Standardize dates
        upload_date_match = re.search(r'data pubblicazione:.*?(\d{1,2})\s+([a-z]+)\s+(\d{4})', work_html, re.IGNORECASE | re.DOTALL)
        pub_year = "Unknown"
        if upload_date_match:
            pub_year = upload_date_match.group(3)
            
        # Create database entries
        main_entry = {
            'title': c['work_title'],
            'channel': 'Liber Liber',
            'channel_url': c['author_url'],
            'duration': total_duration,
            'upload_date': pub_year,
            'description': synopsis,
            'transcript': '',
            'view_count': 0,
            'like_count': 0,
            'download_date': datetime.now().isoformat(),
            'url': c['work_url'],
            'audio_file': cleaned_chapters[0]['audio_url'] if len(cleaned_chapters) == 1 else '',
            'processed': True,
            'summary': synopsis[:200] + '...' if len(synopsis) > 200 else synopsis,
            'thumbnail': cover_image,
            'tags': ['Liber Liber', 'Pubblico Dominio', 'Italiano'],
            'categories': [genre]
        }
        
        augmented_entry = {
            **main_entry,
            'source': 'liberliber',
            'source_url': c['work_url'],
            'embed_type': 'audio',
            'embed_url': c['work_url'],
            'audio_url': cleaned_chapters[0]['audio_url'],
            'audio_chapters': cleaned_chapters,
            'license': 'public_domain',
            'real_title': real_title,
            'real_author': real_author,
            'real_genre': genre,
            'real_synopsis': synopsis,
            'content_type': 'audiobook',
            'real_language': 'it',
            'real_narrator': narrator_str
        }
        
        if not dry_run:
            audiobooks[c['key']] = main_entry
            augmented[c['key']] = augmented_entry
            
            # Save progress periodically
            with open(audiobooks_path, 'w', encoding='utf-8') as f:
                json.dump(audiobooks, f, ensure_ascii=False, indent=2)
            with open(augmented_path, 'w', encoding='utf-8') as f:
                json.dump(augmented, f, ensure_ascii=False, indent=2)
                
        ingested_count += 1
        print(f"  ✅ Ingested successfully: {real_title} by {real_author}")
        
    print("\n" + "=" * 60)
    if dry_run:
        print(f"DRY-RUN COMPLETE. Evaluated and parsed {ingested_count} new books.")
    else:
        print(f"INGESTION COMPLETE. Added {ingested_count} new books to JSON databases.")
    print("=" * 60)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Liber Liber Audiobook Scraper')
    parser.add_argument('--limit', type=int, default=20, help='Maximum new books to ingest')
    parser.add_argument('--dry-run', action='store_true', help='Parse and print details without saving to DB')
    parser.add_argument('--verbose', action='store_true', help='Print detailed chapter information')
    args = parser.parse_args()
    
    scrape_liberliber(
        limit=args.limit,
        dry_run=args.dry_run,
        verbose=args.verbose
    )
