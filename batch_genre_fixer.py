#!/usr/bin/env python3
"""
Batch Genre Fixer for Audiolibri Collection

This script automatically fixes the most obvious genre issues based on analysis.
It's designed to be run after reviewing the genre_manager.py analysis.
"""

import json
import sys
from collections import Counter
import argparse
import shutil
from datetime import datetime

class BatchGenreFixer:
    def __init__(self, audiobooks_file='audiobooks.json', augmented_file='augmented.json'):
        self.audiobooks_file = audiobooks_file
        self.augmented_file = augmented_file
        self.data = {}
        self.augmented_data = {}
        self.changes_made = []
        
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
    
    def create_backup(self):
        """Create timestamped backups of the files"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            # Backup main file
            backup_main = f"{self.audiobooks_file}.backup_{timestamp}"
            shutil.copy(self.audiobooks_file, backup_main)
            print(f"📁 Created backup: {backup_main}")
            
            # Backup augmented file if it exists
            if self.augmented_data:
                backup_augmented = f"{self.augmented_file}.backup_{timestamp}"
                shutil.copy(self.augmented_file, backup_augmented)
                print(f"📁 Created backup: {backup_augmented}")
                
            return True
        except Exception as e:
            print(f"❌ Error creating backups: {e}")
            return False
    
    def replace_genre(self, old_genre, new_genre, source_field='real_genre'):
        """Replace a genre across both data files"""
        replacements = 0
        affected_books = []
        
        # Replace in main data
        for book_id, book in self.data.items():
            if source_field in book:
                if isinstance(book[source_field], str) and book[source_field] == old_genre:
                    book[source_field] = new_genre
                    replacements += 1
                    affected_books.append((book_id, book.get('title', 'Unknown')))
                elif isinstance(book[source_field], list) and old_genre in book[source_field]:
                    idx = book[source_field].index(old_genre)
                    book[source_field][idx] = new_genre
                    replacements += 1
                    affected_books.append((book_id, book.get('title', 'Unknown')))
        
        # Replace in augmented data
        for book_id, book in self.augmented_data.items():
            if source_field in book:
                if isinstance(book[source_field], str) and book[source_field] == old_genre:
                    book[source_field] = new_genre
                    replacements += 1
                    # Only add if not already in affected_books
                    if not any(bid == book_id for bid, _ in affected_books):
                        affected_books.append((book_id, book.get('title', 'Unknown')))
                elif isinstance(book[source_field], list) and old_genre in book[source_field]:
                    idx = book[source_field].index(old_genre)
                    book[source_field][idx] = new_genre
                    replacements += 1
                    # Only add if not already in affected_books
                    if not any(bid == book_id for bid, _ in affected_books):
                        affected_books.append((book_id, book.get('title', 'Unknown')))
        
        if replacements > 0:
            change_record = {
                'old_genre': old_genre,
                'new_genre': new_genre,
                'source_field': source_field,
                'replacements': replacements,
                'affected_books': len(affected_books)
            }
            self.changes_made.append(change_record)
            print(f"✅ Replaced '{old_genre}' → '{new_genre}' in {replacements} occurrences ({len(affected_books)} books)")
        
        return replacements, affected_books
    
    def apply_obvious_fixes(self, dry_run=True):
        """Apply obvious genre fixes based on analysis"""
        
        print("\n" + "="*80)
        print("🔧 APPLYING OBVIOUS GENRE FIXES")
        print("="*80)
        
        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
        else:
            print("⚠️  LIVE MODE - Changes will be applied!")
        
        print()
        
        # Define obvious fixes based on our analysis
        fixes = [
            # Misspellings that are clearly meant to be 'racconto'
            ('Riccardo', 'racconto', 'real_genre'),
            ('Riccone', 'racconto', 'real_genre'),  
            ('Ricciardo', 'racconto', 'real_genre'),
            
            # Consolidations
            ('novella', 'romanzo', 'real_genre'),
            ('fantasy', 'fantascienza', 'real_genre'),
            
            # Capitalize properly
            ('thriller', 'giallo', 'real_genre'),  # Could be 'horror' or 'giallo', choosing 'giallo'
            
            # Single-use genres that look like mistakes
            ('playlist', 'varie', 'real_genre'),
            ('quiz', 'gioco', 'real_genre'),
            ('diario', 'biografia', 'real_genre'),
        ]
        
        total_changes = 0
        all_affected = []
        
        for old_genre, new_genre, source_field in fixes:
            if not dry_run:
                count, affected = self.replace_genre(old_genre, new_genre, source_field)
                total_changes += count
                all_affected.extend(affected)
            else:
                # Preview what would change
                count = self._count_genre_occurrences(old_genre, source_field)
                if count > 0:
                    print(f"📋 Would replace '{old_genre}' → '{new_genre}' ({count} occurrences)")
                    total_changes += count
        
        print(f"\n📊 Summary: {total_changes} total changes {'would be made' if dry_run else 'made'}")
        
        if not dry_run and total_changes > 0:
            print(f"📚 {len(all_affected)} unique books affected")
        
        return total_changes
    
    def _count_genre_occurrences(self, genre, source_field):
        """Count how many times a genre appears"""
        count = 0
        all_data = {**self.data, **self.augmented_data}
        
        for book_id, book in all_data.items():
            if source_field in book:
                if isinstance(book[source_field], str) and book[source_field] == genre:
                    count += 1
                elif isinstance(book[source_field], list) and genre in book[source_field]:
                    count += 1
        
        return count
    
    def normalize_case(self, dry_run=True):
        """Normalize genre case (first letter uppercase, rest lowercase)"""
        print("\n" + "="*80)
        print("🔧 NORMALIZING GENRE CASE")
        print("="*80)
        
        if dry_run:
            print("🔍 DRY RUN MODE - No changes will be made")
        else:
            print("⚠️  LIVE MODE - Changes will be applied!")
        
        print()
        
        case_fixes = []
        all_data = {**self.data, **self.augmented_data}
        
        # Find genres that need case normalization
        genres_to_fix = set()
        for book_id, book in all_data.items():
            if 'real_genre' in book and book['real_genre']:
                genre = book['real_genre']
                if isinstance(genre, str):
                    normalized = genre.lower()
                    if genre != normalized and not genre.isupper():  # Don't change all-caps genres
                        genres_to_fix.add(genre)
        
        # Apply case normalization
        total_changes = 0
        for genre in genres_to_fix:
            normalized = genre.lower()
            if not dry_run:
                count, _ = self.replace_genre(genre, normalized, 'real_genre')
                total_changes += count
            else:
                count = self._count_genre_occurrences(genre, 'real_genre')
                if count > 0:
                    print(f"📋 Would normalize '{genre}' → '{normalized}' ({count} occurrences)")
                    total_changes += count
        
        print(f"\n📊 Case normalization: {total_changes} changes {'would be made' if dry_run else 'made'}")
        return total_changes
    
    def save_data(self):
        """Save the modified data back to files"""
        try:
            # Save main data
            with open(self.audiobooks_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            
            # Save augmented data if it exists
            if self.augmented_data:
                with open(self.augmented_file, 'w', encoding='utf-8') as f:
                    json.dump(self.augmented_data, f, ensure_ascii=False, indent=2)
            
            print("✅ Files saved successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error saving files: {e}")
            return False
    
    def generate_report(self):
        """Generate a report of all changes made"""
        if not self.changes_made:
            print("\n📝 No changes were made")
            return
        
        print("\n" + "="*80)
        print("📝 CHANGE REPORT")
        print("="*80)
        
        total_replacements = 0
        total_books = 0
        
        for change in self.changes_made:
            print(f"\n🔄 {change['old_genre']} → {change['new_genre']}")
            print(f"   Field: {change['source_field']}")
            print(f"   Replacements: {change['replacements']}")
            print(f"   Books affected: {change['affected_books']}")
            
            total_replacements += change['replacements']
            total_books += change['affected_books']
        
        print(f"\n📊 TOTAL SUMMARY:")
        print(f"   Total replacements: {total_replacements}")
        print(f"   Total books affected: {total_books}")
        print(f"   Change operations: {len(self.changes_made)}")

def main():
    parser = argparse.ArgumentParser(description='Batch fix obvious genre issues')
    parser.add_argument('--audiobooks', '-a', default='audiobooks.json', 
                       help='Path to audiobooks.json file')
    parser.add_argument('--augmented', '-u', default='augmented.json',
                       help='Path to augmented.json file')
    parser.add_argument('--dry-run', action='store_true', default=True,
                       help='Preview changes without applying them (default)')
    parser.add_argument('--apply', action='store_true',
                       help='Actually apply the changes (overrides --dry-run)')
    parser.add_argument('--normalize-case', action='store_true',
                       help='Also normalize genre case')
    
    args = parser.parse_args()
    
    # Determine if this is a dry run
    dry_run = args.dry_run and not args.apply
    
    # Create fixer
    fixer = BatchGenreFixer(args.audiobooks, args.augmented)
    
    # Load data
    if not fixer.load_data():
        sys.exit(1)
    
    if not dry_run:
        # Create backups before making changes
        if not fixer.create_backup():
            print("❌ Could not create backups. Aborting.")
            sys.exit(1)
    
    # Apply fixes
    changes = fixer.apply_obvious_fixes(dry_run=dry_run)
    
    if args.normalize_case:
        case_changes = fixer.normalize_case(dry_run=dry_run)
        changes += case_changes
    
    if not dry_run and changes > 0:
        # Save changes
        if fixer.save_data():
            fixer.generate_report()
        else:
            print("❌ Failed to save changes")
            sys.exit(1)
    elif dry_run and changes > 0:
        print(f"\n💡 To apply these {changes} changes, run:")
        print(f"   python3 {sys.argv[0]} --apply")
    elif changes == 0:
        print("\n✅ No changes needed - genres look good!")

if __name__ == '__main__':
    main()
