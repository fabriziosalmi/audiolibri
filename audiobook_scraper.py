import sys
import json
import os
import time
import subprocess
import re
from pathlib import Path
from datetime import datetime
from pytube import YouTube, Playlist, Channel
import ffmpeg
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TimeElapsedColumn, TaskProgressColumn
from rich.panel import Panel
from rich.table import Table
import yt_dlp
import concurrent.futures
import random
import filelock  # Add this import
from urllib.parse import urlparse, parse_qs

try:
    import ffmpeg
    import yt_dlp
    import filelock
except ImportError as e:
    print(f"Error: Missing required dependency - {e}")
    print("Please install required packages: pip install ffmpeg-python yt-dlp filelock")
    sys.exit(1)

console = Console()

# Configuration settings
CONFIG = {
    'output_dir': os.environ.get('AUDIOBOOKS_OUTPUT_DIR', 'audiobooks'),
    'metadata_file': 'audiobooks.json',
    'audio_format': 'mp3',
    'bitrate': '64k',
    'checkpoint_file': 'checkpoint.json',
    'max_retries': 3,
    'recursive_depth': 2,  # How deep to go when traversing channels/playlists
    'max_workers': int(os.environ.get('MAX_WORKERS', '4')),      # Number of parallel workers for downloading
    'min_duration': 0,     # Minimum duration in seconds (0 = no filter)
    'max_duration': 0,     # Maximum duration in seconds (0 = no filter)
    'rate_limit': float(os.environ.get('RATE_LIMIT', '1')),       # Minimum seconds between requests
    'extract_description': True,  # Extract transcript from video description
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# Rate limiter class
class RateLimiter:
    def __init__(self, rate_limit):
        self.rate_limit = rate_limit
        self.last_request = 0
        
    def wait(self):
        if self.rate_limit <= 0:
            return
            
        now = time.time()
        elapsed = now - self.last_request
        if elapsed < self.rate_limit:
            time.sleep(self.rate_limit - elapsed)
        self.last_request = time.time()

rate_limiter = RateLimiter(CONFIG['rate_limit'])

def extract_audio_metadata(audio_file):
    """Extract metadata from audio file using ffprobe"""
    try:
        probe = ffmpeg.probe(audio_file)
        audio_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'audio'), None)
        if audio_stream:
            return {
                'codec': audio_stream.get('codec_name', 'unknown'),
                'channels': audio_stream.get('channels', 0),
                'sample_rate': audio_stream.get('sample_rate', 'unknown'),
                'bit_rate': audio_stream.get('bit_rate', 'unknown'),
                'duration': probe.get('format', {}).get('duration', 0)
            }
        return {}
    except Exception as e:
        console.log(f"[bold yellow]Warning:[/bold yellow] Could not extract audio metadata: {str(e)}")
        return {}

def validate_youtube_url(url):
    """Validate if the URL is a valid YouTube URL"""
    youtube_regex = r'^(https?://)?(www\.)?(youtube\.com|youtu\.?be)/.+$'
    if not re.match(youtube_regex, url):
        return False
    return True

# Add a file lock for metadata operations
METADATA_LOCK = filelock.FileLock(f"{CONFIG['metadata_file']}.lock", timeout=30)

def load_existing_metadata():
    try:
        with METADATA_LOCK:
            try:
                with open(CONFIG['metadata_file'], 'r') as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                return {}
    except filelock.Timeout:
        console.log("[bold yellow]Warning:[/bold yellow] Could not acquire metadata file lock. Using empty metadata.")
        return {}

def save_metadata(metadata):
    try:
        with METADATA_LOCK:
            # Create a backup first
            if os.path.exists(CONFIG['metadata_file']):
                backup_file = f"{CONFIG['metadata_file']}.bak"
                try:
                    import shutil
                    shutil.copy2(CONFIG['metadata_file'], backup_file)
                except Exception as e:
                    console.log(f"[bold yellow]Warning:[/bold yellow] Failed to create metadata backup: {e}")
                    
            # Write the new metadata
            with open(CONFIG['metadata_file'], 'w') as f:
                json.dump(metadata, f, indent=2)
    except filelock.Timeout:
        console.log("[bold red]Error:[/bold red] Could not acquire metadata file lock for writing. Changes may be lost.")
        
# Add a file lock for checkpoint operations
CHECKPOINT_LOCK = filelock.FileLock(f"{CONFIG['checkpoint_file']}.lock", timeout=30)

def load_checkpoint():
    try:
        with CHECKPOINT_LOCK:
            try:
                with open(CONFIG['checkpoint_file'], 'r') as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                return {'last_url': None, 'processed_urls': []}
    except filelock.Timeout:
        console.log("[bold yellow]Warning:[/bold yellow] Could not acquire checkpoint file lock. Using empty checkpoint.")
        return {'last_url': None, 'processed_urls': []}

def save_checkpoint(url):
    try:
        with CHECKPOINT_LOCK:
            checkpoint = load_checkpoint()
            checkpoint['last_url'] = url
            if url not in checkpoint['processed_urls']:
                checkpoint['processed_urls'].append(url)
            with open(CONFIG['checkpoint_file'], 'w') as f:
                json.dump(checkpoint, f, indent=2)
    except filelock.Timeout:
        console.log("[bold red]Error:[/bold red] Could not acquire checkpoint file lock for writing. Changes may be lost.")
        
def extract_transcript_from_description(description):
    """Extract transcript-like content from video description"""
    if not description:
        return ""
    
    # Look for patterns that might indicate transcript sections
    transcript = ""
    
    # Common patterns in timestamps: HH:MM:SS, MM:SS, or MM.SS format
    timestamp_pattern = r'(\d{1,2}:)?\d{1,2}:\d{2}|\d{1,2}:\d{2}|\d{1,2}\.\d{2}'
    
    # Split by lines and look for timestamp patterns
    lines = description.split('\n')
    for line in lines:
        if re.search(timestamp_pattern, line):
            transcript += line + "\n"
    
    # If no timestamps found, check for paragraph-like content
    if not transcript:
        # Heuristic: paragraphs longer than 100 chars might be transcript parts
        for line in lines:
            if len(line.strip()) > 100:
                transcript += line + "\n\n"
    
    return transcript

def extract_metadata(youtube_url, progress):
    # Create a task for this metadata extraction
    task_id = progress.add_task(f"[cyan]Extracting metadata...", total=100)
    
    # Validate YouTube URL
    if not validate_youtube_url(youtube_url):
        progress.update(task_id, description=f"[red]Invalid YouTube URL: {youtube_url[:40]}...", completed=100)
        console.log(f"[bold red]Error:[/bold red] Invalid YouTube URL: {youtube_url}")
        return False
    
    try:
        # Use yt-dlp to download comprehensive video metadata
        progress.update(task_id, description=f"[cyan]Fetching metadata with yt-dlp...", completed=30)
        
        ydl_opts = {
            'format': 'bestaudio',
            'quiet': True,
            'extract_flat': False,  # Extract full info
            'skip_download': True,  # Don't download the video
            'no_warnings': True,
            'user_agent': CONFIG['user_agent'],
            'socket_timeout': 30,
        }
        
        # Apply rate limiting
        rate_limiter.wait()
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(youtube_url, download=False)
            
        # Apply duration filtering if configured
        if CONFIG['min_duration'] > 0 and float(info_dict.get('duration', 0)) < CONFIG['min_duration']:
            progress.update(task_id, description=f"[yellow]Skipped: Duration too short", completed=100)
            console.log(f"Skipping {info_dict.get('id')} - duration too short")
            return True
            
        if CONFIG['max_duration'] > 0 and float(info_dict.get('duration', 0)) > CONFIG['max_duration']:
            progress.update(task_id, description=f"[yellow]Skipped: Duration too long", completed=100)
            console.log(f"Skipping {info_dict.get('id')} - duration too long")
            return True
            
        # Extract video ID for consistent identification
        video_id = info_dict.get('id', youtube_url.split('v=')[-1])
        existing_metadata = load_existing_metadata()

        if video_id in existing_metadata:
            progress.update(task_id, description=f"[yellow]Skipped: {video_id[:40]}...", completed=100)
            console.log(f"Skipping {video_id} - already exists")
            return True
            
        # Extract transcript from description if enabled
        transcript = ""
        if CONFIG['extract_description']:
            transcript = extract_transcript_from_description(info_dict.get('description', ''))
            
        # Save comprehensive metadata
        progress.update(task_id, description=f"[cyan]Saving metadata: {info_dict.get('title', video_id)[:40]}...", completed=90)
        
        # Create a comprehensive metadata entry
        existing_metadata[video_id] = {
            'title': info_dict.get('title', 'Unknown'),
            'channel': info_dict.get('channel', info_dict.get('uploader', 'Unknown')),
            'channel_url': info_dict.get('channel_url', info_dict.get('uploader_url', '')),
            'duration': float(info_dict.get('duration', 0)),
            'upload_date': info_dict.get('upload_date', 'Unknown'),
            'description': info_dict.get('description', ''),
            'transcript': transcript,
            'view_count': info_dict.get('view_count', 0),
            'like_count': info_dict.get('like_count', 0),
            'download_date': datetime.now().isoformat(),
            'url': youtube_url,
            'audio_file': '',
            'processed': False,
            'summary': '',
            'thumbnail': info_dict.get('thumbnail', ''),
            'tags': info_dict.get('tags', []),
            'categories': info_dict.get('categories', [])
        }

        save_metadata(existing_metadata)
        save_checkpoint(youtube_url)
        
        progress.update(task_id, description=f"[green]Completed: {info_dict.get('title', video_id)[:40]}...", completed=100)
        console.log(f"Successfully extracted metadata for {video_id}: {info_dict.get('title', 'Unknown')}")
        return True
        
    except Exception as e:
        progress.update(task_id, description=f"[red]Error: {str(e)[:40]}...", completed=100)
        console.log(f"[bold red]Error:[/bold red] {str(e)}")
        console.log(f"[bold red]URL causing error:[/bold red] {youtube_url}")
        return False

def download_audio(youtube_url, progress):
    # Create a task for this download
    task_id = progress.add_task(f"[cyan]Downloading...", total=100)
    
    # Validate YouTube URL
    if not validate_youtube_url(youtube_url):
        progress.update(task_id, description=f"[red]Invalid YouTube URL: {youtube_url[:40]}...", completed=100)
        console.log(f"[bold red]Error:[/bold red] Invalid YouTube URL: {youtube_url}")
        return False
    
    # Implement retry logic with exponential backoff
    retry_count = 0
    max_retries = CONFIG['max_retries']
    base_wait_time = 2  # seconds
    
    while retry_count <= max_retries:
        try:
            # If this is a retry, update the progress bar
            if retry_count > 0:
                progress.update(task_id, description=f"[yellow]Retry {retry_count}/{max_retries}...", completed=5)
                console.log(f"Retry attempt {retry_count}/{max_retries} for {youtube_url}")
            
            # Apply rate limiting
            rate_limiter.wait()
            
            # Use a timeout for the YouTube API request
            yt = YouTube(youtube_url, use_oauth=False, allow_oauth_cache=False)
            progress.update(task_id, description=f"[cyan]Analyzing: {yt.title[:40]}...", completed=10)
            
            video_id = yt.video_id
            existing_metadata = load_existing_metadata()  # Changed variable name for clarity

            if video_id in existing_metadata:
                progress.update(task_id, description=f"[yellow]Skipped: {yt.title[:40]}...", completed=100)
                console.log(f"Skipping {video_id} - already exists")
                return True

            # Get the best audio stream
            progress.update(task_id, description=f"[cyan]Finding best audio: {yt.title[:40]}...", completed=20)
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            if not audio_stream:
                progress.update(task_id, description=f"[red]No audio stream: {yt.title[:40]}", completed=100)
                console.log(f"[bold red]Error:[/bold red] No audio stream found for {video_id}")
                return False
                
            output_path = Path(CONFIG['output_dir'])
            output_path.mkdir(exist_ok=True)

            # Download audio
            progress.update(task_id, description=f"[cyan]Downloading: {yt.title[:40]}...", completed=30)
            audio_file = audio_stream.download(output_path=output_path)
            progress.update(task_id, description=f"[cyan]Converting: {yt.title[:40]}...", completed=70)
            
            output_file = output_path / f'{video_id}.{CONFIG["audio_format"]}'
            
            # Convert to desired format
            (
                ffmpeg
                .input(audio_file)
                .output(str(output_file), ac=1, audio_bitrate=CONFIG['bitrate'])
                .run(overwrite_output=True, quiet=True)
            )
            
            # Remove the original file after conversion
            if os.path.exists(audio_file) and os.path.exists(output_file):
                os.remove(audio_file)

            # Extract audio metadata using ffmpeg
            progress.update(task_id, description=f"[cyan]Extracting audio metadata: {yt.title[:40]}...", completed=85)
            audio_metadata = extract_audio_metadata(str(output_file))
            
            # Save metadata
            progress.update(task_id, description=f"[cyan]Saving metadata: {yt.title[:40]}...", completed=90)
            
            # Load the latest metadata to avoid overwriting other entries
            existing_metadata = load_existing_metadata()
            
            # Update the specific video entry in the existing metadata
            existing_metadata[video_id] = {
                'title': yt.title or 'Unknown',
                'channel': yt.author or 'Unknown',
                'channel_url': yt.channel_url or '',
                'duration': yt.length or 0,
                'upload_date': str(yt.publish_date) if yt.publish_date else 'Unknown',
                'download_date': datetime.now().isoformat(),
                'url': youtube_url,
                'audio_file': str(output_file),
                'audio_metadata': audio_metadata or {},
                'processed': False,
                'summary': '',
                'transcript': extract_transcript_from_description(yt.description or '') if CONFIG['extract_description'] else ''
            }

            save_metadata(existing_metadata)
            save_checkpoint(youtube_url)
            
            progress.update(task_id, description=f"[green]Completed: {yt.title[:40]}...", completed=100)
            console.log(f"Successfully downloaded {video_id}: {yt.title}")
            return True
            
        except Exception as e:
            progress.update(task_id, description=f"[red]Error: {str(e)[:40]}...", completed=100)
            console.log(f"[bold red]Error:[/bold red] {str(e)}")
            console.log(f"[bold red]URL causing error:[/bold red] {youtube_url}")
            
            # Check for various network-related errors
            retry_errors = [
                "HTTP Error",
                "Connection",
                "Timeout",
                "Network",
                "socket",
                "SSL",
                "ConnectionError",
                "ConnectionResetError",
                "ReadTimeout"
            ]
            
            should_retry = any(err in str(e) for err in retry_errors)
            
            if should_retry:
                retry_count += 1
                if retry_count <= max_retries:
                    # Exponential backoff
                    wait_time = base_wait_time * (2 ** (retry_count - 1))
                    console.log(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
            
            return False
    
    # If we've exhausted all retries
    return False

def parse_youtube_url(url):
    """Parse and normalize YouTube URL to extract ID and type"""
    parsed_url = urlparse(url)
    
    if 'youtu.be' in parsed_url.netloc:
        # Short URL format
        video_id = parsed_url.path.strip('/')
        return {'type': 'video', 'id': video_id}
        
    if 'youtube.com' in parsed_url.netloc:
        # Channel URLs
        if '/channel/' in parsed_url.path:
            channel_id = parsed_url.path.split('/channel/')[-1].split('/')[0]
            return {'type': 'channel', 'id': channel_id}
        
        if '/c/' in parsed_url.path or '/@' in parsed_url.path:
            channel_name = parsed_url.path.split('/c/')[-1].split('/')[0] if '/c/' in parsed_url.path else parsed_url.path.split('/@')[-1].split('/')[0]
            return {'type': 'channel_name', 'id': channel_name}
            
        # Playlist URL
        if '/playlist' in parsed_url.path:
            query = parse_qs(parsed_url.query)
            playlist_id = query.get('list', [None])[0]
            if playlist_id:
                return {'type': 'playlist', 'id': playlist_id}
                
        # Video URL
        if '/watch' in parsed_url.path:
            query = parse_qs(parsed_url.query)
            video_id = query.get('v', [None])[0]
            if video_id:
                return {'type': 'video', 'id': video_id}
    
    # Default return if we can't identify the URL type
    return {'type': 'unknown', 'id': None}

def get_urls_from_channel(channel_url, depth=0):
    """Extract all video URLs from a channel"""
    if depth > CONFIG['recursive_depth']:
        return []
    
    urls = []
    try:
        # Apply rate limiting
        rate_limiter.wait()
        
        channel = Channel(channel_url)
        console.log(f"Processing channel: {channel.channel_name}")
        
        # Use yt-dlp for better channel scraping
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'skip_download': True,
            'no_warnings': True,
            'user_agent': CONFIG['user_agent']
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                channel_info = ydl.extract_info(channel_url, download=False)
                if 'entries' in channel_info:
                    for entry in channel_info['entries']:
                        if entry.get('url'):
                            video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                            urls.append(video_url)
        except Exception as ydl_err:
            console.log(f"[yellow]yt-dlp error, falling back to pytube: {str(ydl_err)}")
            # Fallback to pytube
            urls = list(channel.video_urls)
            
        return urls
    except Exception as e:
        console.log(f"[bold red]Error processing channel:[/bold red] {str(e)}")
        return []

def get_urls_from_playlist(playlist_url, depth=0):
    """Extract all video URLs from a playlist"""
    if depth > CONFIG['recursive_depth']:
        return []
    
    urls = []
    try:
        # Apply rate limiting
        rate_limiter.wait()
        
        # Try yt-dlp first for better playlist extraction
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'skip_download': True,
            'no_warnings': True,
            'user_agent': CONFIG['user_agent']
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                playlist_info = ydl.extract_info(playlist_url, download=False)
                console.log(f"Processing playlist: {playlist_info.get('title', 'Unknown')}")
                
                if 'entries' in playlist_info:
                    for entry in playlist_info['entries']:
                        if entry and entry.get('id'):
                            video_url = f"https://www.youtube.com/watch?v={entry['id']}"
                            urls.append(video_url)
        except Exception as ydl_err:
            console.log(f"[yellow]yt-dlp error, falling back to pytube: {str(ydl_err)}")
            # Fallback to pytube
            playlist = Playlist(playlist_url)
            console.log(f"Processing playlist: {playlist.title}")
            urls = list(playlist.video_urls)
            
        return urls
    except Exception as e:
        console.log(f"[bold red]Error processing playlist:[/bold red] {str(e)}")
        return []

def discover_urls(url, depth=0):
    """Recursively discover URLs from channels, playlists, and videos"""
    discovered = set()
    
    # Parse the URL to identify its type
    parsed = parse_youtube_url(url)
    
    # Base case for recursion
    if depth > CONFIG['recursive_depth']:
        return discovered
    
    # Handle different URL types based on parsed info
    if parsed['type'] == 'channel' or parsed['type'] == 'channel_name':
        # Channel URL
        videos = get_urls_from_channel(url, depth)
        discovered.update(videos)
        
        # If recursive, also process playlists in the channel
        if depth < CONFIG['recursive_depth']:
            try:
                channel = Channel(url)
                for playlist_url in channel.playlist_urls:
                    # Add a small random delay to avoid rate limiting
                    time.sleep(random.uniform(0.5, 1.5))
                    discovered.update(discover_urls(playlist_url, depth + 1))
            except Exception as e:
                console.log(f"[yellow]Error discovering channel playlists: {str(e)}")
                
    elif parsed['type'] == 'playlist':
        # Playlist URL
        videos = get_urls_from_playlist(url, depth)
        discovered.update(videos)
    elif parsed['type'] == 'video':
        # Single video URL
        discovered.add(url)
    else:
        # Try to handle as a regular URL
        if 'youtube.com/channel/' in url or 'youtube.com/c/' in url or 'youtube.com/@' in url:
            videos = get_urls_from_channel(url, depth)
            discovered.update(videos)
        elif 'playlist?list=' in url:
            videos = get_urls_from_playlist(url, depth)
            discovered.update(videos)
        else:
            discovered.add(url)
        
    return discovered

def process_urls(urls, progress):
    """Process multiple URLs in parallel with managed progress displays"""
    # Add a task for overall progress
    overall_task = progress.add_task("[bold blue]Overall Progress", total=len(urls))
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=CONFIG['max_workers']) as executor:
        futures = []
        for url in urls:
            # Submit the task
            future = executor.submit(extract_metadata, url, progress)
            future.url = url  # Store URL with the future for reference
            futures.append(future)
        
        # Process completed futures as they come in
        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            url = future.url
            try:
                success = future.result()
                if success:
                    save_checkpoint(url)
            except Exception as e:
                console.log(f"[bold red]Error processing {url}: {str(e)}")
            finally:
                # Update overall progress
                progress.update(overall_task, advance=1)

def process_url(url):
    # Load checkpoint data
    checkpoint = load_checkpoint()
    resume_from = checkpoint.get('last_url')
    processed_urls = set(checkpoint.get('processed_urls', []))
    
    # Create a rich progress display
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    ) as progress:
        # Display resume information if applicable
        if resume_from:
            console.log(f"[bold green]Resuming from checkpoint:[/bold green] {resume_from}")

        # Discover all URLs to process
        discovery_task = progress.add_task("[yellow]Discovering content...", total=100)
        all_urls = discover_urls(url)
        progress.update(discovery_task, completed=100, description="[green]Discovery complete")
        
        # Create a summary table
        table = Table(title="Content Summary")
        table.add_column("Type", style="cyan")
        table.add_column("Count", style="magenta")
        table.add_row("Videos to download", str(len(all_urls)))
        table.add_row("Already processed", str(len(processed_urls & all_urls)))
        table.add_row("New to process", str(len(all_urls - processed_urls)))
        console.print(Panel(table))
        
        # Filter URLs - remove already processed and get ones to process
        urls_to_process = [u for u in all_urls if u not in processed_urls or u == resume_from]
        
        # Reset resume point after finding it
        if resume_from in urls_to_process:
            resume_index = urls_to_process.index(resume_from)
            urls_to_process = urls_to_process[resume_index:]
        
        # Process all discovered URLs in parallel if there's more than one
        if urls_to_process:
            if len(urls_to_process) > 1 and CONFIG['max_workers'] > 1:
                process_urls(urls_to_process, progress)
            else:
                # Process sequentially for single URLs or if parallel disabled
                for video_url in urls_to_process:
                    success = extract_metadata(video_url, progress)
                    if success:
                        save_checkpoint(video_url)
        else:
            console.print("[yellow]No new content to process[/yellow]")

def display_stats():
    """Display statistics about downloaded audiobooks"""
    metadata = load_existing_metadata()
    
    if not metadata:
        console.print("[yellow]No audiobooks have been downloaded yet.[/yellow]")
        return
        
    total_duration = sum(float(item.get('duration', 0)) for item in metadata.values())
    hours = total_duration // 3600
    minutes = (total_duration % 3600) // 60
    
    table = Table(title="Audiobook Library Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")
    
    table.add_row("Total Audiobooks", str(len(metadata)))
    table.add_row("Total Duration", f"{hours} hours, {minutes} minutes")
    table.add_row("Channels", str(len(set(item.get('channel', '') for item in metadata.values()))))
    
    console.print(Panel(table))

if __name__ == '__main__':
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='YouTube Audiobook Scraper')
    parser.add_argument('url', nargs='?', help='YouTube URL (video, playlist, or channel)')
    parser.add_argument('--stats', action='store_true', help='Display statistics about downloaded audiobooks')
    parser.add_argument('--resume', action='store_true', help='Resume from last checkpoint')
    parser.add_argument('--depth', type=int, default=CONFIG['recursive_depth'], 
                      help=f'Maximum depth for recursive scraping (default: {CONFIG["recursive_depth"]})')
    parser.add_argument('--workers', type=int, default=CONFIG['max_workers'],
                      help=f'Number of parallel download workers (default: {CONFIG["max_workers"]})')
    parser.add_argument('--min-duration', type=int, default=CONFIG['min_duration'],
                      help=f'Minimum video duration in seconds (default: {CONFIG["min_duration"]} - no limit)')
    parser.add_argument('--max-duration', type=int, default=CONFIG['max_duration'],
                      help=f'Maximum video duration in seconds (default: {CONFIG["max_duration"]} - no limit)')
    parser.add_argument('--rate-limit', type=float, default=CONFIG['rate_limit'],
                      help=f'Rate limit in seconds between requests (default: {CONFIG["rate_limit"]})')
    parser.add_argument('--no-transcript', action='store_true', 
                      help='Disable transcript extraction from descriptions')
    
    args = parser.parse_args()
    
    # Update configuration based on command line arguments
    if args.depth is not None:
        CONFIG['recursive_depth'] = args.depth
    if args.workers is not None:
        CONFIG['max_workers'] = args.workers
    if args.min_duration is not None:
        CONFIG['min_duration'] = args.min_duration
    if args.max_duration is not None:
        CONFIG['max_duration'] = args.max_duration
    if args.rate_limit is not None:
        CONFIG['rate_limit'] = args.rate_limit
        rate_limiter = RateLimiter(CONFIG['rate_limit'])
    if args.no_transcript:
        CONFIG['extract_description'] = False
        
    if args.stats:
        display_stats()
        sys.exit(0)
        
    if args.resume:
        checkpoint = load_checkpoint()
        last_url = checkpoint.get('last_url')
        if last_url:
            console.print(f"[bold green]Resuming from last URL:[/bold green] {last_url}")
            try:
                process_url(last_url)
                sys.exit(0)
            except KeyboardInterrupt:
                console.print("\n[bold yellow]Interrupt received[/bold yellow]. Progress has been saved.")
                sys.exit(0)
        else:
            console.print("[bold yellow]No checkpoint found to resume from.[/bold yellow]")
            sys.exit(1)
    
    if not args.url:
        console.print("[bold red]Error:[/bold red] Please provide a YouTube URL (video, playlist, or channel)")
        console.print("Run with --help for more information")
        sys.exit(1)
    
    try:
        process_url(args.url)
        console.print("\n[bold green]All downloads completed successfully![/bold green]")
        display_stats()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Interrupt received[/bold yellow]. Progress has been saved and can be resumed with --resume.")
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        console.print("You can resume the download with --resume")