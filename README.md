# Audiolibri.org

## Overview
Audiolibri.org is a curated platform that aggregates and organizes audiobooks in Italian. This project serves as a discovery engine for audiobook content, making it easy for users to find and access literary works in audio format.

## [https://audiolibri.org](https://audiolibri.org)

![screenshot](https://github.com/fabriziosalmi/audiolibri/blob/main/screenshot.png?raw=true)

## Features
- **Extensive Library**: Collection of audiobooks from various sources and narrators
- **Categorized Content**: Browse by author, genre, narrator, or popularity
- **Search Functionality**: Find specific works or authors
- **Metadata Rich**: Detailed information about each audiobook including:
  - Duration
  - Narrator/channel
  - Publication date
  - View and like statistics
  - Descriptions and transcripts where available

## Technology
This platform is built using:
- Frontend: HTML, CSS, JavaScript
- Data storage: JSON
- Deployment: GitHub Pages

## Data Processing
The platform includes several Python tools for processing audiobook data:

### Python Scripts
- `audiobook_scraper.py`: Collects metadata from audiobook sources
- `augment.py`: Enhances audiobook entries with additional metadata using LLM
- `stats.py`: Generates usage statistics and analytics
- Other utilities: `author_cleaner.py`, `genre_manager.py`, `title_cleaner_v2.py`

### Python Environment Setup

It's recommended to use a virtual environment to manage dependencies:

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Environment Variables

The Python scripts support configuration via environment variables:

**audiobook_scraper.py:**
- `AUDIOBOOKS_OUTPUT_DIR`: Output directory for audiobooks data (default: current directory)
- `MAX_WORKERS`: Number of concurrent workers for scraping (default: 5)
- `RATE_LIMIT`: Rate limit for API requests in seconds (default: 0.5)

**augment.py:**
- `LLM_API_URL`: URL for LLM API endpoint (default: http://localhost:1234/v1/chat/completions)

Example:
```bash
export LLM_API_URL="http://localhost:1234/v1/chat/completions"
export MAX_WORKERS=10
python augment.py
```

## Contributing
Contributions to improve the platform are welcome. Please feel free to:
- Report bugs or issues
- Suggest new audiobooks to be included
- Contribute to code improvements

## License
This project is available under Creative Commons 1.0 License. Content rights belong to their respective owners.

## Acknowledgments
Thanks to all the narrators and creators who make literary works accessible in audio format.

## Visit
[https://audiolibri.org](https://audiolibri.org)
