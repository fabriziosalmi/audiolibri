#!/usr/bin/env python3
"""
Genre Management Script for Audiolibri Collection

This script helps analyze, clean, and standardize genres across the audiobook collection.
It handles multiple genre sources: 'genre', 'real_genre', and 'categories'.
"""

import json
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Set, Tuple
import argparse
import re

class GenreManager:
    def __init__(self, audiobooks_file='audiobooks.json', augmented_file='augmented.json'):
        self.audiobooks_file = audiobooks_file
        self.augmented_file = augmented_file
        self.data = {}
        self.augmented_data = {}
        
    def load_data(self):
        """Load audiobooks data from JSON files"""
        try:
            with open(self.audiobooks_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            print(f"✅ Loaded {len(self.data)} books from {self.audiobooks_file}")
        except FileNotFoundError:
            print(f"❌ File {self.audiobooks_file} not found")
            return False
        except json.JSONDecodeError as e:
            print(f"❌ Error reading {self.audiobooks_file}: {e}")
            return False
            
        try:
            with open(self.augmented_file, 'r', encoding='utf-8') as f:
                self.augmented_data = json.load(f)
            print(f"✅ Loaded {len(self.augmented_data)} books from {self.augmented_file}")
        except FileNotFoundError:
            print(f"⚠️  File {self.augmented_file} not found, will only use main data")
        except json.JSONDecodeError as e:
            print(f"⚠️  Error reading {self.augmented_file}: {e}")
            
        return True
    
    def extract_all_genres(self) -> Dict[str, Set[str]]:
        """Extract all unique genres from all sources"""
        genres = {
            'genre': set(),
            'real_genre': set(),
            'categories': set()
        }
        
        all_data = {**self.data, **self.augmented_data}
        
        for book_id, book in all_data.items():
            # Extract from 'genre' field
            if 'genre' in book and book['genre']:
                if isinstance(book['genre'], str):
                    genres['genre'].add(book['genre'].strip())
                elif isinstance(book['genre'], list):
                    genres['genre'].update([g.strip() for g in book['genre'] if g])
            
            # Extract from 'real_genre' field
            if 'real_genre' in book and book['real_genre']:
                if isinstance(book['real_genre'], str):
                    genres['real_genre'].add(book['real_genre'].strip())
                elif isinstance(book['real_genre'], list):
                    genres['real_genre'].update([g.strip() for g in book['real_genre'] if g])
            
            # Extract from 'categories' field
            if 'categories' in book and book['categories']:
                if isinstance(book['categories'], list):
                    genres['categories'].update([c.strip() for c in book['categories'] if c])
                elif isinstance(book['categories'], str):
                    genres['categories'].add(book['categories'].strip())
        
        return genres
    
    def count_genres(self) -> Dict[str, Counter]:
        """Count occurrences of each genre across all sources"""
        genre_counts = {
            'genre': Counter(),
            'real_genre': Counter(),
            'categories': Counter()
        }
        
        all_data = {**self.data, **self.augmented_data}
        
        for book_id, book in all_data.items():
            # Count 'genre' field
            if 'genre' in book and book['genre']:
                if isinstance(book['genre'], str):
                    genre_counts['genre'][book['genre'].strip()] += 1
                elif isinstance(book['genre'], list):
                    for g in book['genre']:
                        if g:
                            genre_counts['genre'][g.strip()] += 1
            
            # Count 'real_genre' field
            if 'real_genre' in book and book['real_genre']:
                if isinstance(book['real_genre'], str):
                    genre_counts['real_genre'][book['real_genre'].strip()] += 1
                elif isinstance(book['real_genre'], list):
                    for g in book['real_genre']:
                        if g:
                            genre_counts['real_genre'][g.strip()] += 1
            
            # Count 'categories' field
            if 'categories' in book and book['categories']:
                if isinstance(book['categories'], list):
                    for c in book['categories']:
                        if c:
                            genre_counts['categories'][c.strip()] += 1
                elif isinstance(book['categories'], str):
                    genre_counts['categories'][book['categories'].strip()] += 1
        
        return genre_counts
    
    def analyze_genres(self):
        """Analyze and display genre distribution"""
        genre_counts = self.count_genres()
        
        print("\n" + "="*80)
        print("📊 GENRE ANALYSIS REPORT")
        print("="*80)
        
        for source, counts in genre_counts.items():
            print(f"\n📚 {source.upper().replace('_', ' ')} FIELD:")
            print(f"   Total unique genres: {len(counts)}")
            print(f"   Total assignments: {sum(counts.values())}")
            
            if counts:
                print(f"\n   🔝 Top 20 most common:")
                for genre, count in counts.most_common(20):
                    print(f"      {genre:<30} : {count:>4} books")
                
                print(f"\n   🔍 Rare genres (≤ 5 books):")
                rare_genres = [(g, c) for g, c in counts.items() if c <= 5]
                if rare_genres:
                    rare_genres.sort(key=lambda x: x[1])
                    for genre, count in rare_genres:
                        print(f"      {genre:<30} : {count:>4} books")
                else:
                    print("      None found")
    
    def find_problematic_genres(self) -> Dict[str, List[Tuple[str, int]]]:
        """Find potentially problematic genres"""
        genre_counts = self.count_genres()
        problems = {}
        
        for source, counts in genre_counts.items():
            issues = []
            
            for genre, count in counts.items():
                # Check for various issues
                if not genre or genre.strip() == "":
                    issues.append((f"Empty genre: '{genre}'", count))
                elif len(genre) < 3:
                    issues.append((f"Too short: '{genre}'", count))
                elif len(genre) > 50:
                    issues.append((f"Too long: '{genre}'", count))
                elif re.search(r'\d{4}', genre):  # Contains year
                    issues.append((f"Contains year: '{genre}'", count))
                elif genre.lower() in ['unknown', 'n/a', 'na', 'none', 'null']:
                    issues.append((f"Placeholder: '{genre}'", count))
                elif re.search(r'[^\w\s\-\'àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ]', genre, re.IGNORECASE):
                    issues.append((f"Special chars: '{genre}'", count))
                elif count == 1:  # Single occurrence
                    issues.append((f"Single use: '{genre}'", count))
            
            if issues:
                problems[source] = issues
        
        return problems
    
    def suggest_consolidations(self) -> Dict[str, List[Tuple[str, List[str]]]]:
        """Suggest genre consolidations based on similarity"""
        genre_counts = self.count_genres()
        suggestions = {}
        
        for source, counts in genre_counts.items():
            consolidations = []
            genres_list = list(counts.keys())
            
            # Group similar genres
            genre_groups = defaultdict(list)
            
            for genre in genres_list:
                genre_lower = genre.lower().strip()
                
                # Basic normalization
                normalized = re.sub(r'[^\w\s]', '', genre_lower)
                normalized = re.sub(r'\s+', ' ', normalized).strip()
                
                # Group by common roots
                if 'romanzo' in normalized or 'novel' in normalized:
                    genre_groups['romanzo'].append(genre)
                elif 'racconto' in normalized or 'short' in normalized or 'story' in normalized:
                    genre_groups['racconto'].append(genre)
                elif 'poesia' in normalized or 'poetry' in normalized or 'poem' in normalized:
                    genre_groups['poesia'].append(genre)
                elif 'teatro' in normalized or 'drama' in normalized or 'theatre' in normalized:
                    genre_groups['teatro'].append(genre)
                elif 'biografia' in normalized or 'biography' in normalized:
                    genre_groups['biografia'].append(genre)
                elif 'storia' in normalized or 'history' in normalized or 'storico' in normalized:
                    genre_groups['storia'].append(genre)
                elif 'fantasy' in normalized or 'fantasia' in normalized:
                    genre_groups['fantasy'].append(genre)
                elif 'giallo' in normalized or 'mystery' in normalized or 'detective' in normalized:
                    genre_groups['giallo'].append(genre)
                elif 'horror' in normalized or 'thriller' in normalized:
                    genre_groups['horror'].append(genre)
                elif 'commedia' in normalized or 'comedy' in normalized or 'comic' in normalized:
                    genre_groups['commedia'].append(genre)
                elif 'avventura' in normalized or 'adventure' in normalized:
                    genre_groups['avventura'].append(genre)
                elif 'scienza' in normalized or 'science' in normalized or 'scientifico' in normalized:
                    genre_groups['scienza'].append(genre)
                elif 'fiction' in normalized:
                    genre_groups['fiction'].append(genre)
                else:
                    genre_groups['other'].append(genre)
            
            # Create consolidation suggestions
            for group_name, group_genres in genre_groups.items():
                if len(group_genres) > 1 and group_name != 'other':
                    # Calculate total count for the group
                    total_count = sum(counts.get(g, 0) for g in group_genres)
                    if total_count > 5:  # Only suggest if significant
                        consolidations.append((f"Consolidate to '{group_name}'", group_genres))
            
            if consolidations:
                suggestions[source] = consolidations
        
        return suggestions
    
    def display_problematic_genres(self):
        """Display genres that might need fixing"""
        problems = self.find_problematic_genres()
        
        print("\n" + "="*80)
        print("⚠️  PROBLEMATIC GENRES REPORT")
        print("="*80)
        
        if not problems:
            print("✅ No obvious problems found!")
            return
        
        for source, issues in problems.items():
            print(f"\n🚨 Issues in {source.upper().replace('_', ' ')} field:")
            
            issue_types = defaultdict(list)
            for issue, count in issues:
                issue_type = issue.split(':')[0]
                issue_types[issue_type].append((issue, count))
            
            for issue_type, items in issue_types.items():
                print(f"\n   {issue_type}:")
                for issue, count in sorted(items, key=lambda x: x[1], reverse=True)[:10]:
                    print(f"      {issue} ({count} books)")
    
    def display_consolidation_suggestions(self):
        """Display genre consolidation suggestions"""
        suggestions = self.suggest_consolidations()
        
        print("\n" + "="*80)
        print("💡 GENRE CONSOLIDATION SUGGESTIONS")
        print("="*80)
        
        if not suggestions:
            print("✅ No obvious consolidations suggested!")
            return
        
        for source, consolidations in suggestions.items():
            print(f"\n🔄 Suggestions for {source.upper().replace('_', ' ')} field:")
            
            for suggestion, genres in consolidations:
                print(f"\n   {suggestion}:")
                for genre in genres[:10]:  # Show max 10 examples
                    print(f"      • {genre}")
                if len(genres) > 10:
                    print(f"      ... and {len(genres) - 10} more")
    
    def interactive_genre_replacer(self):
        """Interactive tool to replace genres"""
        print("\n" + "="*80)
        print("🔧 INTERACTIVE GENRE REPLACER")
        print("="*80)
        
        print("\nThis tool allows you to replace genres interactively.")
        print("You can specify source field (genre, real_genre, categories)")
        print("Type 'quit' to exit, 'list' to see all genres, 'help' for commands")
        
        while True:
            print("\n" + "-"*50)
            command = input("Command> ").strip().lower()
            
            if command == 'quit':
                break
            elif command == 'help':
                self._show_help()
            elif command == 'list':
                self._list_genres_interactive()
            elif command.startswith('replace'):
                self._handle_replace_command(command)
            elif command.startswith('count'):
                self._handle_count_command(command)
            elif command.startswith('find'):
                self._handle_find_command(command)
            else:
                print("Unknown command. Type 'help' for available commands.")
    
    def _show_help(self):
        """Show help for interactive commands"""
        print("""
Available commands:
  help                          - Show this help
  quit                          - Exit the tool
  list [source]                 - List all genres (optionally for specific source)
  count <genre> [source]        - Count books with specific genre
  find <pattern> [source]       - Find genres matching pattern
  replace <old> <new> [source]  - Replace genre (with confirmation)
  
Sources: genre, real_genre, categories (default: all)

Examples:
  list genre
  count romanzo
  find *poesia*
  replace "racconto breve" "racconto" genre
        """)
    
    def _list_genres_interactive(self):
        """List genres interactively"""
        parts = input("List genres for which source? (genre/real_genre/categories/all): ").strip().lower()
        if not parts:
            parts = 'all'
        
        genre_counts = self.count_genres()
        
        if parts == 'all':
            sources = ['genre', 'real_genre', 'categories']
        elif parts in genre_counts:
            sources = [parts]
        else:
            print(f"Invalid source: {parts}")
            return
        
        for source in sources:
            if source in genre_counts and genre_counts[source]:
                print(f"\n📚 {source.upper().replace('_', ' ')} genres:")
                for genre, count in sorted(genre_counts[source].items()):
                    print(f"  {genre:<40} : {count:>4} books")
    
    def _handle_count_command(self, command):
        """Handle count command"""
        parts = command.split()[1:]  # Remove 'count'
        if not parts:
            print("Usage: count <genre> [source]")
            return
        
        genre = parts[0]
        source = parts[1] if len(parts) > 1 else 'all'
        
        genre_counts = self.count_genres()
        
        if source == 'all':
            total = 0
            for src, counts in genre_counts.items():
                count = counts.get(genre, 0)
                if count > 0:
                    print(f"  {src}: {count} books")
                    total += count
            print(f"  Total: {total} books")
        elif source in genre_counts:
            count = genre_counts[source].get(genre, 0)
            print(f"  {source}: {count} books")
        else:
            print(f"Invalid source: {source}")
    
    def _handle_find_command(self, command):
        """Handle find command"""
        parts = command.split()[1:]  # Remove 'find'
        if not parts:
            print("Usage: find <pattern> [source]")
            return
        
        pattern = parts[0].lower()
        source = parts[1] if len(parts) > 1 else 'all'
        
        genre_counts = self.count_genres()
        
        # Convert shell pattern to regex
        regex_pattern = pattern.replace('*', '.*').replace('?', '.')
        
        if source == 'all':
            sources = ['genre', 'real_genre', 'categories']
        elif source in genre_counts:
            sources = [source]
        else:
            print(f"Invalid source: {source}")
            return
        
        for src in sources:
            matches = []
            for genre, count in genre_counts[src].items():
                if re.search(regex_pattern, genre.lower()):
                    matches.append((genre, count))
            
            if matches:
                print(f"\n📚 Matches in {src.upper().replace('_', ' ')}:")
                for genre, count in sorted(matches, key=lambda x: x[1], reverse=True):
                    print(f"  {genre:<40} : {count:>4} books")
    
    def _handle_replace_command(self, command):
        """Handle replace command"""
        parts = command.split()[1:]  # Remove 'replace'
        if len(parts) < 2:
            print("Usage: replace <old_genre> <new_genre> [source]")
            return
        
        old_genre = parts[0].strip('"\'')
        new_genre = parts[1].strip('"\'')
        source = parts[2] if len(parts) > 2 else None
        
        if not source:
            sources = ['genre', 'real_genre', 'categories']
            print("No source specified. Will check all sources.")
        else:
            sources = [source]
        
        # Show what would be changed
        changes_preview = self._preview_genre_replacement(old_genre, new_genre, sources)
        
        if not changes_preview:
            print(f"❌ No books found with genre '{old_genre}' in specified sources")
            return
        
        # Show preview
        total_changes = sum(len(books) for books in changes_preview.values())
        print(f"\n📋 Preview of changes ({total_changes} books affected):")
        for src, books in changes_preview.items():
            if books:
                print(f"  {src}: {len(books)} books")
                for book_id, title in books[:5]:  # Show first 5
                    print(f"    • {title}")
                if len(books) > 5:
                    print(f"    ... and {len(books) - 5} more")
        
        # Confirm
        confirm = input(f"\nReplace '{old_genre}' with '{new_genre}'? (yes/no): ").strip().lower()
        if confirm in ['yes', 'y']:
            self._perform_genre_replacement(old_genre, new_genre, sources, changes_preview)
        else:
            print("❌ Replacement cancelled")
    
    def _preview_genre_replacement(self, old_genre, new_genre, sources):
        """Preview what would be changed"""
        changes = {}
        all_data = {**self.data, **self.augmented_data}
        
        for source in sources:
            changes[source] = []
            
            for book_id, book in all_data.items():
                if source in book:
                    if isinstance(book[source], str) and book[source] == old_genre:
                        changes[source].append((book_id, book.get('title', 'Unknown')))
                    elif isinstance(book[source], list) and old_genre in book[source]:
                        changes[source].append((book_id, book.get('title', 'Unknown')))
        
        return changes
    
    def _perform_genre_replacement(self, old_genre, new_genre, sources, changes_preview):
        """Actually perform the genre replacement"""
        replacements_made = 0
        
        # Replace in main data
        for source in sources:
            for book_id, _ in changes_preview.get(source, []):
                if book_id in self.data and source in self.data[book_id]:
                    if isinstance(self.data[book_id][source], str):
                        if self.data[book_id][source] == old_genre:
                            self.data[book_id][source] = new_genre
                            replacements_made += 1
                    elif isinstance(self.data[book_id][source], list):
                        if old_genre in self.data[book_id][source]:
                            idx = self.data[book_id][source].index(old_genre)
                            self.data[book_id][source][idx] = new_genre
                            replacements_made += 1
        
        # Replace in augmented data
        for source in sources:
            for book_id, _ in changes_preview.get(source, []):
                if book_id in self.augmented_data and source in self.augmented_data[book_id]:
                    if isinstance(self.augmented_data[book_id][source], str):
                        if self.augmented_data[book_id][source] == old_genre:
                            self.augmented_data[book_id][source] = new_genre
                            replacements_made += 1
                    elif isinstance(self.augmented_data[book_id][source], list):
                        if old_genre in self.augmented_data[book_id][source]:
                            idx = self.augmented_data[book_id][source].index(old_genre)
                            self.augmented_data[book_id][source][idx] = new_genre
                            replacements_made += 1
        
        print(f"✅ Made {replacements_made} replacements")
        
        # Ask if user wants to save
        save = input("Save changes to files? (yes/no): ").strip().lower()
        if save in ['yes', 'y']:
            self._save_data()
        else:
            print("❌ Changes not saved")
    
    def _save_data(self):
        """Save data back to files"""
        try:
            # Backup original files
            import shutil
            shutil.copy(self.audiobooks_file, f"{self.audiobooks_file}.backup")
            if self.augmented_data:
                shutil.copy(self.augmented_file, f"{self.augmented_file}.backup")
            
            # Save main data
            with open(self.audiobooks_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            
            # Save augmented data if it exists
            if self.augmented_data:
                with open(self.augmented_file, 'w', encoding='utf-8') as f:
                    json.dump(self.augmented_data, f, ensure_ascii=False, indent=2)
            
            print("✅ Files saved successfully")
            print("📁 Backups created with .backup extension")
            
        except Exception as e:
            print(f"❌ Error saving files: {e}")

def main():
    parser = argparse.ArgumentParser(description='Manage genres in audiobook collection')
    parser.add_argument('--audiobooks', '-a', default='audiobooks.json', 
                       help='Path to audiobooks.json file')
    parser.add_argument('--augmented', '-u', default='augmented.json',
                       help='Path to augmented.json file')
    parser.add_argument('--analyze', action='store_true',
                       help='Show genre analysis report')
    parser.add_argument('--problems', action='store_true',
                       help='Show problematic genres')
    parser.add_argument('--suggestions', action='store_true',
                       help='Show consolidation suggestions')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Start interactive genre replacer')
    
    args = parser.parse_args()
    
    # Create genre manager
    manager = GenreManager(args.audiobooks, args.augmented)
    
    # Load data
    if not manager.load_data():
        sys.exit(1)
    
    # Run requested operations
    if args.analyze:
        manager.analyze_genres()
    
    if args.problems:
        manager.display_problematic_genres()
    
    if args.suggestions:
        manager.display_consolidation_suggestions()
    
    if args.interactive:
        manager.interactive_genre_replacer()
    
    # If no specific action requested, show basic analysis
    if not any([args.analyze, args.problems, args.suggestions, args.interactive]):
        print("🔍 Running basic analysis (use --help for more options)")
        manager.analyze_genres()
        manager.display_problematic_genres()
        manager.display_consolidation_suggestions()
        
        print(f"\n💡 Tip: Use --interactive to start the interactive genre replacer")

if __name__ == '__main__':
    main()
