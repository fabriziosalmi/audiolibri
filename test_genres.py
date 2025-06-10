#!/usr/bin/env python3
"""
Simple Genre Analysis Test
"""

import json

def main():
    print("🔍 Testing genre analysis...")
    
    try:
        # Load data
        with open('audiobooks.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Loaded {len(data)} books from audiobooks.json")
        
        with open('augmented.json', 'r', encoding='utf-8') as f:
            augmented = json.load(f)
        print(f"✅ Loaded {len(augmented)} books from augmented.json")
        
        # Analyze real_genre field
        genre_counts = {}
        for book_id, book in augmented.items():
            if 'real_genre' in book and book['real_genre']:
                genre = book['real_genre']
                genre_counts[genre] = genre_counts.get(genre, 0) + 1
        
        print(f"\n📊 Found {len(genre_counts)} unique genres in real_genre field")
        
        # Find suspicious genres (likely typos)
        suspicious = []
        for genre, count in genre_counts.items():
            if any(word in genre.lower() for word in ['ricc', 'ricch']):
                suspicious.append((genre, count))
        
        if suspicious:
            print(f"\n⚠️  Suspicious genres found:")
            for genre, count in suspicious:
                print(f"   {genre}: {count} books")
        else:
            print(f"\n✅ No obvious suspicious genres found")
            
        # Show top genres
        print(f"\n🔝 Top 10 genres:")
        sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
        for genre, count in sorted_genres[:10]:
            print(f"   {genre}: {count} books")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
