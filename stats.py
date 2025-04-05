#!/usr/bin/env python3
import json
import os
import argparse
from datetime import datetime
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track
from rich import box
from collections import Counter
import matplotlib.pyplot as plt
import numpy as np
from dateutil import parser as date_parser

console = Console()

DEFAULT_METADATA_FILE = "audiobooks.json"

def format_duration(seconds):
    """Format seconds into hours and minutes"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m"
    else:
        return f"{minutes}m {seconds}s"

def load_metadata(file_path):
    """Load the audiobooks metadata file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        console.print(f"Could not load metadata file: {file_path}")
        return {}

def general_stats(metadata):
    """Display general statistics about the audiobook collection"""
    if not metadata:
        console.print("[yellow]No audiobooks found in the metadata file.[/yellow]")
        return
    
    # Calculate statistics
    total_books = len(metadata)
    total_duration = sum(float(item.get('duration', 0)) for item in metadata.values())
    channels = Counter(item.get('channel', 'Unknown') for item in metadata.values())
    processed_count = sum(1 for item in metadata.values() if item.get('processed', False))
    
    # Find the longest and shortest audiobooks
    books_with_duration = [(k, v) for k, v in metadata.items() if v.get('duration', 0) > 0]
    if books_with_duration:
        longest_book = max(books_with_duration, key=lambda x: x[1].get('duration', 0))
        shortest_book = min(books_with_duration, key=lambda x: x[1].get('duration', 0))
    else:
        longest_book = shortest_book = (None, {'title': 'N/A', 'duration': 0})
    
    # Get recently added books
    try:
        books_with_date = [(k, v) for k, v in metadata.items() if v.get('download_date')]
        books_with_date.sort(key=lambda x: date_parser.parse(x[1].get('download_date', '')), reverse=True)
        recent_books = books_with_date[:5]  # Get 5 most recent
    except:
        recent_books = []
    
    # Create statistics table
    stats_table = Table(title="Audiobook Library Statistics", box=box.ROUNDED)
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", style="magenta")
    
    stats_table.add_row("Total Audiobooks", str(total_books))
    stats_table.add_row("Total Duration", format_duration(total_duration))
    stats_table.add_row("Average Duration", format_duration(total_duration / max(1, total_books)))
    stats_table.add_row("Number of Channels", str(len(channels)))
    stats_table.add_row("Processed Books", f"{processed_count} ({processed_count/max(1, total_books):.1%})")
    
    console.print(stats_table)
    
    # Create longest/shortest books table
    books_table = Table(title="Duration Extremes", box=box.ROUNDED)
    books_table.add_column("Type", style="cyan")
    books_table.add_column("Title", style="green")
    books_table.add_column("Channel", style="blue")
    books_table.add_column("Duration", style="magenta")
    
    books_table.add_row(
        "Longest",
        longest_book[1].get('title', 'Unknown')[:50] + ('...' if len(longest_book[1].get('title', '')) > 50 else ''),
        longest_book[1].get('channel', 'Unknown'),
        format_duration(longest_book[1].get('duration', 0))
    )
    
    books_table.add_row(
        "Shortest",
        shortest_book[1].get('title', 'Unknown')[:50] + ('...' if len(shortest_book[1].get('title', '')) > 50 else ''),
        shortest_book[1].get('channel', 'Unknown'),
        format_duration(shortest_book[1].get('duration', 0))
    )
    
    console.print(books_table)
    
    # Display recent additions
    if recent_books:
        recent_table = Table(title="Recently Added Audiobooks", box=box.ROUNDED)
        recent_table.add_column("Title", style="green")
        recent_table.add_column("Channel", style="blue")
        recent_table.add_column("Date Added", style="yellow")
        recent_table.add_column("Duration", style="magenta")
        
        for _, book in recent_books:
            try:
                date_added = date_parser.parse(book.get('download_date', '')).strftime("%Y-%m-%d")
            except:
                date_added = "Unknown"
                
            recent_table.add_row(
                book.get('title', 'Unknown')[:50] + ('...' if len(book.get('title', '')) > 50 else ''),
                book.get('channel', 'Unknown'),
                date_added,
                format_duration(book.get('duration', 0))
            )
            
        console.print(recent_table)

def channel_stats(metadata):
    """Display statistics grouped by channel"""
    if not metadata:
        return
    
    # Group by channel
    channels = {}
    for book_id, book in metadata.items():
        channel = book.get('channel', 'Unknown')
        if channel not in channels:
            channels[channel] = {
                'count': 0,
                'total_duration': 0,
                'books': []
            }
        channels[channel]['count'] += 1
        channels[channel]['total_duration'] += float(book.get('duration', 0))
        channels[channel]['books'].append(book)
    
    # Sort channels by book count
    sorted_channels = sorted(channels.items(), key=lambda x: x[1]['count'], reverse=True)
    
    # Create channels table
    channel_table = Table(title="Channels Breakdown", box=box.ROUNDED)
    channel_table.add_column("Channel", style="cyan")
    channel_table.add_column("Books", style="magenta", justify="right")
    channel_table.add_column("Total Duration", style="green", justify="right")
    channel_table.add_column("Avg Duration", style="blue", justify="right")
    
    # Add top channels (limit to 15 for readability)
    for channel_name, data in sorted_channels[:15]:
        avg_duration = data['total_duration'] / data['count']
        channel_table.add_row(
            channel_name,
            str(data['count']),
            format_duration(data['total_duration']),
            format_duration(avg_duration)
        )
    
    console.print(channel_table)
    
    # If there are more channels, show a summary for "others"
    if len(sorted_channels) > 15:
        others_count = sum(data['count'] for _, data in sorted_channels[15:])
        others_duration = sum(data['total_duration'] for _, data in sorted_channels[15:])
        console.print(f"[dim]+ {len(sorted_channels) - 15} more channels with {others_count} books " 
                      f"({format_duration(others_duration)})[/dim]")

def duration_distribution(metadata, save_plot=False):
    """Analyze and visualize the distribution of audiobook durations"""
    if not metadata:
        return
    
    # Extract durations
    durations = [float(book.get('duration', 0)) / 60 for book in metadata.values()]  # Convert to minutes
    
    if not durations:
        console.print("[yellow]No duration data available for analysis.[/yellow]")
        return
    
    # Create duration distribution statistics
    duration_stats = {
        'count': len(durations),
        'min': min(durations),
        'max': max(durations),
        'mean': sum(durations) / len(durations),
        'median': sorted(durations)[len(durations) // 2],
    }
    
    # Duration brackets
    brackets = [
        (0, 10, "Very Short (0-10 min)"),
        (10, 30, "Short (10-30 min)"),
        (30, 60, "Medium (30-60 min)"),
        (60, 120, "Long (1-2 hours)"),
        (120, 240, "Very Long (2-4 hours)"),
        (240, float('inf'), "Epic (4+ hours)")
    ]
    
    # Count books in each bracket
    bracket_counts = {label: 0 for _, _, label in brackets}
    for duration in durations:
        for min_val, max_val, label in brackets:
            if min_val <= duration < max_val:
                bracket_counts[label] += 1
                break
    
    # Create duration stats table
    duration_table = Table(title="Duration Analysis", box=box.ROUNDED)
    duration_table.add_column("Statistic", style="cyan")
    duration_table.add_column("Value", style="magenta")
    
    duration_table.add_row("Shortest", format_duration(duration_stats['min'] * 60))
    duration_table.add_row("Longest", format_duration(duration_stats['max'] * 60))
    duration_table.add_row("Average", format_duration(duration_stats['mean'] * 60))
    duration_table.add_row("Median", format_duration(duration_stats['median'] * 60))
    
    console.print(duration_table)
    
    # Create duration distribution table
    dist_table = Table(title="Duration Distribution", box=box.ROUNDED)
    dist_table.add_column("Duration Category", style="cyan")
    dist_table.add_column("Count", style="magenta", justify="right")
    dist_table.add_column("Percentage", style="blue", justify="right")
    
    total_books = len(durations)
    for label, count in bracket_counts.items():
        percentage = (count / total_books) * 100 if total_books > 0 else 0
        dist_table.add_row(label, str(count), f"{percentage:.1f}%")
    
    console.print(dist_table)
    
    # Generate visual plot if matplotlib is available
    if save_plot:
        try:
            labels = list(bracket_counts.keys())
            values = list(bracket_counts.values())
            
            plt.figure(figsize=(10, 6))
            
            # Create the bar chart
            plt.bar(labels, values, color='skyblue')
            plt.title('Duration Distribution of Audiobooks')
            plt.xlabel('Duration Category')
            plt.ylabel('Number of Audiobooks')
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            # Save the plot
            plot_path = 'audiobook_duration_distribution.png'
            plt.savefig(plot_path)
            console.print(f"[green]Plot saved to:[/green] {plot_path}")
            
        except Exception as e:
            console.print(f"[yellow]Could not generate plot: {str(e)}[/yellow]")

def missing_content_report(metadata):
    """Report on audiobooks with missing data"""
    if not metadata:
        return
    
    missing_audio = []
    missing_transcript = []
    missing_thumbnail = []
    
    for book_id, book in metadata.items():
        audio_file = book.get('audio_file', '')
        if audio_file and not os.path.exists(audio_file):
            missing_audio.append((book_id, book))
            
        if not book.get('transcript', '').strip():
            missing_transcript.append((book_id, book))
            
        if not book.get('thumbnail', ''):
            missing_thumbnail.append((book_id, book))
    
    # Create missing content table
    missing_table = Table(title="Missing Content Report", box=box.ROUNDED)
    missing_table.add_column("Content Type", style="cyan")
    missing_table.add_column("Count", style="magenta", justify="right")
    missing_table.add_column("Percentage", style="blue", justify="right")
    
    total_books = len(metadata)
    missing_table.add_row(
        "Missing Audio Files",
        str(len(missing_audio)),
        f"{(len(missing_audio) / total_books) * 100:.1f}%"
    )
    missing_table.add_row(
        "Missing Transcripts",
        str(len(missing_transcript)),
        f"{(len(missing_transcript) / total_books) * 100:.1f}%"
    )
    missing_table.add_row(
        "Missing Thumbnails",
        str(len(missing_thumbnail)),
        f"{(len(missing_thumbnail) / total_books) * 100:.1f}%"
    )
    
    console.print(missing_table)
    
    # If there are missing audio files, list them
    if missing_audio and len(missing_audio) <= 10:
        audio_table = Table(title="Books with Missing Audio Files", box=box.ROUNDED)
        audio_table.add_column("Title", style="cyan")
        audio_table.add_column("Channel", style="blue")
        audio_table.add_column("Expected Path", style="yellow", no_wrap=False)
        
        for _, book in missing_audio:
            audio_table.add_row(
                book.get('title', 'Unknown')[:50] + ('...' if len(book.get('title', '')) > 50 else ''),
                book.get('channel', 'Unknown'),
                book.get('audio_file', 'N/A')
            )
            
        console.print(audio_table)
    elif missing_audio:
        console.print(f"[yellow]{len(missing_audio)} books have missing audio files[/yellow]")

def main():
    parser = argparse.ArgumentParser(description='Audiobook Library Statistics')
    parser.add_argument('-f', '--file', default=DEFAULT_METADATA_FILE, help=f'Path to the metadata file (default: {DEFAULT_METADATA_FILE})')
    parser.add_argument('--channels', action='store_true', help='Show detailed channel statistics')
    parser.add_argument('--duration', action='store_true', help='Show duration distribution analysis')
    parser.add_argument('--missing', action='store_true', help='Report on missing content')
    parser.add_argument('--full', action='store_true', help='Show all statistics')
    parser.add_argument('--plot', action='store_true', help='Generate and save plots')
    
    args = parser.parse_args()
    
    # Load metadata
    console.print(f"[bold]Loading audiobook metadata from[/bold] {args.file}...")
    metadata = load_metadata(args.file)
    
    if not metadata:
        return
    
    # Always show general stats
    general_stats(metadata)
    
    # Show optional stats based on arguments
    if args.channels or args.full:
        console.print("\n")
        channel_stats(metadata)
    
    if args.duration or args.full:
        console.print("\n")
        duration_distribution(metadata, save_plot=args.plot)
    
    if args.missing or args.full:
        console.print("\n")
        missing_content_report(metadata)
        
    # Final summary
    console.print(f"\n[bold green]Analysis complete for {len(metadata)} audiobooks![/bold green]")

if __name__ == "__main__":
    main()