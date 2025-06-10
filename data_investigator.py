#!/usr/bin/env python3
"""
Comprehensive Data Quality Investigator for Audiobook Collection

This script analyzes all fields in the audiobook data to identify:
- Strange values, outliers, and inconsistencies
- Missing or empty fields
- Format issues and potential typos
- Unusual patterns that might indicate data quality problems
"""

import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
import statistics
from urllib.parse import urlparse
import argparse

class DataInvestigator:
    def __init__(self, audiobooks_file='audiobooks.json', augmented_file='augmented.json'):
        self.audiobooks_file = audiobooks_file
        self.augmented_file = augmented_file
        self.data = {}
        self.augmented_data = {}
        self.all_data = {}
        
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
        
        # Merge data for comprehensive analysis
        self.all_data = {**self.data, **self.augmented_data}
        print(f"📊 Total unique books for analysis: {len(self.all_data)}")
        return True
    
    def analyze_field_coverage(self):
        """Analyze which fields exist and their coverage"""
        print("\n" + "="*80)
        print("📋 FIELD COVERAGE ANALYSIS")
        print("="*80)
        
        field_stats = defaultdict(lambda: {'count': 0, 'empty': 0, 'null': 0})
        
        for book_id, book in self.all_data.items():
            for field, value in book.items():
                field_stats[field]['count'] += 1
                
                if value is None:
                    field_stats[field]['null'] += 1
                elif isinstance(value, str) and value.strip() == "":
                    field_stats[field]['empty'] += 1
                elif isinstance(value, list) and len(value) == 0:
                    field_stats[field]['empty'] += 1
        
        total_books = len(self.all_data)
        
        print(f"\n📊 Field Coverage (out of {total_books} books):")
        print(f"{'Field':<25} {'Present':<8} {'Coverage':<10} {'Empty':<7} {'Null':<6}")
        print("-" * 65)
        
        for field in sorted(field_stats.keys()):
            stats = field_stats[field]
            coverage = (stats['count'] / total_books) * 100
            print(f"{field:<25} {stats['count']:<8} {coverage:<9.1f}% {stats['empty']:<7} {stats['null']:<6}")
    
    def analyze_titles(self):
        """Analyze title field for issues"""
        print("\n" + "="*80)
        print("📚 TITLE ANALYSIS")
        print("="*80)
        
        titles = []
        issues = []
        
        for book_id, book in self.all_data.items():
            title = book.get('title', '')
            if title:
                titles.append(title)
                
                # Check for various issues
                if len(title) < 5:
                    issues.append(('Too short', title, book_id))
                elif len(title) > 150:
                    issues.append(('Too long', title[:100] + '...', book_id))
                elif title.upper() == title and len(title) > 20:
                    issues.append(('ALL CAPS', title[:100], book_id))
                elif re.search(r'\d{4}[-/]\d{2}[-/]\d{2}', title):
                    issues.append(('Contains date', title[:100], book_id))
                elif title.count('|') > 2:
                    issues.append(('Too many separators', title[:100], book_id))
                elif re.search(r'[^\w\s\-\'àáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿ.,;:!?()&\""]', title):
                    issues.append(('Special characters', title[:100], book_id))
        
        if titles:
            avg_length = statistics.mean(len(t) for t in titles)
            print(f"📊 Title Statistics:")
            print(f"   Total titles: {len(titles)}")
            print(f"   Average length: {avg_length:.1f} characters")
            print(f"   Shortest: {min(len(t) for t in titles)} chars")
            print(f"   Longest: {max(len(t) for t in titles)} chars")
        
        if issues:
            print(f"\n⚠️  Title Issues Found ({len(issues)} total):")
            issue_types = defaultdict(list)
            for issue_type, title, book_id in issues:
                issue_types[issue_type].append((title, book_id))
            
            for issue_type, items in issue_types.items():
                print(f"\n   {issue_type} ({len(items)} titles):")
                for title, book_id in items[:5]:  # Show first 5
                    print(f"      • {title}")
                if len(items) > 5:
                    print(f"      ... and {len(items) - 5} more")
    
    def analyze_authors(self):
        """Analyze author field for issues"""
        print("\n" + "="*80)
        print("👤 AUTHOR ANALYSIS")
        print("="*80)
        
        authors = []
        author_counts = Counter()
        issues = []
        
        for book_id, book in self.all_data.items():
            # Check both 'real_author' and 'channel' fields
            real_author = book.get('real_author', '')
            channel = book.get('channel', '')
            
            if real_author:
                authors.append(real_author)
                author_counts[real_author] += 1
                
                # Check for issues in real_author
                if len(real_author) < 3:
                    issues.append(('Too short', real_author, book_id))
                elif real_author.lower() in ['unknown', 'sconosciuto', 'n/a', 'na', 'none']:
                    issues.append(('Placeholder', real_author, book_id))
                elif re.search(r'\d{4}', real_author):
                    issues.append(('Contains year', real_author, book_id))
                elif real_author.upper() == real_author and len(real_author) > 10:
                    issues.append(('ALL CAPS', real_author, book_id))
            
            # Analyze channel names for potential issues
            if channel:
                if 'letture' in channel.lower() and not real_author:
                    issues.append(('Channel but no author', channel, book_id))
        
        if authors:
            print(f"📊 Author Statistics:")
            print(f"   Total books with authors: {len(authors)}")
            print(f"   Unique authors: {len(author_counts)}")
            
            print(f"\n🔝 Most prolific authors:")
            for author, count in author_counts.most_common(10):
                print(f"      {author:<40} : {count:>3} books")
        
        if issues:
            print(f"\n⚠️  Author Issues Found ({len(issues)} total):")
            issue_types = defaultdict(list)
            for issue_type, author, book_id in issues:
                issue_types[issue_type].append((author, book_id))
            
            for issue_type, items in issue_types.items():
                print(f"\n   {issue_type} ({len(items)} items):")
                for author, book_id in items[:5]:
                    print(f"      • {author}")
                if len(items) > 5:
                    print(f"      ... and {len(items) - 5} more")
    
    def analyze_durations(self):
        """Analyze duration field for outliers"""
        print("\n" + "="*80)
        print("⏱️  DURATION ANALYSIS")
        print("="*80)
        
        durations = []
        issues = []
        
        for book_id, book in self.all_data.items():
            duration = book.get('duration')
            if duration is not None:
                durations.append(duration)
                
                # Check for issues
                if duration < 60:  # Less than 1 minute
                    issues.append(('Too short', f"{duration}s", book.get('title', 'Unknown'), book_id))
                elif duration > 50000:  # More than ~14 hours
                    hours = duration / 3600
                    issues.append(('Very long', f"{hours:.1f}h", book.get('title', 'Unknown'), book_id))
                elif duration == 0:
                    issues.append(('Zero duration', '0s', book.get('title', 'Unknown'), book_id))
        
        if durations:
            avg_duration = statistics.mean(durations)
            median_duration = statistics.median(durations)
            
            print(f"📊 Duration Statistics:")
            print(f"   Total books with duration: {len(durations)}")
            print(f"   Average duration: {avg_duration/3600:.1f} hours ({avg_duration:.0f}s)")
            print(f"   Median duration: {median_duration/3600:.1f} hours ({median_duration:.0f}s)")
            print(f"   Shortest: {min(durations)/60:.1f} minutes")
            print(f"   Longest: {max(durations)/3600:.1f} hours")
        
        if issues:
            print(f"\n⚠️  Duration Issues Found ({len(issues)} total):")
            issue_types = defaultdict(list)
            for issue_type, duration, title, book_id in issues:
                issue_types[issue_type].append((duration, title, book_id))
            
            for issue_type, items in issue_types.items():
                print(f"\n   {issue_type} ({len(items)} items):")
                for duration, title, book_id in items[:5]:
                    print(f"      • {duration} - {title[:60]}")
                if len(items) > 5:
                    print(f"      ... and {len(items) - 5} more")
    
    def analyze_dates(self):
        """Analyze date fields for issues"""
        print("\n" + "="*80)
        print("📅 DATE ANALYSIS")
        print("="*80)
        
        upload_dates = []
        download_dates = []
        issues = []
        
        for book_id, book in self.all_data.items():
            # Analyze upload_date
            upload_date = book.get('upload_date')
            if upload_date:
                upload_dates.append(upload_date)
                
                # Check format (should be YYYYMMDD)
                if not re.match(r'^\d{8}$', str(upload_date)):
                    issues.append(('Invalid upload date format', str(upload_date), book_id))
                else:
                    year = int(str(upload_date)[:4])
                    if year < 2005 or year > 2025:
                        issues.append(('Suspicious upload year', f"{year}", book_id))
            
            # Analyze download_date
            download_date = book.get('download_date')
            if download_date:
                download_dates.append(download_date)
                
                # Should be ISO format
                if not re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}', str(download_date)):
                    issues.append(('Invalid download date format', str(download_date), book_id))
        
        print(f"📊 Date Statistics:")
        print(f"   Books with upload date: {len(upload_dates)}")
        print(f"   Books with download date: {len(download_dates)}")
        
        if upload_dates:
            years = [int(str(d)[:4]) for d in upload_dates if len(str(d)) >= 4]
            if years:
                year_counts = Counter(years)
                print(f"\n📈 Upload years distribution:")
                for year in sorted(year_counts.keys())[-10:]:  # Last 10 years
                    print(f"      {year}: {year_counts[year]} books")
        
        if issues:
            print(f"\n⚠️  Date Issues Found ({len(issues)} total):")
            issue_types = defaultdict(list)
            for issue_type, date_val, book_id in issues:
                issue_types[issue_type].append((date_val, book_id))
            
            for issue_type, items in issue_types.items():
                print(f"\n   {issue_type} ({len(items)} items):")
                for date_val, book_id in items[:10]:
                    print(f"      • {date_val}")
                if len(items) > 10:
                    print(f"      ... and {len(items) - 10} more")
    
    def analyze_urls(self):
        """Analyze URL fields for issues"""
        print("\n" + "="*80)
        print("🔗 URL ANALYSIS")
        print("="*80)
        
        urls = []
        issues = []
        
        for book_id, book in self.all_data.items():
            # Check main URL
            url = book.get('url')
            if url:
                urls.append(url)
                
                # Parse URL
                try:
                    parsed = urlparse(url)
                    if not parsed.scheme:
                        issues.append(('Missing scheme', url, book_id))
                    elif parsed.scheme not in ['http', 'https']:
                        issues.append(('Invalid scheme', url, book_id))
                    elif 'youtube.com' not in parsed.netloc and 'youtu.be' not in parsed.netloc:
                        issues.append(('Not YouTube', url, book_id))
                except Exception:
                    issues.append(('Invalid URL format', url, book_id))
            
            # Check channel URL
            channel_url = book.get('channel_url')
            if channel_url:
                try:
                    parsed = urlparse(channel_url)
                    if 'youtube.com' not in parsed.netloc:
                        issues.append(('Invalid channel URL', channel_url, book_id))
                except Exception:
                    issues.append(('Invalid channel URL format', channel_url, book_id))
        
        print(f"📊 URL Statistics:")
        print(f"   Books with URLs: {len(urls)}")
        
        if issues:
            print(f"\n⚠️  URL Issues Found ({len(issues)} total):")
            issue_types = defaultdict(list)
            for issue_type, url, book_id in issues:
                issue_types[issue_type].append((url, book_id))
            
            for issue_type, items in issue_types.items():
                print(f"\n   {issue_type} ({len(items)} items):")
                for url, book_id in items[:3]:
                    print(f"      • {url}")
                if len(items) > 3:
                    print(f"      ... and {len(items) - 3} more")
    
    def analyze_view_counts(self):
        """Analyze view and like counts for outliers"""
        print("\n" + "="*80)
        print("👀 VIEW COUNT ANALYSIS")
        print("="*80)
        
        view_counts = []
        like_counts = []
        issues = []
        
        for book_id, book in self.all_data.items():
            view_count = book.get('view_count')
            like_count = book.get('like_count')
            
            if view_count is not None:
                view_counts.append(view_count)
                
                if view_count < 0:
                    issues.append(('Negative views', str(view_count), book.get('title', 'Unknown'), book_id))
                elif view_count == 0:
                    issues.append(('Zero views', '0', book.get('title', 'Unknown'), book_id))
                elif view_count > 1000000:  # More than 1M views
                    issues.append(('Very high views', f"{view_count:,}", book.get('title', 'Unknown'), book_id))
            
            if like_count is not None:
                like_counts.append(like_count)
                
                if like_count < 0:
                    issues.append(('Negative likes', str(like_count), book.get('title', 'Unknown'), book_id))
                elif view_count and like_count > view_count:
                    issues.append(('More likes than views', f"L:{like_count} V:{view_count}", book.get('title', 'Unknown'), book_id))
        
        if view_counts:
            avg_views = statistics.mean(view_counts)
            median_views = statistics.median(view_counts)
            
            print(f"📊 View Count Statistics:")
            print(f"   Books with view counts: {len(view_counts)}")
            print(f"   Average views: {avg_views:,.0f}")
            print(f"   Median views: {median_views:,.0f}")
            print(f"   Highest views: {max(view_counts):,}")
            print(f"   Lowest views: {min(view_counts):,}")
        
        if like_counts:
            avg_likes = statistics.mean(like_counts)
            print(f"\n   Average likes: {avg_likes:,.0f}")
            print(f"   Highest likes: {max(like_counts):,}")
        
        if issues:
            print(f"\n⚠️  View/Like Issues Found ({len(issues)} total):")
            issue_types = defaultdict(list)
            for issue_type, count, title, book_id in issues:
                issue_types[issue_type].append((count, title, book_id))
            
            for issue_type, items in issue_types.items():
                print(f"\n   {issue_type} ({len(items)} items):")
                for count, title, book_id in items[:5]:
                    print(f"      • {count} - {title[:50]}")
                if len(items) > 5:
                    print(f"      ... and {len(items) - 5} more")
    
    def analyze_text_fields(self):
        """Analyze text fields for encoding and content issues"""
        print("\n" + "="*80)
        print("📝 TEXT CONTENT ANALYSIS")
        print("="*80)
        
        text_fields = ['description', 'real_synopsis', 'summary', 'transcript']
        issues = []
        
        for field in text_fields:
            field_issues = []
            lengths = []
            
            for book_id, book in self.all_data.items():
                content = book.get(field, '')
                if content:
                    lengths.append(len(content))
                    
                    # Check for issues
                    if len(content) < 10 and field in ['description', 'real_synopsis']:
                        field_issues.append(('Too short', f"{len(content)} chars", book_id))
                    elif len(content) > 10000:
                        field_issues.append(('Very long', f"{len(content)} chars", book_id))
                    elif re.search(r'[^\x00-\x7F\u00C0-\u017F\u0100-\u024F]', content):
                        field_issues.append(('Unusual characters', content[:50] + '...', book_id))
                    elif content.count('\n') > 50:
                        field_issues.append(('Too many line breaks', f"{content.count('\\n')} breaks", book_id))
            
            if lengths:
                avg_length = statistics.mean(lengths)
                print(f"\n📊 {field.upper()} field:")
                print(f"   Books with content: {len(lengths)}")
                print(f"   Average length: {avg_length:.0f} characters")
                print(f"   Longest: {max(lengths):,} characters")
                print(f"   Shortest: {min(lengths)} characters")
                
                if field_issues:
                    print(f"   ⚠️  Issues found: {len(field_issues)}")
                    issues.extend([(field, issue_type, detail, book_id) for issue_type, detail, book_id in field_issues])
        
        if issues:
            print(f"\n⚠️  Text Content Issues ({len(issues)} total):")
            by_field = defaultdict(lambda: defaultdict(list))
            for field, issue_type, detail, book_id in issues:
                by_field[field][issue_type].append((detail, book_id))
            
            for field, field_issues in by_field.items():
                print(f"\n   {field.upper()}:")
                for issue_type, items in field_issues.items():
                    print(f"      {issue_type}: {len(items)} items")
                    for detail, book_id in items[:3]:
                        print(f"         • {detail}")
                    if len(items) > 3:
                        print(f"         ... and {len(items) - 3} more")
    
    def analyze_missing_data(self):
        """Analyze patterns in missing data"""
        print("\n" + "="*80)
        print("❓ MISSING DATA ANALYSIS")
        print("="*80)
        
        important_fields = [
            'title', 'real_author', 'real_genre', 'duration', 'url', 
            'real_synopsis', 'upload_date', 'view_count'
        ]
        
        missing_stats = {}
        books_with_many_missing = []
        
        total_books = len(self.all_data)
        
        for field in important_fields:
            missing_count = 0
            for book_id, book in self.all_data.items():
                value = book.get(field)
                if value is None or (isinstance(value, str) and value.strip() == ""):
                    missing_count += 1
            
            missing_stats[field] = {
                'count': missing_count,
                'percentage': (missing_count / total_books) * 100
            }
        
        # Find books missing many important fields
        for book_id, book in self.all_data.items():
            missing_count = 0
            missing_fields = []
            
            for field in important_fields:
                value = book.get(field)
                if value is None or (isinstance(value, str) and value.strip() == ""):
                    missing_count += 1
                    missing_fields.append(field)
            
            if missing_count >= 4:  # Missing 4 or more important fields
                books_with_many_missing.append((book_id, missing_count, missing_fields, book.get('title', 'Unknown')))
        
        print(f"📊 Missing Data Summary (out of {total_books} books):")
        print(f"{'Field':<20} {'Missing':<8} {'Percentage':<12}")
        print("-" * 45)
        
        for field in important_fields:
            stats = missing_stats[field]
            print(f"{field:<20} {stats['count']:<8} {stats['percentage']:<11.1f}%")
        
        if books_with_many_missing:
            print(f"\n⚠️  Books with many missing fields ({len(books_with_many_missing)} books):")
            books_with_many_missing.sort(key=lambda x: x[1], reverse=True)
            
            for book_id, missing_count, missing_fields, title in books_with_many_missing[:10]:
                print(f"   • {title[:50]:<50} (missing {missing_count} fields)")
                print(f"     Missing: {', '.join(missing_fields[:5])}")
                if len(missing_fields) > 5:
                    print(f"     ... and {len(missing_fields) - 5} more")
                print()
    
    def run_full_investigation(self):
        """Run all analysis modules"""
        print("🔍 COMPREHENSIVE DATA QUALITY INVESTIGATION")
        print("=" * 80)
        print(f"Analysis started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        self.analyze_field_coverage()
        self.analyze_titles()
        self.analyze_authors()
        self.analyze_durations()
        self.analyze_dates()
        self.analyze_urls()
        self.analyze_view_counts()
        self.analyze_text_fields()
        self.analyze_missing_data()
        
        print("\n" + "="*80)
        print("✅ INVESTIGATION COMPLETE")
        print("="*80)
        print("💡 Review the findings above to identify data quality improvements needed.")
        print("🔧 Use the genre_manager.py tools to fix identified issues.")

def main():
    parser = argparse.ArgumentParser(description='Investigate data quality issues in audiobook collection')
    parser.add_argument('--audiobooks', '-a', default='audiobooks.json', 
                       help='Path to audiobooks.json file')
    parser.add_argument('--augmented', '-u', default='augmented.json',
                       help='Path to augmented.json file')
    parser.add_argument('--field', '-f', 
                       choices=['coverage', 'titles', 'authors', 'durations', 'dates', 'urls', 'views', 'text', 'missing'],
                       help='Analyze specific field only')
    
    args = parser.parse_args()
    
    # Create investigator
    investigator = DataInvestigator(args.audiobooks, args.augmented)
    
    # Load data
    if not investigator.load_data():
        sys.exit(1)
    
    # Run analysis
    if args.field:
        print(f"🔍 Analyzing {args.field} field only...")
        if args.field == 'coverage':
            investigator.analyze_field_coverage()
        elif args.field == 'titles':
            investigator.analyze_titles()
        elif args.field == 'authors':
            investigator.analyze_authors()
        elif args.field == 'durations':
            investigator.analyze_durations()
        elif args.field == 'dates':
            investigator.analyze_dates()
        elif args.field == 'urls':
            investigator.analyze_urls()
        elif args.field == 'views':
            investigator.analyze_view_counts()
        elif args.field == 'text':
            investigator.analyze_text_fields()
        elif args.field == 'missing':
            investigator.analyze_missing_data()
    else:
        investigator.run_full_investigation()

if __name__ == '__main__':
    main()
