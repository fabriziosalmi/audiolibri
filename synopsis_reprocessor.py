#!/usr/bin/env python3
"""
Synopsis Reprocessor for Audiobook Collection

This script reprocesses all synopses using a local LLM to improve their quality.
It preserves the original title and author information and only updates the synopsis.
"""

import json
import shutil
import requests
import time
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table

console = Console()

# Configuration
CONFIG = {
    'api_url': 'http://localhost:1234/v1/chat/completions',
    'model': 'qwen3-8b-mlx',  # Using the model from your example
    'rate_limit': 1.0,  # Seconds between requests
    'batch_size': 5,  # Number of books to process before saving checkpoint
}

class RateLimiter:
    def __init__(self, delay):
        self.delay = delay
        self.last_request = 0
    
    def wait(self):
        now = time.time()
        elapsed = now - self.last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)
        self.last_request = time.time()

def is_italian_text(text):
    """Simple heuristic to check if text appears to be in Italian"""
    italian_indicators = ['il', 'la', 'lo', 'gli', 'le', 'di', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra', 'a', 'e', 'che', 'del', 'della', 'dello', 'dei', 'delle', 'degli', 'nel', 'nella', 'nello', 'nei', 'nelle', 'negli', 'al', 'alla', 'allo', 'ai', 'alle', 'agli', 'dal', 'dalla', 'dallo', 'dai', 'dalle', 'dagli', 'sul', 'sulla', 'sullo', 'sui', 'sulle', 'sugli', 'un', 'una', 'uno']
    
    # Convert to lowercase and split into words
    words = text.lower().split()
    if not words:
        return False
    
    # Count Italian indicators
    italian_word_count = sum(1 for word in words if any(indicator in word for indicator in italian_indicators))
    
    # Should have at least 20% Italian indicators
    return italian_word_count / len(words) >= 0.2

def get_improved_synopsis(book_id, book_data, rate_limiter):
    """Query the local LLM to get an improved synopsis for the book."""
    
    # Extract current information
    real_title = book_data.get('real_title', book_data.get('title', ''))
    real_author = book_data.get('real_author', '')
    current_synopsis = book_data.get('real_synopsis', '')
    
    # Create a focused prompt for synopsis improvement
    prompt = f"""
Sei un esperto di letteratura italiana. Il tuo compito è scrivere una sinossi migliorata per questo libro ESCLUSIVAMENTE IN LINGUA ITALIANA.

INFORMAZIONI DEL LIBRO:
- Titolo: {real_title}
- Autore: {real_author}
- Sinossi attuale: {current_synopsis}

ISTRUZIONI OBBLIGATORIE:
- Scrivi SEMPRE in italiano perfetto, mai in altre lingue
- Scrivi una sinossi di 2-4 frasi che descriva accuratamente il contenuto dell'opera
- Usa un linguaggio chiaro, elegante e coinvolgente in italiano
- Se l'opera è famosa, includi elementi caratteristici della trama
- Se la sinossi attuale è già buona, migliorala mantenendo il contenuto corretto
- Non inventare informazioni se non le conosci con certezza
- Mantieni un tono professionale ma accessibile
- Se l'opera è straniera, traduci e adatta i concetti per lettori italiani
- IMPORTANTE: La risposta deve essere SOLO in italiano

Rispondi ESCLUSIVAMENTE con la nuova sinossi in italiano, senza altre spiegazioni./nothink
"""

    headers = {
        "Content-Type": "application/json",
    }
    
    data = {
        "model": CONFIG['model'],
        "messages": [
            {"role": "system", "content": "Sei un esperto di letteratura italiana che scrive SEMPRE sinossi accurate e coinvolgenti ESCLUSIVAMENTE IN LINGUA ITALIANA. Non usare mai altre lingue./nothink"},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": -1,
        "stream": False
    }
    
    # Apply rate limiting
    rate_limiter.wait()
    
    try:
        response = requests.post(CONFIG['api_url'], headers=headers, json=data)
        response.raise_for_status()
        
        result = response.json()
        content = result['choices'][0]['message']['content'].strip()
        
        # Clean up the response - remove all unwanted tags and content
        content = content.replace('/nothink', '').strip()
        
        # Remove think tags and their content
        import re
        content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
        content = re.sub(r'<thinking>.*?</thinking>', '', content, flags=re.DOTALL)
        
        # Remove any other common unwanted patterns
        content = re.sub(r'\[.*?\]', '', content)  # Remove bracketed content
        content = re.sub(r'\*\*.*?\*\*', '', content)  # Remove bold markdown
        content = re.sub(r'\*.*?\*', '', content)  # Remove italic markdown
        content = re.sub(r'```.*?```', '', content, flags=re.DOTALL)  # Remove code blocks
        
        # Clean up extra whitespace and newlines
        content = re.sub(r'\n+', ' ', content)  # Replace multiple newlines with space
        content = re.sub(r'\s+', ' ', content)  # Replace multiple spaces with single space
        content = content.strip()
        
        # Validate the response
        if len(content) < 20:
            return current_synopsis  # Keep current if response is too short
        
        # Check if response is in Italian
        if not is_italian_text(content):
            console.log(f"[yellow]Warning:[/yellow] Response for {book_id} doesn't appear to be in Italian, keeping current synopsis")
            return current_synopsis
        
        return content
        
    except Exception as e:
        console.log(f"[bold red]Error:[/bold red] API request failed for {book_id}: {str(e)}")
        return current_synopsis  # Keep current synopsis on error

def save_checkpoint(data, processed_count):
    """Save a checkpoint of the current progress"""
    checkpoint_file = f'synopsis_checkpoint_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    
    try:
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump({
                'processed_count': processed_count,
                'data': data,
                'timestamp': datetime.now().isoformat()
            }, f, ensure_ascii=False, indent=2)
        console.log(f"[green]Checkpoint saved:[/green] {checkpoint_file}")
    except Exception as e:
        console.log(f"[red]Failed to save checkpoint:[/red] {e}")

def load_checkpoint():
    """Load the most recent checkpoint if available"""
    import glob
    checkpoint_files = glob.glob('synopsis_checkpoint_*.json')
    
    if not checkpoint_files:
        return None, 0
    
    # Get the most recent checkpoint
    latest_checkpoint = max(checkpoint_files)
    console.log(f"[yellow]Found checkpoint:[/yellow] {latest_checkpoint}")
    
    try:
        with open(latest_checkpoint, 'r', encoding='utf-8') as f:
            checkpoint_data = json.load(f)
        
        return checkpoint_data['data'], checkpoint_data['processed_count']
    except Exception as e:
        console.log(f"[red]Failed to load checkpoint:[/red] {e}")
        return None, 0

def main():
    console.print(Panel.fit(
        "[bold blue]📖 Synopsis Reprocessor[/bold blue]\n"
        "Improving all synopses using local LLM",
        border_style="blue"
    ))
    
    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f'augmented.json.backup_synopsis_{timestamp}'
    
    try:
        shutil.copy('augmented.json', backup_file)
        console.print(f"[green]✅ Created backup:[/green] {backup_file}")
    except Exception as e:
        console.print(f"[red]❌ Failed to create backup:[/red] {e}")
        return
    
    # Check if we should resume from checkpoint
    data, processed_count = load_checkpoint()
    
    if data is None:
        # Load fresh data
        try:
            with open('augmented.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
            console.print(f"[green]✅ Loaded {len(data)} books from augmented.json[/green]")
            processed_count = 0
        except Exception as e:
            console.print(f"[red]❌ Failed to load data:[/red] {e}")
            return
    else:
        console.print(f"[yellow]📂 Resuming from checkpoint - {processed_count} books already processed[/yellow]")
    
    # Filter books that need synopsis improvement
    books_to_process = []
    for book_id, book in data.items():
        if processed_count > 0:
            # Skip already processed books when resuming
            processed_count -= 1
            continue
            
        # Check if book has required fields and could benefit from synopsis improvement
        real_title = book.get('real_title', '')
        real_author = book.get('real_author', '')
        current_synopsis = book.get('real_synopsis', '')
        
        if real_title and real_author:  # Only process books with title and author
            books_to_process.append((book_id, book))
    
    if not books_to_process:
        console.print("[yellow]🎉 All books already processed![/yellow]")
        return
    
    console.print(f"[cyan]📊 Found {len(books_to_process)} books to process[/cyan]")
    
    # Initialize rate limiter
    rate_limiter = RateLimiter(CONFIG['rate_limit'])
    
    # Statistics
    improved_count = 0
    error_count = 0
    total_processed = 0
    
    # Process books with progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("Processing synopses...", total=len(books_to_process))
        
        for i, (book_id, book) in enumerate(books_to_process):
            current_synopsis = book.get('real_synopsis', '')
            
            progress.update(task, description=f"Processing: {book.get('real_title', 'Unknown')[:40]}...")
            
            try:
                # Get improved synopsis
                new_synopsis = get_improved_synopsis(book_id, book, rate_limiter)
                
                # Update the book data
                if new_synopsis and new_synopsis != current_synopsis:
                    data[book_id]['real_synopsis'] = new_synopsis
                    improved_count += 1
                    
                    # Show a sample of improvements
                    if improved_count <= 5:
                        console.print(f"[green]📝 Improved:[/green] {book.get('real_title', 'Unknown')[:40]}")
                        console.print(f"[dim]   Old:[/dim] {current_synopsis[:100]}...")
                        console.print(f"[bright_green]   New:[/bright_green] {new_synopsis[:100]}...")
                        console.print()
                
                total_processed += 1
                
                # Save checkpoint every batch_size books
                if (i + 1) % CONFIG['batch_size'] == 0:
                    save_checkpoint(data, total_processed)
                
            except Exception as e:
                error_count += 1
                console.log(f"[red]Error processing {book_id}:[/red] {e}")
            
            progress.advance(task)
    
    # Final save
    console.print("\n[cyan]💾 Saving final results...[/cyan]")
    
    try:
        with open('augmented.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        console.print(f"[green]✅ Successfully saved updated data[/green]")
        
        # Display final statistics
        stats_table = Table(title="Synopsis Reprocessing Results", box=None)
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", style="green")
        
        stats_table.add_row("Total processed", str(total_processed))
        stats_table.add_row("Synopses improved", str(improved_count))
        stats_table.add_row("Errors encountered", str(error_count))
        stats_table.add_row("Improvement rate", f"{improved_count/max(1, total_processed):.1%}")
        
        console.print(stats_table)
        console.print(f"\n[green]🎉 Synopsis reprocessing complete![/green]")
        console.print(f"[dim]📁 Backup saved as: {backup_file}[/dim]")
        
        # Clean up checkpoint files
        import glob
        checkpoint_files = glob.glob('synopsis_checkpoint_*.json')
        for checkpoint_file in checkpoint_files:
            try:
                import os
                os.remove(checkpoint_file)
                console.log(f"[dim]Cleaned up checkpoint: {checkpoint_file}[/dim]")
            except:
                pass
        
    except Exception as e:
        console.print(f"[red]❌ Failed to save results:[/red] {e}")

if __name__ == '__main__':
    main()
