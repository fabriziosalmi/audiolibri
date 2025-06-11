# Author Name Standardizer

## Overview

The `author_name_standardizer.py` script standardizes author names across the audiobook collection to achieve consistent "Name Surname" formatting throughout the database.

## What It Fixes

### 1. ALL CAPS Names
Converts authors in all uppercase to proper case:
- `H. HESSE` → `Hermann Hesse`
- `G. GOZZANO` → `G. Gozzano`
- `K. GIBRAN` → `K. Gibran`

### 2. Initial Expansions
Expands known author initials to full names:
- `F. Dostoevsky` → `Fëdor Dostoevskij`
- `A. Cechov` → `Anton Čechov`
- `N. Gogol` → `Nikolaj Gogol`
- `H. Hesse` → `Hermann Hesse`
- `O. Wilde` → `Oscar Wilde`

### 3. Case Inconsistencies
Standardizes capitalization:
- `autore sconosciuto` → `Autore Sconosciuto`
- `anonimo` → `Anonimo`

### 4. Format Consistency
Ensures consistent spacing and formatting throughout.

## Usage

### Run the Script
```bash
python3 author_name_standardizer.py
```

### What Happens
1. **Analysis**: The script analyzes all author names and shows a preview of changes
2. **Confirmation**: Asks for user confirmation before making changes
3. **Backup**: Creates a timestamped backup file automatically
4. **Processing**: Applies all standardizations to the data
5. **Summary**: Shows detailed statistics of changes made

### Safety Features
- **Automatic Backup**: Creates `augmented.json.backup_authors_TIMESTAMP` before any changes
- **Preview Mode**: Shows exactly what will be changed before applying
- **User Confirmation**: Requires explicit confirmation before proceeding
- **Rollback Support**: Original data can be restored from backup if needed

## Results

After running the enhanced standardizer on the audiobook collection:

- **Total Changes**: 136 author name standardizations (across multiple runs)
- **Duplicate Reduction**: 33 fewer duplicate author entries  
- **Books Affected**: All books with inconsistent author names
- **Final Unique Authors**: 409 properly formatted authors
- **N. Surname Patterns**: 0 remaining (all expanded to full names)

### Final Author Format Distribution
- **Full Names (3+ words)**: 100 authors (e.g., "Johann Wolfgang von Goethe")
- **Two Names (Name Surname)**: 263 authors (e.g., "Charles Dickens") 
- **Standard Initials**: 13 authors (e.g., "H.P. Lovecraft", "T.S. Eliot")
- **Institutional/Other**: 33 authors (e.g., "Autore Sconosciuto")

### Top Authors (After Complete Standardization)
1. A. L. Knorr: 236 books
2. Georges Simenon: 153 books  
3. Guy de Maupassant: 141 books
4. Fëdor Dostoevskij: 56 books
5. Carlo Collodi: 41 books

## Verification

Use the verification script to check results:
```bash
python3 verify_author_standardization.py
```

This shows:
- Before/after comparison
- Change statistics by type
- Remaining issues (if any)
- Top authors after standardization

## Technical Details

### Supported Name Expansions
The script includes expansions for over 60 well-known authors across multiple languages:

- **English/American**: Shakespeare, Hemingway, Steinbeck, Austen, Dickens, London, Carver, Irving
- **Russian**: Dostoevsky, Tolstoy, Chekhov, Pushkin, Gogol, Esenin  
- **Italian**: Boccaccio, Manzoni, Leopardi, Verga, Calvino, Pirandello, Buzzati, Pavese
- **French**: Hugo, Proust, Camus, Flaubert, Verne, Zola, Leblanc
- **German**: Hesse, Kafka, Mann, Grass, Nietzsche, Rilke
- **Portuguese**: Pessoa, Saramago
- **Spanish**: Borges (Jorge Luis Borges)
- **Other**: Gibran, Zweig, Celan, Deledda, and many more

### Edge Cases Handled
- Preserves well-known abbreviated forms (H.P. Lovecraft, G.K. Chesterton)
- Handles special characters and diacritics correctly
- Maintains spacing consistency
- Respects existing proper formatting

## Files Created

- `author_name_standardizer.py` - Main standardization script
- `verify_author_standardization.py` - Verification and comparison script
- `augmented.json.backup_authors_TIMESTAMP` - Automatic backup (created when run)

## Integration

This script complements the existing data quality tools:
- `author_cleaner.py` - Manual author fixes and duplicate detection
- `title_cleaner_v2.py` - Title standardization
- `data_investigator.py` - Data quality analysis

## Best Practices

1. **Always run verification** after standardization
2. **Keep backups** for important changes
3. **Run periodically** as new data is added
4. **Review expansions** and add new authors as needed
5. **Test changes** on a small dataset first when modifying the script
