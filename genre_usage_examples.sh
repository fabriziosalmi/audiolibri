#!/bin/bash
# Example script showing how to use the genre manager

echo "=== Genre Manager Usage Examples ==="
echo

echo "1. Basic analysis:"
echo "python3 genre_manager.py --analyze"
echo

echo "2. Find problematic genres:"
echo "python3 genre_manager.py --problems"
echo

echo "3. Get consolidation suggestions:"
echo "python3 genre_manager.py --suggestions"
echo

echo "4. Interactive mode for fixing genres:"
echo "python3 genre_manager.py --interactive"
echo

echo "=== Interactive Commands ==="
echo "Once in interactive mode, you can use:"
echo "  list                    - Show all genres"
echo "  list real_genre         - Show genres from real_genre field"
echo "  count romanzo           - Count books with 'romanzo' genre"
echo "  find *riccard*          - Find genres matching pattern"
echo "  replace 'Riccardo' 'racconto' real_genre  - Replace genre"
echo "  help                    - Show all commands"
echo "  quit                    - Exit"
echo

echo "=== Common Fixes Based on Analysis ==="
echo
echo "Issues found that could be fixed:"
echo "• 'Riccardo' (5 books) - likely should be 'racconto'"
echo "• 'Riccone' (1 book) - likely should be 'racconto'"  
echo "• 'Ricciardo' (1 book) - likely should be 'racconto'"
echo "• 'fantasy' (1 book) - could be merged with 'fantascienza'"
echo "• 'novella' (3 books) - could be merged with 'romanzo'"
echo "• 'thriller' (2 books) - could be merged with 'horror' or 'giallo'"
echo
echo "Example fix commands:"
echo "  replace 'Riccardo' 'racconto' real_genre"
echo "  replace 'Riccone' 'racconto' real_genre"
echo "  replace 'Ricciardo' 'racconto' real_genre"
echo "  replace 'novella' 'romanzo' real_genre"
echo

echo "Run the script interactively to make these changes!"
