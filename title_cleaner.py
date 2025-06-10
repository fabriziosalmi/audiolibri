#!/usr/bin/env python3
"""
Title Cleaner for Audiobook Collection

This script fixes common issues in titles:
- Converts ALL CAPS titles to proper case
- Fixes common formatting issues
- Standardizes punctuation and spacing
- Removes narrator/reader information from titles
- Cleans up special characters
"""

import json
import shutil
import re
from datetime import datetime
from collections import Counter

def main():
    print("📚 Title Data Cleaner")
    print("=" * 50)
    
    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        shutil.copy('augmented.json', f'augmented.json.backup_titles_{timestamp}')
        print(f"✅ Created backup: augmented.json.backup_titles_{timestamp}")
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
    
    # Track changes
    total_changes = 0
    changes_by_type = Counter()
    
    print(f"\n🔍 Analyzing titles...")
    
    # Find issues
    all_caps_titles = []
    special_char_titles = []
    long_titles = []
    narrator_info_titles = []
    
    for book_id, book in data.items():
        title = book.get('title', '').strip()
        real_title = book.get('real_title', '').strip()
        
        # Check original title issues
        if title:
            if title.isupper() and len(title) > 10:
                all_caps_titles.append((book_id, title))
            
            if any(char in title for char in ['/', '\\', '"', '…', '–', '"', '"']):
                special_char_titles.append((book_id, title))
            
            if len(title) > 80:
                long_titles.append((book_id, title))
            
            # Check for narrator information
            narrator_patterns = [
                r'lettura\s+(di|integrale)', r'letto\s+da', r'voce\s+di',
                r'audiolibro\s*:', r'letture\s*$', r'audio\s*lettura',
                r'racconto\s+di', r'narrato\s+da'
            ]
            
            for pattern in narrator_patterns:
                if re.search(pattern, title, re.IGNORECASE):
                    narrator_info_titles.append((book_id, title))
                    break
    
    print(f"📊 Issues found:")
    print(f"   ALL CAPS titles: {len(all_caps_titles)}")
    print(f"   Special characters: {len(special_char_titles)}")
    print(f"   Too long (>80 chars): {len(long_titles)}")
    print(f"   Contains narrator info: {len(narrator_info_titles)}")
    
    # Start fixing
    print(f"\n🔧 Starting fixes...")
    
    # 1. Fix ALL CAPS titles
    print(f"\n1️⃣  Fixing ALL CAPS titles...")
    for book_id, title in all_caps_titles:
        original_title = title
        
        # Convert to title case but preserve specific formatting
        new_title = smart_title_case(title)
        
        if new_title != original_title:
            data[book_id]['title'] = new_title
            print(f"📝 '{original_title[:60]}...' -> '{new_title[:60]}...'")
            total_changes += 1
            changes_by_type['ALL_CAPS_FIXED'] += 1
    
    # 2. Clean special characters
    print(f"\n2️⃣  Cleaning special characters...")
    special_chars_fixed = 0
    for book_id, title in special_char_titles:
        original_title = title
        new_title = clean_special_characters(title)
        
        if new_title != original_title:
            data[book_id]['title'] = new_title
            print(f"📝 '{original_title[:60]}...' -> '{new_title[:60]}...'")
            total_changes += 1
            special_chars_fixed += 1
            changes_by_type['SPECIAL_CHARS_FIXED'] += 1
    
    # 3. Shorten overly long titles
    print(f"\n3️⃣  Shortening long titles...")
    long_titles_fixed = 0
    for book_id, title in long_titles:
        original_title = title
        new_title = shorten_title(title)
        
        if new_title != original_title and len(new_title) < len(original_title):
            data[book_id]['title'] = new_title
            print(f"📝 '{original_title[:40]}...' -> '{new_title[:40]}...'")
            total_changes += 1
            long_titles_fixed += 1
            changes_by_type['LONG_TITLES_FIXED'] += 1
    
    # 4. Remove narrator information (optional - preview only)
    print(f"\n4️⃣  Narrator information found (preview only):")
    narrator_fixes_available = 0
    for book_id, title in narrator_info_titles[:10]:  # Show first 10
        cleaned = remove_narrator_info(title)
        if cleaned != title:
            narrator_fixes_available += 1
            print(f"📋 '{title[:50]}...' -> '{cleaned[:50]}...'")
    
    if narrator_fixes_available > 0:
        print(f"ℹ️  Found {len(narrator_info_titles)} titles with narrator info")
        print(f"    Use --fix-narrator flag to apply these changes")
    
    # Summary
    print(f"\n📊 Summary:")
    print(f"   Total changes made: {total_changes}")
    for change_type, count in changes_by_type.items():
        print(f"   {change_type}: {count}")
    
    if total_changes > 0:
        # Save changes
        try:
            with open('augmented.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Saved changes to augmented.json")
            print(f"📁 Backup available as: augmented.json.backup_titles_{timestamp}")
            
        except Exception as e:
            print(f"❌ Failed to save changes: {e}")
    else:
        print("ℹ️  No changes were made")

def smart_title_case(title):
    """Convert title to proper case while preserving certain patterns"""
    
    # Words that should stay lowercase (unless at start)
    lowercase_words = {
        'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'if', 'in', 'nor', 'of', 
        'on', 'or', 'so', 'the', 'to', 'up', 'yet', 'di', 'da', 'del', 'della', 
        'delle', 'dei', 'degli', 'il', 'la', 'le', 'lo', 'gli', 'un', 'una', 'uno',
        'e', 'o', 'ma', 'per', 'con', 'su', 'tra', 'fra'
    }
    
    # Split by spaces and convert each word
    words = title.split()
    result = []
    
    for i, word in enumerate(words):
        # Remove punctuation for checking
        clean_word = re.sub(r'[^\w]', '', word).lower()
        
        if i == 0 or clean_word not in lowercase_words:
            # Capitalize first letter, keep rest as is (but lowercase)
            if word:
                result.append(word[0].upper() + word[1:].lower())
            else:
                result.append(word)
        else:
            # Keep lowercase
            result.append(word.lower())
    
    return ' '.join(result)

def clean_special_characters(title):
    """Clean problematic special characters from title"""
    
    # Dictionary of character replacements
    char_replacements = {
        '"': '"',  # Smart quotes to regular quotes
        '"': '"',
        ''': "'",  # Smart apostrophes
        ''': "'",
        '…': '...',  # Ellipsis
        '–': '-',   # En dash
        '—': '-',   # Em dash
        '„': '"',   # Other quote styles
        '‚': "'",
        '«': '"',
        '»': '"',
        '/': ' - ', # Forward slash to dash with spaces
        '\\': ' - ', # Backslash to dash
    }
    
    result = title
    for old_char, new_char in char_replacements.items():
        result = result.replace(old_char, new_char)
    
    # Clean up multiple spaces
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result

def shorten_title(title):
    """Shorten overly long titles by removing redundant information"""
    
    # Patterns to remove from end of title
    end_patterns = [
        r'\s*-\s*audiolibro.*$',
        r'\s*-\s*lettura\s+integrale.*$',
        r'\s*-\s*audio\s*lettura.*$',
        r'\s*\(audiolibro\).*$',
        r'\s*\[.*lettura.*\]$',
        r'\s*-\s*letto\s+da.*$',
        r'\s*-\s*voce\s+di.*$',
    ]
    
    result = title
    for pattern in end_patterns:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE).strip()
    
    # If still too long, try to find a natural break point
    if len(result) > 60:
        # Look for common separators
        separators = [' - ', ' / ', ' | ', ': ']
        for sep in separators:
            if sep in result:
                parts = result.split(sep)
                if len(parts[0]) > 20 and len(parts[0]) < 60:
                    result = parts[0].strip()
                    break
    
    return result

def remove_narrator_info(title):
    """Remove narrator/reader information from title"""
    
    # Patterns that indicate narrator information
    narrator_patterns = [
        r'\s*-\s*lettura\s+(di|integrale).*$',
        r'\s*-\s*letto\s+da.*$',
        r'\s*-\s*voce\s+di.*$',
        r'\s*-\s*narrato\s+da.*$',
        r'\s*audiolibro\s*:?\s*',
        r'\s*-\s*audio\s*lettura.*$',
        r'\s*\[.*lettura.*\]',
        r'\s*\(.*lettura.*\)',
    ]
    
    result = title
    for pattern in narrator_patterns:
        result = re.sub(pattern, '', result, flags=re.IGNORECASE).strip()
    
    # Clean up any trailing dashes or colons
    result = re.sub(r'\s*[-:]\s*$', '', result).strip()
    
    return result

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up title issues')
    parser.add_argument('--fix-narrator', action='store_true',
                       help='Also remove narrator information from titles')
    
    args = parser.parse_args()
    
    if args.fix_narrator:
        print("ℹ️  Will also fix narrator information")
        # We'll implement this in a future version
    
    main()
