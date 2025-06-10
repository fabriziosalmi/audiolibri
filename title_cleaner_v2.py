#!/usr/bin/env python3
"""
Enhanced Title Cleaner - Second Pass

This script handles remaining title issues after the first pass.
"""

import json
import shutil
import re
from datetime import datetime

def main():
    print("📚 Enhanced Title Cleaner - Second Pass")
    print("=" * 60)
    
    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    try:
        shutil.copy('augmented.json', f'augmented.json.backup_titles2_{timestamp}')
        print(f"✅ Created backup: augmented.json.backup_titles2_{timestamp}")
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
    
    total_changes = 0
    
    print(f"\n🔍 Finding remaining issues...")
    
    # Find remaining ALL CAPS titles
    remaining_caps = []
    remaining_special = []
    
    for book_id, book in data.items():
        title = book.get('title', '').strip()
        
        if title:
            # Check for remaining ALL CAPS (more aggressive)
            if has_excessive_caps(title):
                remaining_caps.append((book_id, title))
            
            # Check for remaining special characters
            if has_problematic_chars(title):
                remaining_special.append((book_id, title))
    
    print(f"📊 Remaining issues:")
    print(f"   ALL CAPS patterns: {len(remaining_caps)}")
    print(f"   Special characters: {len(remaining_special)}")
    
    # Fix remaining ALL CAPS
    if remaining_caps:
        print(f"\n🔧 Fixing remaining ALL CAPS patterns...")
        for book_id, title in remaining_caps:
            original_title = title
            new_title = fix_advanced_caps(title)
            
            if new_title != original_title:
                data[book_id]['title'] = new_title
                print(f"📝 '{original_title[:50]}...' -> '{new_title[:50]}...'")
                total_changes += 1
    
    # Fix remaining special characters
    if remaining_special:
        print(f"\n🔧 Fixing remaining special characters...")
        for book_id, title in remaining_special:
            original_title = title
            new_title = fix_advanced_special_chars(title)
            
            if new_title != original_title:
                data[book_id]['title'] = new_title
                print(f"📝 '{original_title[:50]}...' -> '{new_title[:50]}...'")
                total_changes += 1
    
    print(f"\n📊 Summary: Made {total_changes} additional changes")
    
    if total_changes > 0:
        # Save changes
        try:
            with open('augmented.json', 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Saved changes to augmented.json")
            print(f"📁 Backup available as: augmented.json.backup_titles2_{timestamp}")
            
        except Exception as e:
            print(f"❌ Failed to save changes: {e}")
    else:
        print("ℹ️  No additional changes were made")

def has_excessive_caps(title):
    """Check if title has excessive capitalization patterns"""
    # Count uppercase vs total letters
    letters = [c for c in title if c.isalpha()]
    if not letters:
        return False
    
    uppercase_count = sum(1 for c in letters if c.isupper())
    uppercase_ratio = uppercase_count / len(letters)
    
    # If more than 70% uppercase and more than 10 letters, it's probably ALL CAPS
    return uppercase_ratio > 0.7 and len(letters) > 10

def has_problematic_chars(title):
    """Check for problematic characters we haven't fixed yet"""
    problematic = ['©', '®', '™', '°', '§', '¶', '†', '‡', '•', '‰', '′', '″', '‴']
    return any(char in title for char in problematic)

def fix_advanced_caps(title):
    """Advanced ALL CAPS fixing"""
    # If it looks like ALL CAPS, convert more intelligently
    if has_excessive_caps(title):
        # Split by common separators
        parts = re.split(r'(\s*[-–—/\\:]\s*)', title)
        
        result_parts = []
        for part in parts:
            if re.match(r'\s*[-–—/\\:]\s*', part):
                # Keep separators as-is
                result_parts.append(part)
            else:
                # Convert this part to title case
                result_parts.append(smart_title_case(part))
        
        return ''.join(result_parts)
    
    return title

def fix_advanced_special_chars(title):
    """Fix advanced special character issues"""
    # Additional character replacements
    advanced_replacements = {
        '©': ' (C)',
        '®': ' (R)',
        '™': ' (TM)',
        '°': ' degrees',
        '§': ' section',
        '¶': ' paragraph',
        '†': '+',
        '‡': '++',
        '•': '-',
        '‰': ' per mille',
        '′': "'",
        '″': '"',
        '‴': "'''",
        '…': '...',
    }
    
    result = title
    for old_char, new_char in advanced_replacements.items():
        result = result.replace(old_char, new_char)
    
    # Clean up multiple spaces and trim
    result = re.sub(r'\s+', ' ', result).strip()
    
    return result

def smart_title_case(text):
    """Smart title case conversion"""
    # Words that should stay lowercase (unless at start)
    lowercase_words = {
        'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'if', 'in', 'nor', 'of', 
        'on', 'or', 'so', 'the', 'to', 'up', 'yet', 'di', 'da', 'del', 'della', 
        'delle', 'dei', 'degli', 'il', 'la', 'le', 'lo', 'gli', 'un', 'una', 'uno',
        'e', 'o', 'ma', 'per', 'con', 'su', 'tra', 'fra'
    }
    
    words = text.split()
    result = []
    
    for i, word in enumerate(words):
        # Remove punctuation for checking
        clean_word = re.sub(r'[^\w]', '', word).lower()
        
        if i == 0 or clean_word not in lowercase_words:
            # Capitalize first letter, keep rest lowercase
            if word:
                result.append(word[0].upper() + word[1:].lower())
            else:
                result.append(word)
        else:
            # Keep lowercase
            result.append(word.lower())
    
    return ' '.join(result)

if __name__ == '__main__':
    main()
