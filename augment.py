#!/usr/bin/env python3
import json
import os
import time
import argparse
import requests
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, SpinnerColumn, TimeElapsedColumn, TaskProgressColumn
from rich.panel import Panel
from rich.table import Table
import filelock

console = Console()

# Configuration
CONFIG = {
    'input_file': 'audiobooks.json',
    'output_file': 'augmented.json',
    'checkpoint_file': 'augment_checkpoint.json',
    'api_url': 'http://localhost:1234/v1/chat/completions',
    'batch_size': 10,  # Process this many items before saving checkpoint
    'rate_limit': 1.0,  # Time in seconds to wait between API calls
}

# Lock files to prevent concurrent access
INPUT_LOCK = filelock.FileLock(f"{CONFIG['input_file']}.lock", timeout=10)
OUTPUT_LOCK = filelock.FileLock(f"{CONFIG['output_file']}.lock", timeout=10)
CHECKPOINT_LOCK = filelock.FileLock(f"{CONFIG['checkpoint_file']}.lock", timeout=10)

def load_audiobooks():
    """Load the audiobooks metadata from the input file."""
    try:
        with INPUT_LOCK:
            try:
                with open(CONFIG['input_file'], 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError) as e:
                console.print(f"[bold red]Error:[/bold red] {str(e)}")
                return {}
    except filelock.Timeout:
        console.log("[bold yellow]Warning:[/bold yellow] Could not acquire input file lock. Using empty data.")
        return {}

def load_checkpoint():
    """Load the checkpoint file to resume processing."""
    try:
        with CHECKPOINT_LOCK:
            try:
                with open(CONFIG['checkpoint_file'], 'r') as f:
                    return json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                return {'processed_ids': []}
    except filelock.Timeout:
        console.log("[bold yellow]Warning:[/bold yellow] Could not acquire checkpoint file lock. Starting fresh.")
        return {'processed_ids': []}

def save_checkpoint(processed_ids):
    """Save checkpoint of processed IDs."""
    try:
        with CHECKPOINT_LOCK:
            checkpoint = {'processed_ids': processed_ids}
            with open(CONFIG['checkpoint_file'], 'w') as f:
                json.dump(checkpoint, f, indent=2)
    except filelock.Timeout:
        console.log("[bold yellow]Warning:[/bold yellow] Could not acquire checkpoint file lock. Checkpoint not saved.")

def save_augmented_data(audiobooks):
    """Save the augmented audiobooks to the output file."""
    try:
        with OUTPUT_LOCK:
            # Create a backup if the output file already exists
            if os.path.exists(CONFIG['output_file']):
                backup_file = f"{CONFIG['output_file']}.bak"
                try:
                    import shutil
                    shutil.copy2(CONFIG['output_file'], backup_file)
                except Exception as e:
                    console.log(f"[bold yellow]Warning:[/bold yellow] Failed to create backup: {e}")
            
            # Write the new metadata
            with open(CONFIG['output_file'], 'w', encoding='utf-8') as f:
                json.dump(audiobooks, f, indent=2, ensure_ascii=False)
    except filelock.Timeout:
        console.log("[bold red]Error:[/bold red] Could not acquire output file lock. Changes not saved.")

# Rate limiter class to match the one in audiobook_scraper.py
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

def get_augmented_info(book_id, book_data):
    """Query the local LLM to get augmented information about the book."""
    prompt = f"""
You are a literary expert. Please analyze this audiobook information and provide:
1. The real book title (without narrator info, just the book title)
2. The real author's name (just the author's name, standardized)
3. A brief synopsis of the work (2-3 sentences maximum)

Information:
- Title: {book_data['title']}
- Channel: {book_data['channel']}
- Description: {book_data['description']}
- Tags: {', '.join(book_data['tags'][:10])}
- Duration: {book_data['duration']} seconds

Format your response as a JSON object with these fields: 
{{"real_title": "Actual Book Title", "real_author": "Author Name", "real_synopsis": "Brief synopsis of the work."}}
Do not include any other text in your response.
"""

    headers = {
        "Content-Type": "application/json",
    }
    
    data = {
        "model": "qwen2.5-coder-3b-instruct-mlx",  # Using the model from the example
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that specializes in books and literature."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,  # Lower temperature for more consistent results
        "max_tokens": -1,
        "stream": False
    }
    
    # Apply rate limiting before making request
    rate_limiter.wait()
    
    try:
        response = requests.post(CONFIG['api_url'], headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        content = result['choices'][0]['message']['content']
        
        # Try to extract JSON from the response
        try:
            # Find JSON content in the response (in case there's surrounding text)
            import re
            json_match = re.search(r'({[\s\S]*})', content)
            if json_match:
                content = json_match.group(1)
            
            augmented_info = json.loads(content)
            # Ensure all expected keys are present
            required_keys = ["real_title", "real_author", "real_synopsis"]
            for key in required_keys:
                if key not in augmented_info:
                    augmented_info[key] = ""
            return augmented_info
        except json.JSONDecodeError:
            console.log(f"[bold yellow]Warning:[/bold yellow] Could not parse LLM response as JSON for {book_id}")
            return {
                "real_title": "",
                "real_author": "",
                "real_synopsis": "Failed to generate synopsis",
                "raw_response": content  # Save the raw response for debugging
            }
    except Exception as e:
        console.log(f"[bold red]Error:[/bold red] API request failed for {book_id}: {str(e)}")
        return {
            "real_title": "",
            "real_author": "",
            "real_synopsis": f"Error: {str(e)}",
        }

def display_stats(audiobooks):
    """Display statistics about augmented audiobooks"""
    if not audiobooks:
        console.print("[yellow]No audiobooks found in the metadata file.[/yellow]")
        return
        
    total_books = len(audiobooks)
    augmented_count = sum(1 for item in audiobooks.values() 
                        if item.get('real_title') and item.get('real_author') and item.get('real_synopsis'))
    
    # Create statistics table
    stats_table = Table(title="Audiobook Augmentation Statistics", box=None)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="magenta")
    
    stats_table.add_row("Total Audiobooks", str(total_books))
    stats_table.add_row("Augmented Books", f"{augmented_count} ({augmented_count/max(1, total_books):.1%})")
    stats_table.add_row("Remaining Books", str(total_books - augmented_count))
    
    # Create authors table
    authors = {}
    for book in audiobooks.values():
        if book.get('real_author'):
            author = book['real_author']
            authors[author] = authors.get(author, 0) + 1
    
    top_authors = sorted(authors.items(), key=lambda x: x[1], reverse=True)[:10]
    
    authors_table = Table(title="Top Authors", box=None)
    authors_table.add_column("Author", style="green")
    authors_table.add_column("Books", style="magenta", justify="right")
    
    for author, count in top_authors:
        authors_table.add_row(author, str(count))
    
    # Display the tables in a panel
    console.print(Panel(stats_table, title="Augmentation Progress"))
    if top_authors:
        console.print(Panel(authors_table, title="Author Distribution"))

def main():
    parser = argparse.ArgumentParser(description='Augment audiobook metadata with LLM-generated information')
    parser.add_argument('--input', default=CONFIG['input_file'], help=f'Path to input JSON file (default: {CONFIG["input_file"]})')
    parser.add_argument('--output', default=CONFIG['output_file'], help=f'Path to output JSON file (default: {CONFIG["output_file"]})')
    parser.add_argument('--resume', action='store_true', help='Resume from last checkpoint')
    parser.add_argument('--batch', type=int, default=CONFIG['batch_size'], help=f'Batch size for checkpointing (default: {CONFIG["batch_size"]})')
    parser.add_argument('--rate-limit', type=float, default=CONFIG['rate_limit'], help=f'Seconds between API calls (default: {CONFIG["rate_limit"]})')
    parser.add_argument('--stats', action='store_true', help='Display statistics about augmented audiobooks')
    
    args = parser.parse_args()
    
    # Update config from arguments
    CONFIG['input_file'] = args.input
    CONFIG['output_file'] = args.output
    CONFIG['batch_size'] = args.batch
    CONFIG['rate_limit'] = args.rate_limit
    
    # Update rate limiter
    rate_limiter = RateLimiter(CONFIG['rate_limit'])
    
    # Load audiobooks
    console.print(f"[bold]Loading audiobook data from[/bold] {CONFIG['input_file']}...")
    audiobooks = load_audiobooks()
    
    if not audiobooks:
        console.print("[bold red]Error:[/bold red] No audiobook data loaded. Exiting.")
        return
    
    total_books = len(audiobooks)
    console.print(f"[bold green]Loaded {total_books} audiobooks.[/bold green]")
    
    # Just show stats if requested
    if args.stats:
        display_stats(audiobooks)
        return
    
    # Load checkpoint if resuming
    processed_ids = []
    if args.resume:
        checkpoint = load_checkpoint()
        processed_ids = checkpoint['processed_ids']
        console.print(f"[bold]Resuming from checkpoint with {len(processed_ids)} already processed books.[/bold]")
    
    # Calculate remaining books
    remaining_ids = [book_id for book_id in audiobooks if book_id not in processed_ids]
    
    # Summary table before processing
    summary_table = Table(title="Processing Summary")
    summary_table.add_column("Category", style="cyan")
    summary_table.add_column("Count", style="magenta")
    
    summary_table.add_row("Total Books", str(total_books))
    summary_table.add_row("Already Processed", str(len(processed_ids)))
    summary_table.add_row("To Process", str(len(remaining_ids)))
    
    console.print(Panel(summary_table))
    
    # Process books
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("[cyan]Augmenting audiobooks...", total=len(remaining_ids))
        
        batch_count = 0
        for book_id in remaining_ids:
            # Process the book
            book_data = audiobooks[book_id]
            title = book_data['title'][:40] + "..." if len(book_data['title']) > 40 else book_data['title']
            progress.update(task, description=f"[cyan]Processing: {title}")
            
            # Get augmented information
            augmented_info = get_augmented_info(book_id, book_data)
            
            # Update the book data
            book_data.update(augmented_info)
            
            # Mark as processed
            processed_ids.append(book_id)
            batch_count += 1
            
            # Save checkpoint and data periodically
            if batch_count >= CONFIG['batch_size']:
                save_checkpoint(processed_ids)
                save_augmented_data(audiobooks)
                console.log(f"[bold green]Checkpoint saved after {batch_count} books.[/bold green]")
                batch_count = 0
            
            # Update progress
            progress.update(task, advance=1)
    
    # Final save
    save_checkpoint(processed_ids)
    save_augmented_data(audiobooks)
    
    # Display final stats
    console.print(f"[bold green]Augmentation complete! Processed {len(processed_ids)} audiobooks.[/bold green]")
    console.print(f"[bold]Augmented data saved to[/bold] {CONFIG['output_file']}")
    
    # Show final stats
    display_stats(audiobooks)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Interrupt received[/bold yellow]. Progress has been saved and can be resumed with --resume.")
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        console.print(traceback.format_exc())
        console.print("You can resume the process with --resume")
