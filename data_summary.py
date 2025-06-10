#!/usr/bin/env python3
"""
Data Quality Summary Report Generator

Shows a comprehensive summary of all data quality improvements made
"""

import json
from datetime import datetime
from collections import Counter

def main():
    print("📊 DATA QUALITY IMPROVEMENT SUMMARY")
    print("=" * 80)
    print(f"Report generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        with open('audiobooks.json', 'r', encoding='utf-8') as f:
            original_data = json.load(f)
        
        with open('augmented.json', 'r', encoding='utf-8') as f:
            current_data = json.load(f)
            
        print(f"✅ Loaded {len(original_data)} books from audiobooks.json")
        print(f"✅ Loaded {len(current_data)} books from augmented.json")
        
    except Exception as e:
        print(f"❌ Error loading data: {e}")
        return
    
    # Genre improvements
    print(f"\n" + "="*60)
    print(f"🎭 GENRE CLEANUP SUMMARY")
    print(f"="*60)
    
    genre_counts = Counter()
    for book in current_data.values():
        genre = book.get('real_genre', '')
        if genre:
            genre_counts[genre] += 1
    
    print(f"📊 Current Genre Distribution:")
    print(f"   Total unique genres: {len(genre_counts)}")
    print(f"   Top 10 genres:")
    for genre, count in genre_counts.most_common(10):
        print(f"      {genre:<20} : {count:>4} books")
    
    rare_genres = [(g, c) for g, c in genre_counts.items() if c <= 5]
    print(f"\n   Rare genres (≤5 books): {len(rare_genres)}")
    for genre, count in sorted(rare_genres, key=lambda x: x[1]):
        print(f"      {genre:<20} : {count:>4} books")
    
    # Author improvements
    print(f"\n" + "="*60)
    print(f"👤 AUTHOR CLEANUP SUMMARY")
    print(f"="*60)
    
    author_counts = Counter()
    missing_authors = 0
    
    for book in current_data.values():
        author = book.get('real_author', '').strip()
        if author and author not in ['', 'Autore Sconosciuto']:
            author_counts[author] += 1
        else:
            missing_authors += 1
    
    print(f"📊 Current Author Distribution:")
    print(f"   Total unique authors: {len(author_counts)}")
    print(f"   Books with authors: {len(current_data) - missing_authors}")
    print(f"   Books missing authors: {missing_authors}")
    
    print(f"\n   🔝 Most prolific authors:")
    for author, count in author_counts.most_common(10):
        print(f"      {author:<35} : {count:>3} books")
    
    # Check for remaining issues
    print(f"\n" + "="*60)
    print(f"🔍 REMAINING ISSUES CHECK")
    print(f"="*60)
    
    issues_found = []
    
    # Check genres
    suspicious_genres = []
    for genre, count in genre_counts.items():
        if any(pattern in genre.lower() for pattern in ['ricc', 'ricch']):
            suspicious_genres.append((genre, count))
        elif genre != genre.strip():
            suspicious_genres.append((f"Whitespace: '{genre}'", count))
    
    if suspicious_genres:
        issues_found.append(f"Suspicious genres: {len(suspicious_genres)}")
        print(f"⚠️  Suspicious genres still found:")
        for genre, count in suspicious_genres:
            print(f"      {genre}: {count} books")
    else:
        print(f"✅ No suspicious genres found")
    
    # Check authors
    suspicious_authors = []
    for author, count in author_counts.items():
        if author.upper() == author and len(author) > 10:
            suspicious_authors.append((f"ALL CAPS: {author}", count))
        elif 'N/A' in author or 'Unknown' in author:
            suspicious_authors.append((f"Placeholder: {author}", count))
    
    if suspicious_authors:
        issues_found.append(f"Suspicious authors: {len(suspicious_authors)}")
        print(f"\n⚠️  Suspicious authors still found:")
        for author, count in suspicious_authors:
            print(f"      {author}: {count} books")
    else:
        print(f"✅ No suspicious authors found")
    
    # Title issues
    title_issues = []
    for book in current_data.values():
        title = book.get('title', '')
        if title:
            if len(title) < 5:
                title_issues.append(f"Too short: '{title}'")
            elif title.upper() == title and len(title) > 20:
                title_issues.append(f"ALL CAPS: '{title[:50]}...'")
    
    if title_issues:
        issues_found.append(f"Title issues: {len(title_issues)}")
        print(f"\n⚠️  Title issues found: {len(title_issues)}")
        for issue in title_issues[:5]:
            print(f"      {issue}")
        if len(title_issues) > 5:
            print(f"      ... and {len(title_issues) - 5} more")
    else:
        print(f"✅ No major title issues found")
    
    # Duration outliers
    durations = []
    for book in current_data.values():
        duration = book.get('duration')
        if duration is not None:
            durations.append(duration)
    
    if durations:
        very_short = [d for d in durations if d < 60]
        very_long = [d for d in durations if d > 50000]  # >14 hours
        
        duration_issues = len(very_short) + len(very_long)
        if duration_issues > 0:
            issues_found.append(f"Duration outliers: {duration_issues}")
            print(f"\n⚠️  Duration outliers found:")
            print(f"      Very short (<1 min): {len(very_short)} books")
            print(f"      Very long (>14 hrs): {len(very_long)} books")
        else:
            print(f"✅ No extreme duration outliers found")
    
    # Summary
    print(f"\n" + "="*60)
    print(f"📋 OVERALL SUMMARY")
    print(f"="*60)
    
    if issues_found:
        print(f"⚠️  Issues still requiring attention:")
        for issue in issues_found:
            print(f"   • {issue}")
        print(f"\n💡 Use the following tools to address remaining issues:")
        print(f"   • python3 data_investigator.py --field <field> - Detailed analysis")
        print(f"   • python3 genre_manager.py --interactive - Fix genres manually")
        print(f"   • python3 author_cleaner.py - Fix remaining author issues")
    else:
        print(f"🎉 Excellent! Major data quality issues have been resolved!")
        print(f"✅ Genres are clean and consolidated")
        print(f"✅ Authors are properly formatted")
        print(f"✅ No obvious suspicious values detected")
    
    print(f"\n📁 Available backup files:")
    import glob
    backups = glob.glob("*.backup_*")
    for backup in sorted(backups):
        print(f"   • {backup}")
    
    print(f"\n🛠️  Available tools:")
    print(f"   • data_investigator.py - Comprehensive data analysis")
    print(f"   • genre_manager.py - Genre management and fixes")
    print(f"   • author_cleaner.py - Author name standardization")
    print(f"   • quick_genre_fixer.py - Batch genre fixes")
    print(f"   • test_genres.py - Quick genre verification")

if __name__ == '__main__':
    main()
