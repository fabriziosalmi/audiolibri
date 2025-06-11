#!/usr/bin/env python3
"""
Author Name Standardizer for Audiobook Collection

This script standardizes author names to achieve consistent formatting:
- Converts ALL CAPS to proper case (e.g., "G. GOZZANO" → "G. Gozzano")
- Expands initials to full names where known (e.g., "F. Dostoevsky" → "Fëdor Dostoevskij")
- Standardizes case inconsistencies (e.g., "autore sconosciuto" → "Autore Sconosciuto")
- Ensures consistent "Name Surname" format throughout the collection
"""

import json
import shutil
import re
from datetime import datetime
from collections import Counter

def create_backup(filename):
    """Create a backup of the original file"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{filename}.backup_authors_{timestamp}"
    shutil.copy2(filename, backup_filename)
    print(f"📁 Backup created: {backup_filename}")
    return backup_filename

def standardize_caps(name):
    """Convert ALL CAPS names to proper case"""
    if name.isupper():
        # Handle special cases for initials
        parts = name.split()
        result_parts = []
        
        for part in parts:
            if len(part) <= 3 and '.' in part:
                # This is likely an initial, keep it mostly uppercase
                result_parts.append(part.capitalize())
            else:
                # Regular word, convert to title case
                result_parts.append(part.capitalize())
        
        return ' '.join(result_parts)
    return name

def expand_known_initials(name):
    """Expand known author initials to full names"""
    expansions = {
        # Dostoevsky variations
        'F. Dostoevsky': 'Fëdor Dostoevskij',
        'F. Dostoevskij': 'Fëdor Dostoevskij',
        'F. Dostoyevsky': 'Fëdor Dostoevskij',
        
        # Other well-known authors where we prefer full names
        'G. Orwell': 'George Orwell',
        'J. Joyce': 'James Joyce',
        'H. Melville': 'Herman Melville',
        'O. Wilde': 'Oscar Wilde',
        'T. Mann': 'Thomas Mann',
        'E. Hemingway': 'Ernest Hemingway',
        'J. Steinbeck': 'John Steinbeck',
        'W. Shakespeare': 'William Shakespeare',
        
        # Italian authors
        'G. Boccaccio': 'Giovanni Boccaccio',
        'U. Foscolo': 'Ugo Foscolo',
        'G. Leopardi': 'Giacomo Leopardi',
        'G. Verga': 'Giovanni Verga',
        'I. Calvino': 'Italo Calvino',
        'A. Manzoni': 'Alessandro Manzoni',
        
        # French authors
        'G. Flaubert': 'Gustave Flaubert',
        'V. Hugo': 'Victor Hugo',
        'M. Proust': 'Marcel Proust',
        'A. Camus': 'Albert Camus',
        'J. Verne': 'Jules Verne',
        
        # Russian authors
        'L. Tolstoy': 'Lev Tolstoy',
        'A. Čechov': 'Anton Čechov',
        'A. Cechov': 'Anton Čechov',
        'A. Puskin': 'Aleksandr Puškin',
        'N. Gogol': 'Nikolaj Gogol',
        
        # German authors
        'H. Hesse': 'Hermann Hesse',
        'F. Kafka': 'Franz Kafka',
        'G. Grass': 'Günter Grass',
        
        # English/American authors
        'H. Lovecraft': 'H.P. Lovecraft',  # Keep the H.P. format as it's well-known
        'A. Doyle': 'Arthur Conan Doyle',
        'C. Dickens': 'Charles Dickens',
        'J. Austen': 'Jane Austen',
        'E. Brontë': 'Emily Brontë',
        'C. Brontë': 'Charlotte Brontë',
        
        # Additional single initial expansions
        'A. Bierce': 'Ambrose Bierce',
        'A. Kaminski': 'Andrzej Kamiński',  # Polish author
        'A. Schnitzler': 'Arthur Schnitzler',
        'C. Bukowski': 'Charles Bukowski',
        'C. Bukowskij': 'Charles Bukowski',  # Alternative spelling
        'C. Pavese': 'Cesare Pavese',
        'D. Buzzati': 'Dino Buzzati',
        'E. Salgari': 'Emilio Salgari',
        'E. Zola': 'Émile Zola',
        'F. Nietzsche': 'Friedrich Nietzsche',
        'F. Pessoa': 'Fernando Pessoa',
        'G. Caproni': 'Giorgio Caproni',
        'G. D\'Annunzio': 'Gabriele D\'Annunzio',
        'G. Deledda': 'Grazia Deledda',
        'G. Gozzano': 'Guido Gozzano',
        'G. Guareschi': 'Giovannino Guareschi',
        'G. Simenon': 'Georges Simenon',
        'J. Keats': 'John Keats',
        'J. London': 'Jack London',
        'J. Saramago': 'José Saramago',
        'J. Stenbeck': 'John Steinbeck',  # Likely typo for Steinbeck
        'K. Gibran': 'Kahlil Gibran',
        'L. Pirandello': 'Luigi Pirandello',
        'L. Tolstoj': 'Lev Tolstoy',
        'M. Leblanc': 'Maurice Leblanc',
        'M. Szabo': 'Magda Szabó',
        'P. Celan': 'Paul Celan',
        'R. Carver': 'Raymond Carver',
        'R. Kipling': 'Rudyard Kipling',
        'S. Esenin': 'Sergei Esenin',
        'S. Zweig': 'Stefan Zweig',
        'T. Eliot': 'T.S. Eliot',  # Keep T.S. as it's the well-known format
        'T. Landolfi': 'Tommaso Landolfi',
        'W. Irving': 'Washington Irving',
        
        # Multiple initials - keep as is since they're well-known in that format
        'A. L. Knorr': 'A. L. Knorr',
        'D. H. Lawrence': 'D.H. Lawrence',  # Standardize spacing
        'E. L. James': 'E.L. James',       # Standardize spacing
        'H. G. Wells': 'H.G. Wells',       # Standardize spacing
        'H. P. Lovecraft': 'H.P. Lovecraft', # Standardize spacing
        'J. L. Borges': 'Jorge Luis Borges', # Full name is better known
        'J. W. Goethe': 'Johann Wolfgang von Goethe', # Full name
        'P. G. Wodehouse': 'P.G. Wodehouse', # Standardize spacing
        'R. M. Rilke': 'Rainer Maria Rilke', # Full name
        
        # Already in correct format but ensure consistency
        'H.P. Lovecraft': 'H.P. Lovecraft',
        'G.K. Chesterton': 'G.K. Chesterton',
        'T.S. Eliot': 'T.S. Eliot',
    }
    
    return expansions.get(name, name)

def fix_case_inconsistencies(name):
    """Fix common case inconsistencies"""
    case_fixes = {
        'autore sconosciuto': 'Autore Sconosciuto',
        'anonimo': 'Anonimo',
        'unknown': 'Unknown',
        'sconosciuto': 'Sconosciuto',
    }
    
    return case_fixes.get(name.lower(), name)

def standardize_author_format(name):
    """Apply comprehensive standardization to author name"""
    if not name or not name.strip():
        return name
    
    # Clean up the name
    name = name.strip()
    
    # Fix case inconsistencies first
    name = fix_case_inconsistencies(name)
    
    # Convert ALL CAPS to proper case
    name = standardize_caps(name)
    
    # Expand known initials to full names
    name = expand_known_initials(name)
    
    # Clean up extra spaces
    name = re.sub(r'\s+', ' ', name)
    
    return name

def analyze_changes_needed(data):
    """Analyze what changes would be made"""
    changes_preview = []
    authors = set()
    
    for book_id, book in data.items():
        author = book.get('real_author', '')
        if author and author.strip():
            original = author.strip()
            standardized = standardize_author_format(original)
            
            if original != standardized:
                changes_preview.append((original, standardized))
            
            authors.add(standardized)
    
    return changes_preview, authors

def main():
    filename = 'augmented.json'
    
    print("🔧 Author Name Standardizer")
    print("=" * 50)
    
    # Load data
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"📚 Loaded {len(data)} books from {filename}")
    except FileNotFoundError:
        print(f"❌ File {filename} not found!")
        return
    except json.JSONDecodeError as e:
        print(f"❌ Error reading JSON: {e}")
        return
    
    # Analyze what changes would be made
    print("\n🔍 Analyzing changes needed...")
    changes_preview, final_authors = analyze_changes_needed(data)
    
    if not changes_preview:
        print("✅ All author names are already properly standardized!")
        return
    
    print(f"\n📋 Preview of changes ({len(changes_preview)} authors to be standardized):")
    print("-" * 80)
    
    # Group changes by type
    caps_fixes = []
    initial_expansions = []
    case_fixes = []
    other_fixes = []
    
    for original, standardized in changes_preview:
        if original.isupper():
            caps_fixes.append((original, standardized))
        elif len(original.split()) == 2 and len(original.split()[0]) <= 3 and '.' in original.split()[0]:
            if original != standardized:
                initial_expansions.append((original, standardized))
        elif original.lower() != original and original != standardized:
            case_fixes.append((original, standardized))
        else:
            other_fixes.append((original, standardized))
    
    if caps_fixes:
        print(f"\n🔤 ALL CAPS fixes ({len(caps_fixes)}):")
        for orig, std in caps_fixes[:10]:
            print(f"   '{orig}' → '{std}'")
        if len(caps_fixes) > 10:
            print(f"   ... and {len(caps_fixes) - 10} more")
    
    if initial_expansions:
        print(f"\n📝 Initial expansions ({len(initial_expansions)}):")
        for orig, std in initial_expansions[:10]:
            print(f"   '{orig}' → '{std}'")
        if len(initial_expansions) > 10:
            print(f"   ... and {len(initial_expansions) - 10} more")
    
    if case_fixes:
        print(f"\n📋 Case fixes ({len(case_fixes)}):")
        for orig, std in case_fixes[:10]:
            print(f"   '{orig}' → '{std}'")
        if len(case_fixes) > 10:
            print(f"   ... and {len(case_fixes) - 10} more")
    
    if other_fixes:
        print(f"\n🔧 Other fixes ({len(other_fixes)}):")
        for orig, std in other_fixes[:10]:
            print(f"   '{orig}' → '{std}'")
        if len(other_fixes) > 10:
            print(f"   ... and {len(other_fixes) - 10} more")
    
    # Ask for confirmation
    print(f"\n📊 Summary:")
    print(f"   Total changes: {len(changes_preview)}")
    print(f"   Final unique authors: {len(final_authors)}")
    
    response = input(f"\n🤔 Apply these standardizations to {filename}? (y/N): ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ Operation cancelled by user")
        return
    
    # Create backup
    backup_file = create_backup(filename)
    
    # Apply changes
    total_changes = 0
    changes_by_type = Counter()
    
    for book_id, book in data.items():
        if 'real_author' in book:
            original = book['real_author']
            if original and original.strip():
                standardized = standardize_author_format(original.strip())
                
                if original != standardized:
                    book['real_author'] = standardized
                    total_changes += 1
                    
                    # Categorize change type
                    if original.isupper():
                        changes_by_type['ALL CAPS fixes'] += 1
                    elif len(original.split()) == 2 and len(original.split()[0]) <= 3 and '.' in original.split()[0]:
                        changes_by_type['Initial expansions'] += 1
                    elif original.lower() != original:
                        changes_by_type['Case fixes'] += 1
                    else:
                        changes_by_type['Other fixes'] += 1
    
    # Save the updated data
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ Successfully updated {filename}")
    except Exception as e:
        print(f"❌ Error saving file: {e}")
        print(f"🔄 Restoring from backup...")
        shutil.copy2(backup_file, filename)
        return
    
    # Final summary
    print(f"\n🎉 Standardization Complete!")
    print("=" * 50)
    print(f"📁 Backup saved as: {backup_file}")
    print(f"📚 Total books processed: {len(data)}")
    print(f"🔧 Total changes made: {total_changes}")
    
    if changes_by_type:
        print(f"\n📊 Changes by type:")
        for change_type, count in changes_by_type.most_common():
            print(f"   {change_type}: {count}")
    
    # Show final author statistics
    final_authors = Counter()
    for book in data.values():
        author = book.get('real_author', '')
        if author and author.strip():
            final_authors[author.strip()] += 1
    
    print(f"\n👤 Final author statistics:")
    print(f"   Unique authors: {len(final_authors)}")
    print(f"   Books with authors: {sum(final_authors.values())}")
    
    print(f"\n🔝 Top authors after standardization:")
    for author, count in final_authors.most_common(10):
        print(f"   {author:<40}: {count:>3} books")

if __name__ == '__main__':
    main()
