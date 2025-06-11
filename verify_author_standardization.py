#!/usr/bin/env python3
"""
Author Standardization Verification Script

This script verifies the results of the author name standardization
and shows before/after comparisons.
"""

import json
from collections import Counter

def compare_authors():
    """Compare author names before and after standardization"""
    
    # Load backup file (before standardization)
    backup_files = [
        'augmented.json.backup_authors_20250611_104815',
        'augmented.json.backup_authors_20250610_220524'
    ]
    
    old_data = None
    for backup_file in backup_files:
        try:
            with open(backup_file, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
            print(f"📁 Loaded backup file: {backup_file}")
            break
        except FileNotFoundError:
            continue
    
    if old_data is None:
        print("❌ No backup file found")
        return
    
    # Load current file (after standardization)
    try:
        with open('augmented.json', 'r', encoding='utf-8') as f:
            new_data = json.load(f)
        print("📁 Loaded current file (after standardization)")
    except FileNotFoundError:
        print("❌ Current file not found!")
        return
    
    print("\n" + "="*80)
    print("📊 AUTHOR STANDARDIZATION VERIFICATION")
    print("="*80)
    
    # Collect changes
    changes = []
    old_authors = Counter()
    new_authors = Counter()
    
    for book_id in old_data:
        old_author = old_data[book_id].get('real_author', '').strip()
        new_author = new_data[book_id].get('real_author', '').strip()
        
        if old_author:
            old_authors[old_author] += 1
        if new_author:
            new_authors[new_author] += 1
            
        if old_author != new_author and old_author and new_author:
            changes.append((old_author, new_author))
    
    print(f"\n🔧 Changes Made:")
    print(f"   Total author changes: {len(changes)}")
    print(f"   Unique authors before: {len(old_authors)}")
    print(f"   Unique authors after: {len(new_authors)}")
    print(f"   Reduction in duplicates: {len(old_authors) - len(new_authors)}")
    
    # Show specific examples
    if changes:
        print(f"\n📝 Example Changes:")
        print("-" * 80)
        
        # Group by change type
        caps_fixes = []
        expansions = []
        case_fixes = []
        
        for old, new in changes:
            if old.isupper():
                caps_fixes.append((old, new))
            elif len(old.split()) == 2 and len(old.split()[0]) <= 3 and '.' in old.split()[0]:
                if old != new:
                    expansions.append((old, new))
            elif old.lower() == new.lower() and old != new:
                case_fixes.append((old, new))
        
        if caps_fixes:
            print(f"\n🔤 ALL CAPS → Proper Case:")
            for old, new in caps_fixes[:5]:
                print(f"   '{old}' → '{new}'")
        
        if expansions:
            print(f"\n📚 Initial Expansions:")
            for old, new in expansions[:8]:
                print(f"   '{old}' → '{new}'")
        
        if case_fixes:
            print(f"\n📋 Case Standardization:")
            for old, new in case_fixes[:5]:
                print(f"   '{old}' → '{new}'")
    
    # Show most common authors after standardization
    print(f"\n🏆 Top 15 Authors After Standardization:")
    print("-" * 80)
    for i, (author, count) in enumerate(new_authors.most_common(15), 1):
        print(f"{i:2d}. {author:<35} : {count:>3} books")
    
    # Check for remaining inconsistencies
    print(f"\n🔍 Checking for Remaining Issues:")
    
    remaining_caps = [a for a in new_authors.keys() if a.isupper() and len(a) > 3]
    case_variants = {}
    
    for author in new_authors.keys():
        key = author.lower()
        if key not in case_variants:
            case_variants[key] = []
        case_variants[key].append(author)
    
    duplicates = {k: v for k, v in case_variants.items() if len(v) > 1}
    
    if remaining_caps:
        print(f"   ⚠️  Remaining ALL CAPS authors: {len(remaining_caps)}")
        for author in remaining_caps[:5]:
            print(f"      • {author}")
    
    if duplicates:
        print(f"   ⚠️  Remaining case inconsistencies: {len(duplicates)}")
        for variants in list(duplicates.values())[:3]:
            print(f"      • {variants}")
    
    if not remaining_caps and not duplicates:
        print("   ✅ No remaining inconsistencies found!")
    
    print(f"\n✅ Verification Complete!")
    print("="*80)

if __name__ == '__main__':
    compare_authors()
