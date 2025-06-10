#!/usr/bin/env python3
"""
Author Data Cleaner for Audiobook Collection

This script fixes common issues in author names:
- Consolidates duplicate authors with different capitalizations
- Fixes obvious typos and inconsistencies
- Standardizes author name formats
"""

import json
import shutil
from datetime import datetime
from collections import Counter
import re

def main():
    print("👤 Author Data Cleaner")
    print("=" * 50)
    
    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        shutil.copy('augmented.json', f'augmented.json.backup_authors_{timestamp}')
        print(f"✅ Created backup: augmented.json.backup_authors_{timestamp}")
    except Exception as e:
        print(f"❌ Failed to create backup: {e}")
        return
    
    # Load data
    try:
        with open('augmented.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Loaded {len(data)} books from augmented.json")
    except Exception as e:
        print(f"❌ Failed to load data: {e}")
        return
    
    # Define author fixes
    author_fixes = [
        # Case variations of the same author
        ('Guy De Maupassant', 'Guy de Maupassant'),
        ('guy de maupassant', 'Guy de Maupassant'),
        ('GUY DE MAUPASSANT', 'Guy de Maupassant'),
        
        # Case fixes for ALL CAPS authors
        ('LEPRINCE DE BEAUMONT', 'Leprince de Beaumont'),
        ('MARCELLO COMITINI', 'Marcello Comitini'),
        ('GIANNI RODARI', 'Gianni Rodari'),
        ('ALESSANDRO FREZZA', 'Alessandro Frezza'),
        
        # Placeholder fixes
        ('N/A', ''),
        ('Unknown', ''),
        ('Sconosciuto', ''),
        
        # Dostoevsky name variations
        ('F. Dostoëvskij', 'Fëdor Dostoevskij'),
        ('Dostoevskij', 'Fëdor Dostoevskij'),
        ('Dostoievski', 'Fëdor Dostoevskij'),
        ('Dostoyevsky', 'Fëdor Dostoevskij'),
        
        # Other common variations
        ('A.L. Knorr', 'A. L. Knorr'),
        ('G.K.Chesterton', 'G.K. Chesterton'),
        ('G. K. Chesterton', 'G.K. Chesterton'),
        
        # Obvious typos or formatting issues
        ('mike bongiorno', 'Mike Bongiorno'),
        ('carlo collodi', 'Carlo Collodi'),
        ('edgar allan poe', 'Edgar Allan Poe'),
    ]
    
    total_changes = 0
    changes_by_author = Counter()
    
    # Apply fixes
    for old_author, new_author in author_fixes:
        changes = 0
        
        for book_id, book in data.items():
            if 'real_author' in book and book['real_author'] == old_author:
                old_title = book.get('title', 'Unknown')
                print(f"📝 '{old_author}' -> '{new_author}' in: {old_title[:60]}")
                book['real_author'] = new_author if new_author else 'Autore Sconosciuto'
                changes += 1
                changes_by_author[new_author if new_author else 'Autore Sconosciuto'] += 1
        
        if changes > 0:
            total_changes += changes
            print(f"✅ Fixed {changes} books for author: '{old_author}'")
    
    # Look for additional potential duplicates by similarity
    print(f"\n🔍 Checking for similar author names...")
    
    author_counts = Counter()
    for book in data.values():
        author = book.get('real_author', '').strip()
        if author and author not in ['', 'Autore Sconosciuto']:
            author_counts[author] += 1
    
    # Find potential duplicates
    authors_list = list(author_counts.keys())
    potential_duplicates = []
    
    for i, author1 in enumerate(authors_list):
        for author2 in authors_list[i+1:]:
            # Check for case-insensitive similarity
            if author1.lower() == author2.lower() and author1 != author2:
                potential_duplicates.append((author1, author2, author_counts[author1], author_counts[author2]))
            # Check for very similar names (missing punctuation, etc.)
            elif (re.sub(r'[^\w\s]', '', author1.lower()) == re.sub(r'[^\w\s]', '', author2.lower()) 
                  and author1 != author2):
                potential_duplicates.append((author1, author2, author_counts[author1], author_counts[author2]))
    
    if potential_duplicates:
        print(f"\n⚠️  Found {len(potential_duplicates)} potential duplicate author pairs:")
        for auth1, auth2, count1, count2 in potential_duplicates:
            print(f"   • '{auth1}' ({count1} books) vs '{auth2}' ({count2} books)")
    
    print(f"\n📊 Summary:")
    print(f"   Total changes made: {total_changes}")
    
    if total_changes > 0:
        # Save changes
        try:
            with open('augmented.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ Saved changes to augmented.json")
            
            # Show new author distribution
            print(f"\n📈 Updated author statistics:")
            new_author_counts = Counter()
            for book in data.values():
                author = book.get('real_author', '').strip()
                if author:
                    new_author_counts[author] += 1
            
            print(f"   Total unique authors: {len(new_author_counts)}")
            print(f"\n   🔝 Top 15 authors after cleanup:")
            for author, count in new_author_counts.most_common(15):
                change_indicator = " ✨" if author in changes_by_author else ""
                print(f"      {author:<40} : {count:>3} books{change_indicator}")
                
        except Exception as e:
            print(f"❌ Failed to save changes: {e}")
    else:
        print("ℹ️  No changes were made")
    
    print(f"\n💡 Tip: Review potential duplicates above and use data_investigator.py to find more issues")

if __name__ == '__main__':
    main()
