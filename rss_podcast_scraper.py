#!/usr/bin/env python3
import json
import os
import re
import sys
import hashlib
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
from datetime import datetime
import email.utils

def clean_html(text):
    if not text:
        return ""
    # Strip HTML tags
    clean = re.compile('<.*?>')
    clean_text = re.sub(clean, '', text)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    return clean_text

def parse_duration(duration_str):
    if not duration_str:
        return 0.0
    duration_str = str(duration_str).strip()
    if ':' in duration_str:
        try:
            parts = list(map(float, duration_str.split(':')))
            seconds = 0.0
            for part in parts:
                seconds = seconds * 60 + part
            return seconds
        except ValueError:
            return 0.0
    else:
        try:
            return float(duration_str)
        except ValueError:
            return 0.0

def parse_pub_date(pub_date_str):
    if not pub_date_str:
        return "Unknown"
    try:
        dt = email.utils.parsedate_to_datetime(pub_date_str)
        return dt.strftime('%Y%m%d')
    except Exception:
        try:
            # Fallback parse
            dt = datetime.strptime(pub_date_str, "%Y-%m-%d")
            return dt.strftime('%Y%m%d')
        except Exception:
            return "Unknown"

def slugify(text: str) -> str:
    import unicodedata
    text = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return re.sub(r"-{2,}", "-", text) or "x"

def scrape_rss(feed_url, mode='single', title_override=None, author=None, genre=None, channel_name=None):
    print(f"📡 Fetching RSS Podcast Feed: {feed_url}...")
    try:
        r = requests.get(feed_url, timeout=30)
        r.raise_for_status()
        xml_content = r.content
    except Exception as e:
        print(f"❌ Failed to fetch RSS feed: {e}")
        sys.exit(1)
        
    try:
        root = ET.fromstring(xml_content)
    except Exception as e:
        print(f"❌ Failed to parse XML: {e}")
        sys.exit(1)
        
    channel = root.find('channel')
    if channel is None:
        print("❌ Invalid RSS feed structure (no <channel> found).")
        sys.exit(1)
        
    # Get feed title, description, image
    feed_title = title_override or channel.findtext('title')
    feed_desc = clean_html(channel.findtext('description'))
    
    namespaces = {
        'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd',
        'content': 'http://purl.org/rss/1.0/modules/content/'
    }
    
    feed_image = ""
    itunes_image = channel.find('itunes:image', namespaces)
    if itunes_image is not None:
        feed_image = itunes_image.attrib.get('href', '')
    if not feed_image:
        image_el = channel.find('image')
        if image_el is not None:
            feed_image = image_el.findtext('url')
            
    feed_author = author or channel.findtext('itunes:author', namespaces=namespaces) or "Autore Sconosciuto"
    feed_genre = genre or "romanzo"
    feed_channel = channel_name or channel.findtext('title')
    feed_channel_url = channel.findtext('link') or feed_url
    
    items = channel.findall('item')
    print(f"Found {len(items)} episodes/items in feed.")
    
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
        
    new_added = 0
    
    if mode == 'single':
        # Mode A: Feed represents a single audiobook, episodes are chapters.
        print(f"Ingesting entire feed as a single audiobook: '{feed_title}'")
        key = f"podcast_single_{slugify(feed_title)}"
        
        # Compile chapters
        chapters = []
        for item in items:
            title = item.findtext('title')
            desc = clean_html(item.findtext('description') or item.findtext('itunes:summary', default='', namespaces=namespaces))
            
            enclosure = item.find('enclosure')
            if enclosure is None or not enclosure.attrib.get('url'):
                continue
            audio_url = enclosure.attrib.get('url')
            
            dur_str = item.findtext('itunes:duration', namespaces=namespaces)
            dur = parse_duration(dur_str)
            
            pub_date = parse_pub_date(item.findtext('pubDate'))
            
            chapters.append({
                'title': title,
                'audio_url': audio_url,
                'duration': dur,
                'pub_date': pub_date,
                'description': desc
            })
            
        if not chapters:
            print("❌ No valid chapters found in feed (no <enclosure> tags).")
            sys.exit(1)
            
        # Sort chapters by pubDate (oldest first = chapter 1)
        # Some podcasts list chapters newest first, so sorting chronologically aligns chapter order.
        chapters = sorted(chapters, key=lambda x: x['pub_date'])
        
        # Build chapter array
        audio_chapters = []
        for idx, ch in enumerate(chapters):
            audio_chapters.append({
                'title': ch['title'],
                'audio_url': ch['audio_url'],
                'duration': ch['duration']
            })
            
        total_duration = sum(ch['duration'] for ch in audio_chapters)
        first_pub_date = chapters[0]['pub_date']
        
        # Check if already in DB
        if key in audiobooks:
            print(f"ℹ️ Audiobook '{feed_title}' already exists. Overwriting with latest chapters...")
            
        audiobooks[key] = {
            'title': feed_title,
            'channel': feed_channel,
            'channel_url': feed_channel_url,
            'duration': total_duration,
            'upload_date': first_pub_date,
            'description': feed_desc,
            'transcript': '',
            'view_count': 0,
            'like_count': 0,
            'download_date': datetime.now().isoformat(),
            'url': feed_channel_url,
            'audio_file': audio_chapters[0]['audio_url'] if len(audio_chapters) == 1 else '',
            'processed': True,
            'summary': feed_desc[:200] + '...' if len(feed_desc) > 200 else feed_desc,
            'thumbnail': feed_image,
            'tags': ['Podcast', 'Italiano'],
            'categories': [feed_genre]
        }
        
        augmented[key] = {
            **audiobooks[key],
            'source': 'podcast',
            'source_url': feed_url,
            'embed_type': 'audio',
            'embed_url': '',
            'audio_url': audio_chapters[0]['audio_url'],
            'audio_chapters': audio_chapters,
            'license': 'creative_commons',
            'real_title': feed_title,
            'real_author': feed_author,
            'real_genre': feed_genre,
            'real_synopsis': feed_desc,
            'content_type': 'audiobook',
            'real_language': 'it',
            'real_narrator': feed_author
        }
        new_added = 1
        print(f"✅ Ingested single audiobook '{feed_title}' with {len(audio_chapters)} chapters.")
        
    else:
        # Mode B: Each episode in feed is a separate book.
        print("Ingesting feed episodes as separate audiobooks...")
        for item in items:
            title = item.findtext('title')
            desc = clean_html(item.findtext('description') or item.findtext('itunes:summary', default='', namespaces=namespaces))
            
            enclosure = item.find('enclosure')
            if enclosure is None or not enclosure.attrib.get('url'):
                continue
            audio_url = enclosure.attrib.get('url')
            
            # Use md5 of audio_url for key to prevent collisions
            url_hash = hashlib.md5(audio_url.encode('utf-8')).hexdigest()[:10]
            key = f"podcast_item_{slugify(title)}_{url_hash}"
            
            if key in audiobooks:
                print(f"⏭️ Skipping existing episode: {title}")
                continue
                
            dur_str = item.findtext('itunes:duration', namespaces=namespaces)
            dur = parse_duration(dur_str)
            pub_date = parse_pub_date(item.findtext('pubDate'))
            
            ep_image = feed_image
            itunes_ep_image = item.find('itunes:image', namespaces)
            if itunes_ep_image is not None:
                ep_image = itunes_ep_image.attrib.get('href', ep_image)
                
            audiobooks[key] = {
                'title': title,
                'channel': feed_channel,
                'channel_url': feed_channel_url,
                'duration': dur,
                'upload_date': pub_date,
                'description': desc,
                'transcript': '',
                'view_count': 0,
                'like_count': 0,
                'download_date': datetime.now().isoformat(),
                'url': feed_channel_url,
                'audio_file': audio_url,
                'processed': True,
                'summary': desc[:200] + '...' if len(desc) > 200 else desc,
                'thumbnail': ep_image,
                'tags': ['Podcast', 'Italiano'],
                'categories': [feed_genre]
            }
            
            augmented[key] = {
                **audiobooks[key],
                'source': 'podcast',
                'source_url': feed_url,
                'embed_type': 'audio',
                'embed_url': '',
                'audio_url': audio_url,
                'audio_chapters': [],
                'license': 'creative_commons',
                'real_title': title,
                'real_author': feed_author,
                'real_genre': feed_genre,
                'real_synopsis': desc,
                'content_type': 'audiobook',
                'real_language': 'it',
                'real_narrator': feed_author
            }
            new_added += 1
            print(f"  ✅ Added episode: {title}")

    if new_added > 0:
        with open(audiobooks_path, 'w', encoding='utf-8') as f:
            json.dump(audiobooks, f, indent=2, ensure_ascii=False)
        with open(augmented_path, 'w', encoding='utf-8') as f:
            json.dump(augmented, f, indent=2, ensure_ascii=False)
        print("🎉 Database files updated successfully with podcast feed!")
    else:
        print("ℹ️ No new podcast episodes added.")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Ingest podcast RSS feed as audiobooks')
    parser.add_argument('url', help='RSS Feed URL')
    parser.add_argument('--mode', choices=['single', 'multiple'], default='single', help='Feed mode: "single" for one book with chapters, "multiple" for each episode as a book')
    parser.add_argument('--title', help='Override feed title')
    parser.add_argument('--author', help='Override author name')
    parser.add_argument('--genre', help='Override genre/category')
    parser.add_argument('--channel', help='Override publisher channel name')
    
    args = parser.parse_args()
    scrape_rss(args.url, args.mode, args.title, args.author, args.genre, args.channel)
