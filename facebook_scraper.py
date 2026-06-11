#!/usr/bin/env python3
import json
import re
import os
import subprocess
import argparse
from datetime import datetime
import time

def clean_html(text):
    if not text:
        return ""
    # Strip HTML tags
    clean = re.compile('<.*?>')
    clean_text = re.sub(clean, '', text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text

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

def extract_author(title, description):
    # Try to search for author patterns: "di Nome Cognome" or "scritto da Nome Cognome"
    content = f"{title} | {description}"
    
    # Try common patterns
    patterns = [
        r'(?i)(?:scritto\s+)?di\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'(?i)autore:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)',
        r'(?i)scrittore:\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
    ]
    
    for pat in patterns:
        m = re.search(pat, content)
        if m:
            author = m.group(1).strip()
            # Avoid matching reader/narrator name or common phrases
            if not any(x in author.lower() for x in ['lettura', 'leggo', 'audiolibro', 'capitolo', 'voce', 'canale']):
                return author
                
    return "Autore Sconosciuto"

def run_yt_dlp(url):
    """Run yt-dlp to get JSON metadata"""
    print(f"🎬 Querying Facebook metadata for: {url}...")
    try:
        cmd = ["yt-dlp", "--dump-json", "--skip-download", url]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
    except subprocess.CalledProcessError as e:
        print(f"  ❌ Failed to fetch metadata using yt-dlp: {e.stderr}")
        return None
    except Exception as e:
        print(f"  ❌ Error running yt-dlp: {e}")
        return None

def scrape_facebook(urls, min_duration=1200, ingest=False, overrides=None):
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
        
    added_count = 0
    overrides = overrides or {}
    
    for url in urls:
        url = url.strip()
        if not url:
            continue
            
        meta = run_yt_dlp(url)
        
        # Fallback logic if yt-dlp fails
        if not meta:
            print(f"  ⚠️  yt-dlp could not extract metadata automatically for {url}.")
            if overrides.get('title') and overrides.get('duration'):
                print("     -> Using manual overrides for metadata...")
                # Derive a dummy ID from URL if uploader/video ID is missing
                # Match watch/?v=XXXX or video ID numbers
                m_id = re.search(r'(?:v=|videos/|watch/live/\?v=)(\d+)', url)
                video_id = m_id.group(1) if m_id else str(int(time.time()))
                
                meta = {
                    'id': video_id,
                    'title': overrides.get('title'),
                    'duration': overrides.get('duration'),
                    'uploader': overrides.get('channel', 'Facebook Video'),
                    'uploader_id': '',
                    'description': overrides.get('description', 'Audiolibri pubblici condivisi.'),
                    'upload_date': datetime.now().strftime('%Y%m%d'),
                    'thumbnail': overrides.get('thumbnail', '')
                }
            else:
                print("  ❌ Skipping video. To ingest manually, pass --title, --duration (seconds), and optional --author, --description, --channel.")
                continue
            
        video_id = meta.get('id')
        title = meta.get('title', 'Unknown Facebook Audiobook')
        duration = float(meta.get('duration', 0))
        uploader = meta.get('uploader', 'Facebook User')
        uploader_id = meta.get('uploader_id', '')
        uploader_url = f"https://www.facebook.com/{uploader_id}" if uploader_id else "https://www.facebook.com"
        
        description = clean_html(meta.get('description', ''))
        upload_date = meta.get('upload_date', 'Unknown')
        thumbnail = meta.get('thumbnail', '')
        
        # Ingestion constraints
        if duration < min_duration:
            print(f"  ⚠️  Skipping {title}: duration {duration/60:.1f}m is less than {min_duration/60:.1f}m limit.")
            continue
            
        key = f"facebook_{video_id}"
        if key in audiobooks:
            print(f"  ℹ  Skipping {title}: already in database.")
            continue
            
        genre = overrides.get('genre') or guess_genre(title, description)
        author = overrides.get('author') or extract_author(title, description)
        
        # Standardize Facebook URL format
        standard_url = f"https://www.facebook.com/watch/?v={video_id}"
        
        # Facebook video embed plugin URL
        import urllib.parse
        escaped_fb_url = urllib.parse.quote(standard_url, safe='')
        embed_url = f"https://www.facebook.com/plugins/video.php?href={escaped_fb_url}&show_text=0"
        
        print(f"  ✅ Discovered candidate: {title}")
        print(f"     Duration: {duration/3600:.2f}h, Page: {uploader}, Genre: {genre}, Author: {author}")
        
        if ingest:
            audiobooks[key] = {
                'title': title,
                'channel': uploader,
                'channel_url': uploader_url,
                'duration': duration,
                'upload_date': upload_date,
                'description': description,
                'transcript': '',
                'view_count': 0,
                'like_count': 0,
                'download_date': datetime.now().isoformat(),
                'url': standard_url,
                'audio_file': '',
                'processed': True,
                'summary': description[:200] + '...' if len(description) > 200 else description,
                'thumbnail': thumbnail,
                'tags': ['Facebook', 'Audiolibro', 'Italiano'],
                'categories': [genre]
            }
            
            augmented[key] = {
                **audiobooks[key],
                'source': 'facebook',
                'source_url': standard_url,
                'embed_type': 'iframe',
                'embed_url': embed_url,
                'audio_url': '',
                'audio_chapters': [],
                'license': 'public_domain',
                'real_title': title,
                'real_author': author,
                'real_genre': genre,
                'real_synopsis': description,
                'content_type': 'audiobook',
                'real_language': 'it',
                'real_narrator': uploader
            }
            
            added_count += 1
            print(f"     🎉 Ingested: {key}")
            
    if ingest and added_count > 0:
        with open(audiobooks_path, 'w', encoding='utf-8') as f:
            json.dump(audiobooks, f, indent=2, ensure_ascii=False)
        with open(augmented_path, 'w', encoding='utf-8') as f:
            json.dump(augmented, f, indent=2, ensure_ascii=False)
        print(f"\n🎉 Successfully saved {added_count} Facebook audiobooks to database!")
    elif ingest:
        print("\nℹ No new Facebook audiobooks were added.")
    else:
        print("\nDRY RUN COMPLETE. Re-run with --ingest to save candidates.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Facebook Public Video Audiobook Ingestor')
    parser.add_argument('urls', nargs='*', help='Public Facebook video watch/share URLs')
    parser.add_argument('--file', help='Path to file containing Facebook URLs (one per line)')
    parser.add_argument('--min-duration', type=int, default=1200, help='Minimum duration in seconds (default: 1200 = 20m)')
    parser.add_argument('--ingest', action='store_true', help='Ingest candidates directly into databases')
    
    # Override/fallback parameters
    parser.add_argument('--title', help='Override or manual title fallback')
    parser.add_argument('--author', help='Override or manual author fallback')
    parser.add_argument('--genre', help='Override or manual genre fallback')
    parser.add_argument('--duration', type=float, help='Override or manual duration fallback (in seconds)')
    parser.add_argument('--description', help='Override or manual description fallback')
    parser.add_argument('--thumbnail', help='Override or manual thumbnail fallback')
    parser.add_argument('--channel', help='Override or manual channel/uploader name')
    
    args = parser.parse_args()
    
    url_list = args.urls if args.urls else []
    if args.file and os.path.exists(args.file):
        with open(args.file, 'r', encoding='utf-8') as f:
            url_list.extend([line.strip() for line in f if line.strip()])
            
    if not url_list:
        print("❌ Error: No Facebook URLs provided. Pass them as arguments or via --file.")
        exit(1)
        
    overrides = {
        'title': args.title,
        'author': args.author,
        'genre': args.genre,
        'duration': args.duration,
        'description': args.description,
        'thumbnail': args.thumbnail,
        'channel': args.channel
    }
        
    scrape_facebook(url_list, min_duration=args.min_duration, ingest=args.ingest, overrides=overrides)
