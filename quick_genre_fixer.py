#!/usr/bin/env python3
"""
Quick Genre Fixer for Obvious Issues
"""

import json
import shutil
from datetime import datetime

def main():
    print("🔧 Quick Genre Fixer")
    print("=" * 50)
    
    # Create backups first
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        shutil.copy('audiobooks.json', f'audiobooks.json.backup_{timestamp}')
        shutil.copy('augmented.json', f'augmented.json.backup_{timestamp}')
        print(f"✅ Created backups with timestamp {timestamp}")
    except Exception as e:
        print(f"❌ Failed to create backups: {e}")
        return
    
    # Load data
    try:
        with open('audiobooks.json', 'r', encoding='utf-8') as f:
            audiobooks = json.load(f)
        
        with open('augmented.json', 'r', encoding='utf-8') as f:
            augmented = json.load(f)
            
        print(f"✅ Loaded {len(audiobooks)} books from audiobooks.json")
        print(f"✅ Loaded {len(augmented)} books from augmented.json")
    except Exception as e:
        print(f"❌ Failed to load data: {e}")
        return
    
    # Define fixes
    fixes = [
        # Obvious typos that should be "racconto"
        ('Riccardo', 'racconto'),
        ('Riccone', 'racconto'),
        ('Ricciardo', 'racconto'),
        ('Ricettario', 'racconto'),
        
        # Genre consolidations
        ('novella', 'romanzo'),
        ('fantasy', 'fantascienza'),
        ('thriller', 'giallo'),
        
        # Capitalization fixes
        ('Saggio', 'saggio'),
        ('Ragno', 'racconto'),  # Likely a typo
        ('Rapporto', 'racconto'),  # Likely a typo
        ('Tragedia', 'teatro'),
        ('Drammatico', 'teatro'),
        ('Psicologia', 'saggio'),
        ('Humorous Fiction', 'commedia'),
        ('Film', 'documentario'),
    ]
    
    total_changes = 0
    
    for old_genre, new_genre in fixes:
        changes = 0
        
        # Fix in augmented data (where real_genre is)
        for book_id, book in augmented.items():
            if 'real_genre' in book and book['real_genre'] == old_genre:
                print(f"📝 Changing '{old_genre}' -> '{new_genre}' in book: {book.get('title', 'Unknown')}")
                book['real_genre'] = new_genre
                changes += 1
        
        if changes > 0:
            print(f"✅ Fixed {changes} books: '{old_genre}' -> '{new_genre}'")
            total_changes += changes
        else:
            print(f"ℹ️  No books found with genre '{old_genre}'")
    
    print(f"\n📊 Summary: Made {total_changes} total changes")
    
    if total_changes > 0:
        # Save the changes
        try:
            with open('augmented.json', 'w', encoding='utf-8') as f:
                json.dump(augmented, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Saved changes to augmented.json")
            print(f"📁 Backup available as: augmented.json.backup_{timestamp}")
            
            # Show new genre distribution
            print(f"\n📊 Updated genre distribution:")
            genre_counts = {}
            for book in augmented.values():
                if 'real_genre' in book and book['real_genre']:
                    genre = book['real_genre']
                    genre_counts[genre] = genre_counts.get(genre, 0) + 1
            
            # Show top 15 genres
            sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
            for genre, count in sorted_genres[:15]:
                print(f"   {genre:<20} : {count:>4} books")
                
        except Exception as e:
            print(f"❌ Failed to save changes: {e}")
    else:
        print("ℹ️  No changes were made")

if __name__ == '__main__':
    main()
