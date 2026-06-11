#!/usr/bin/env python3
import json
import re
import os
import time
import requests
from urllib.parse import urlparse
from datetime import datetime

def clean_html(text):
    if not text:
        return ""
    # Strip HTML tags using simple regex
    clean = re.compile('<.*?>')
    clean_text = re.sub(clean, '', text)
    # Replace multiple spaces/newlines
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text

def get_archive_identifier(archive_url):
    if not archive_url:
        return None
    # Extract identifier from archive.org/compress/IDENTIFIER or details/IDENTIFIER or download/IDENTIFIER
    parsed = urlparse(archive_url)
    path_parts = [p for p in parsed.path.split('/') if p]
    for seg in ['compress', 'details', 'download']:
        if seg in path_parts:
            idx = path_parts.index(seg)
            if idx + 1 < len(path_parts):
                return path_parts[idx + 1]
    # Fallback pattern matching
    m = re.search(r'archive\.org\/(?:compress|details|download)\/([a-zA-Z0-9_\-]+)', archive_url)
    return m.group(1) if m else None

def guess_genre(title, description):
    content = f"{title} {description}".lower()
    if 'poesia' in content or 'poesie' in content or 'versi' in content or 'canti' in content:
        return 'poesia'
    if 'racconto' in content or 'racconti' in content or 'novella' in content or 'novelle' in content:
        return 'racconto'
    if 'saggio' in content or 'filosofia' in content or 'trattato' in content:
        return 'saggio'
    if 'fiaba' in content or 'fiabe' in content or 'favola' in content or 'favole' in content:
        return 'fiaba'
    return 'romanzo' # Default fallback

def scrape_librivox(max_new_books=100):
    print("🚀 Starting LibriVox Italian Audiobooks Ingestion...")
    
    # Paths to the active database files
    audiobooks_path = 'audiobooks.json'
    augmented_path = 'augmented.json'
    
    if os.path.exists(audiobooks_path):
        with open(audiobooks_path, 'r', encoding='utf-8') as f:
            audiobooks = json.load(f)
    else:
        audiobooks = {}
        
    if os.path.exists(augmented_path):
        with open(augmented_path, 'r', encoding='utf-8') as f:
            augmented = json.load(f)
    else:
        augmented = {}
        
    # 1. Fetch all Italian books from LibriVox using pagination
    print("Step 1: Fetching all Italian audiobooks from LibriVox catalog API...")
    offset = 0
    limit = 1000
    italian_books = []
    
    while True:
        url = f"https://librivox.org/api/feed/audiobooks/?format=json&limit={limit}&offset={offset}"
        print(f"  Fetching batch at offset {offset}...")
        try:
            r = requests.get(url, timeout=30)
            if r.status_code == 404:
                print("  Reached catalog end (404).")
                break
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"  ❌ Error fetching offset {offset}: {e}")
            break
            
        books = data.get('books', [])
        if not books:
            if isinstance(data, dict) and 'books' in data:
                books = data['books']
            else:
                print("  No books in response. Ending pagination.")
                break
                
        if len(books) == 0:
            print("  Empty batch. Ending pagination.")
            break
            
        page_italian = [b for b in books if b.get('language') == 'Italian']
        print(f"    Found {len(page_italian)} Italian books in this batch.")
        italian_books.extend(page_italian)
        
        offset += limit
        time.sleep(1) # Be nice to the LibriVox API
        
    print(f"Total Italian audiobooks found in LibriVox catalog: {len(italian_books)}")
    
    # 2. Ingest books
    new_added = 0
    skipped_existing = 0
    
    for book in italian_books:
        librivox_id = book.get('id')
        title = book.get('title')
        archive_url = book.get('url_zip_file') or book.get('url_rss') or book.get('url_librivox')
        
        key = f"librivox_{librivox_id}"
        if key in audiobooks:
            skipped_existing += 1
            continue
            
        archive_id = get_archive_identifier(archive_url)
        if not archive_id:
            # Try to extract archive ID from other URLs or description as a fallback
            m = re.search(r'archive\.org\/details\/([a-zA-Z0-9_\-]+)', book.get('description', ''))
            if m:
                archive_id = m.group(1)
            else:
                print(f"⚠️  Could not extract Archive identifier for: {title}")
                continue
                
        print(f"🔍 [{new_added+1}/{max_new_books}] Querying Archive.org metadata for: {title} (ID: {archive_id})...")
        
        archive_meta_url = f"https://archive.org/metadata/{archive_id}"
        try:
            meta_resp = requests.get(archive_meta_url, timeout=20)
            meta_resp.raise_for_status()
            meta_data = meta_resp.json()
        except Exception as e:
            print(f"  ❌ Failed to fetch Archive metadata for {archive_id}: {e}")
            continue
            
        files = meta_data.get('files', [])
        chapters = []
        
        for f in files:
            name = f.get('name', '')
            if name.endswith('.mp3'):
                length_str = f.get('length', f.get('duration', '0'))
                try:
                    if ':' in str(length_str):
                        parts = list(map(float, str(length_str).split(':')))
                        dur = 0.0
                        for part in parts:
                            dur = dur * 60 + part
                    else:
                        dur = float(length_str)
                except ValueError:
                    dur = 0.0
                    
                chapter_title = f.get('title', name.replace('.mp3', '').replace('_', ' '))
                audio_url = f"https://archive.org/download/{archive_id}/{name}"
                
                chapters.append({
                    'title': clean_html(chapter_title),
                    'audio_url': audio_url,
                    'duration': dur
                })
                
        if not chapters:
            print(f"  ⚠️  No MP3 files found for Archive item {archive_id}")
            continue
            
        # Filter duplicates (e.g. 64kb vs 128kb versions)
        unique_chapters = {}
        for ch in chapters:
            url_path = ch['audio_url'].split('/')[-1]
            # Standardize base name
            base = re.sub(r'_(64kb|128kb|vbr)\.mp3$', '', url_path.lower())
            base = base.replace('.mp3', '')
            
            # Prefer 64kb version for smaller transfer size and faster loading
            if base not in unique_chapters:
                unique_chapters[base] = ch
            else:
                if '64kb' in ch['audio_url']:
                    unique_chapters[base] = ch
                    
        # Sort chapters by filename/URL so they play in reading order
        sorted_chapters = sorted(unique_chapters.values(), key=lambda x: x['audio_url'])
        total_duration = sum(ch['duration'] for ch in sorted_chapters)
        
        # Parse author name
        authors_list = book.get('authors', [])
        author_name = "Autore Sconosciuto"
        if authors_list:
            if isinstance(authors_list, list):
                author_name = ", ".join([f"{a.get('first_name', '')} {a.get('last_name', '')}".strip() for a in authors_list])
            elif isinstance(authors_list, dict):
                author_name = f"{authors_list.get('first_name', '')} {authors_list.get('last_name', '')}".strip()
                
        raw_description = clean_html(book.get('description', ''))
        genre = guess_genre(title, raw_description)
        
        # Build entries
        audiobooks[key] = {
            'title': title,
            'channel': 'LibriVox',
            'channel_url': 'https://librivox.org',
            'duration': total_duration,
            'upload_date': book.get('release_date', '').replace('-', '') or 'Unknown',
            'description': raw_description,
            'transcript': '',
            'view_count': 0,
            'like_count': 0,
            'download_date': datetime.now().isoformat(),
            'url': book.get('url_librivox', ''),
            'audio_file': sorted_chapters[0]['audio_url'] if len(sorted_chapters) == 1 else '',
            'processed': True,
            'summary': raw_description[:200] + '...' if len(raw_description) > 200 else raw_description,
            'thumbnail': '',
            'tags': ['LibriVox', 'Pubblico Dominio', 'Italiano'],
            'categories': [genre]
        }
        
        augmented[key] = {
            **audiobooks[key],
            'source': 'librivox',
            'source_url': book.get('url_librivox', ''),
            'embed_type': 'audio',
            'embed_url': f"https://archive.org/embed/{archive_id}",
            'audio_url': sorted_chapters[0]['audio_url'],
            'audio_chapters': sorted_chapters,
            'license': 'public_domain',
            'real_title': title,
            'real_author': author_name,
            'real_genre': genre,
            'real_synopsis': raw_description,
            'content_type': 'audiobook',
            'real_language': 'it',
            'real_narrator': 'LibriVox lettori'
        }
        
        new_added += 1
        print(f"  ✅ Added: {title} by {author_name} ({len(sorted_chapters)} chapters, {total_duration/3600:.1f}h)")
        
        if new_added >= max_new_books:
            print(f"Reached ingestion limit of {max_new_books} new books.")
            break
            
        time.sleep(0.5) # Be nice to Archive.org API
        
    print(f"\nIngestion summary:")
    print(f"  Already in database: {skipped_existing}")
    print(f"  New books added: {new_added}")
    
    # Save files if changes were made
    if new_added > 0:
        with open(audiobooks_path, 'w', encoding='utf-8') as f:
            json.dump(audiobooks, f, indent=2, ensure_ascii=False)
        with open(augmented_path, 'w', encoding='utf-8') as f:
            json.dump(augmented, f, indent=2, ensure_ascii=False)
        print("🎉 Database files updated successfully!")
    else:
        print("ℹ️  No database updates needed.")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=100, help='Maximum new books to ingest')
    args = parser.parse_args()
    
    scrape_librivox(args.limit)
