// app.js
let player;

document.addEventListener('DOMContentLoaded', () => {
    // Configuration options
    const config = {
        enableChangelog: true,  // Set to false to disable the changelog feature
        changelogPath: 'changelog.json',
        maxChangelogEntries: 3
    };

    let audiobooks = [];
    let currentBook = null;
    let previousBooks = []; // Keep track of book history
    let youtubePlayer = null;
    let playerState = {
        currentTime: 0,
        duration: 0,
        isPlaying: false,
        volume: 100
    };
    let updateInterval;
    let prefersDarkMode = window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    // Show loading state immediately
    document.getElementById('current-audiobook').innerHTML = `
        <div class="loading-container slide-up">
            <div class="loading-spinner"></div>
            <p>Loading your audiobook library...</p>
            <small>Please wait while we prepare your collection</small>
        </div>
    `;
    
    // Theme toggle functionality
    const themeToggle = document.getElementById('theme-toggle');
    const themeLabel = document.getElementById('theme-label');
    themeToggle.addEventListener('click', toggleTheme);
    
    // Set up search functionality
    const searchInput = document.getElementById('search');
    const searchButton = document.getElementById('search-button');
    
    // Add event listeners for search
    searchButton.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            performSearch();
        }
    });
    
    function toggleTheme() {
        if (prefersDarkMode) {
            document.documentElement.style.setProperty('--background-color', '#f5f7fa');
            document.documentElement.style.setProperty('--text-color', '#2d3748');
            document.documentElement.style.setProperty('--card-background', '#ffffff');
            document.documentElement.style.setProperty('--card-shadow', '0 10px 25px rgba(0,0,0,0.05)');
            document.documentElement.style.setProperty('--border-color', '#e2e8f0');
            document.documentElement.style.setProperty('--header-color', '#1e293b');
            document.documentElement.style.setProperty('--secondary-text', '#64748b');
            document.documentElement.style.setProperty('--placeholder-bg', '#f8fafc');
            document.documentElement.style.setProperty('--search-border', '#cbd5e1');
            document.documentElement.style.setProperty('--primary-rgb', '74, 108, 247');
            document.documentElement.style.setProperty('--accent-rgb', '16, 185, 129');
            document.documentElement.style.setProperty('--card-background-rgb', '255, 255, 255');
            prefersDarkMode = false;
        } else {
            document.documentElement.style.setProperty('--background-color', '#000000');
            document.documentElement.style.setProperty('--text-color', '#e2e8f0');
            document.documentElement.style.setProperty('--card-background', '#121212');
            document.documentElement.style.setProperty('--card-shadow', '0 10px 25px rgba(0,0,0,0.4)');
            document.documentElement.style.setProperty('--border-color', '#2a2a2a');
            document.documentElement.style.setProperty('--header-color', '#ffffff');
            document.documentElement.style.setProperty('--secondary-text', '#a0a0a0');
            document.documentElement.style.setProperty('--placeholder-bg', '#1e1e1e');
            document.documentElement.style.setProperty('--search-border', '#333333');
            document.documentElement.style.setProperty('--primary-rgb', '252, 134, 134');
            document.documentElement.style.setProperty('--accent-rgb', '3, 218, 198');
            document.documentElement.style.setProperty('--card-background-rgb', '18, 18, 18');
            prefersDarkMode = true;
        }
        themeLabel.textContent = prefersDarkMode ? 'Tema chiaro' : 'Tema scuro';
    }
    
    // Initialize theme toggle text
    themeLabel.textContent = prefersDarkMode ? 'Tema chiaro' : 'Tema scuro';
    
    // Load the audiobook data from augmented.json
    fetch('augmented.json')
        .then(response => response.json())
        .then(data => {
            // Convert the JSON object to an array of audiobooks
            audiobooks = Object.entries(data).map(([id, book]) => {
                return {
                    id: id,
                    title: book.real_title || book.title || 'Unknown Title',
                    author: book.real_author || 'Unknown Author',
                    description: book.real_synopsis || book.description || 'No description available.',
                    genre: book.real_genre || '',  // Add the genre from augmented data
                    coverImage: book.thumbnail || 'https://via.placeholder.com/400x225?text=No+Cover+Available',
                    audioUrl: book.audio_file || '',
                    duration: book.duration || 0,
                    formattedDuration: formatDuration(book.duration || 0),
                    url: book.url || '',
                    channel: book.channel || '',
                    channelUrl: book.channel_url || '',
                    videoId: extractVideoId(book.url || ''),
                    categories: book.real_genre ? [book.real_genre] : (book.categories || []),  // Use genre as category if available
                    tags: book.tags || [],
                    uploadDate: book.upload_date || ''
                };
            }).filter(book => book.title !== 'Unknown Title' && book.videoId); // Filter out entries without titles and video IDs
            
            // Calculate and display library statistics
            updateLibraryStats(audiobooks);
            
            if (audiobooks.length > 0) {
                // Small delay to show the loading state
                setTimeout(() => {
                    // Select a random book as the initial book
                    const randomIndex = Math.floor(Math.random() * audiobooks.length);
                    currentBook = audiobooks[randomIndex];
                    displayBook(currentBook);
                }, 500);
            } else {
                document.getElementById('current-audiobook').innerHTML = 
                    `<div class="error-message">
                        <div class="error-icon">!</div>
                        <p>No audiobooks found in the library.</p>
                        <small>Please check your data source and try again.</small>
                    </div>`;
            }
        })
        .catch(error => {
            console.error('Error loading audiobooks:', error);
            document.getElementById('current-audiobook').innerHTML = 
                `<div class="error-message">
                    <div class="error-icon">!</div>
                    <p>Error loading audiobooks library.</p>
                    <small>Please check your connection and try again later.</small>
                </div>`;
        });
        
    // Function to calculate and display library stats
    function updateLibraryStats(books) {
        // Calculate statistics
        const totalBooks = books.length;
        
        // Get unique channels
        const uniqueChannels = new Set();
        books.forEach(book => {
            if (book.channel) {
                uniqueChannels.add(book.channel);
            }
        });
        const totalChannels = uniqueChannels.size;
        
        // Get unique authors
        const uniqueAuthors = new Set();
        books.forEach(book => {
            if (book.author && book.author !== 'Unknown Author') {
                uniqueAuthors.add(book.author);
            }
        });
        const totalAuthors = uniqueAuthors.size;
        
        // Calculate total duration of all books
        let totalDurationInSeconds = 0;
        books.forEach(book => {
            if (book.duration) {
                totalDurationInSeconds += book.duration;
            }
        });
        
        // Convert to days, hours, minutes
        const totalDays = Math.floor(totalDurationInSeconds / 86400);
        const totalHours = Math.floor((totalDurationInSeconds % 86400) / 3600);
        const totalFormattedDuration = `${totalDays} giorni, ${totalHours} ore`;
        
        // Update UI
        const libraryStatsContainer = document.getElementById('library-stats');
        if (libraryStatsContainer) {
            libraryStatsContainer.innerHTML = `
                <div class="stat-item">
                    <div class="stat-value">${totalBooks.toLocaleString()}</div>
                    <div class="stat-label">Audiolibri</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${totalAuthors.toLocaleString()}</div>
                    <div class="stat-label">Autori</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${totalChannels.toLocaleString()}</div>
                    <div class="stat-label">Canali</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${totalFormattedDuration}</div>
                    <div class="stat-label">Durata complessiva</div>
                </div>
            `;
        }
        
        // Generate and display genre navigation list
        generateGenreNavigation(books);
    }

    // Helper function to uppercase categories/genres
    function capitalizeCategory(category) {
        if (!category) return '';
        
        // Simply return the category in uppercase
        return category.toUpperCase();
    }

    // Function to generate genre navigation
    function generateGenreNavigation(books) {
        // Count the number of books in each genre
        const genreCounts = books.reduce((acc, book) => {
            if (book.genre) {
                acc[book.genre] = (acc[book.genre] || 0) + 1;
            }
            return acc;
        }, {});

        // Filter genres with at least 10 items
        const filteredGenres = Object.keys(genreCounts).filter(genre => genreCounts[genre] >= 10);

        // First, create or check for the genre navigation container
        let genreNavContainer = document.getElementById('genre-navigation');
        if (!genreNavContainer) {
            // Create the container if it doesn't exist
            const searchContainer = document.querySelector('.search-container');
            genreNavContainer = document.createElement('div');
            genreNavContainer.id = 'genre-navigation';
            genreNavContainer.className = 'genre-navigation fade-in';

            // Insert after the search container
            if (searchContainer && searchContainer.parentNode) {
                searchContainer.parentNode.insertBefore(genreNavContainer, searchContainer.nextSibling);
            } else {
                // Fallback to inserting before the current audiobook element
                const currentAudiobook = document.getElementById('current-audiobook');
                if (currentAudiobook && currentAudiobook.parentNode) {
                    currentAudiobook.parentNode.insertBefore(genreNavContainer, currentAudiobook);
                }
            }
        }

        // Clear existing content
        genreNavContainer.innerHTML = '';
        
        if (filteredGenres.length === 0) {
            genreNavContainer.style.display = 'none';
            return;
        }

        // Add title and list container
        genreNavContainer.innerHTML = `
            <div class="genre-list" role="list" aria-label="Generi disponibili">
            </div>
        `;
        
        const genreList = genreNavContainer.querySelector('.genre-list');

        // Generate navigation for filtered genres
        filteredGenres.forEach(genre => {
            const genrePill = document.createElement('button');
            genrePill.className = 'genre-pill';
            genrePill.dataset.genre = genre;
            genrePill.setAttribute('role', 'listitem');
            genrePill.innerHTML = `
                <span class="genre-name">${capitalizeCategory(genre)}</span>
                <span class="genre-count" aria-label="${genreCounts[genre]} audiolibri">${genreCounts[genre]}</span>
            `;
            
            // Add click event listener
            genrePill.addEventListener('click', function() {
                showGenreView(genre);
            });
            
            genreList.appendChild(genrePill);
        });
        
        // Add CSS styles for genre navigation
        addGenreNavigationStyles();
    }

    // Add CSS styles for genre navigation
    function addGenreNavigationStyles() {
        // Check if styles are already added
        if (document.getElementById('genre-nav-styles')) return;
        
        const styleElement = document.createElement('style');
        styleElement.id = 'genre-nav-styles';
        styleElement.textContent = `
            .genre-navigation {
                margin: 20px 0;
                padding: 1.5rem;
                background: #12121200;
                border-radius: 16px;
                box-shadow: none;
                border: 0px solid var(--border-color);
                transition: all 0.3s ease;
            }
            
            .genre-title {
                font-size: 1.25rem;
                margin-bottom: 1.25rem;
                color: var(--header-color);
                font-weight: 600;
                position: relative;
                padding-bottom: 0.75rem;
            }
            
            .genre-title::after {
                content: '';
                position: absolute;
                bottom: 0;
                left: 0;
                width: 50px;
                height: 3px;
                background: var(--primary-color);
                border-radius: 3px;
            }
            
            .genre-list {
                display: flex;
                flex-wrap: wrap;
                gap: 12px;
                align-items: center;
            }
            
            .genre-pill {
                display: flex;
                align-items: center;
                padding: 10px 16px;
                border-radius: 12px;
                background: rgba(var(--primary-rgb), 0.1);
                border: 1px solid rgba(var(--primary-rgb), 0.2);
                color: var(--primary-color);
                font-size: 1rem;
                font-weight: lighter;
                cursor: pointer;
                transition: all 0.25s ease;
                white-space: nowrap;
                box-shadow: 0 2px 5px rgba(0,0,0,0.05);
                position: relative;
                overflow: hidden;
            }
            
            .genre-pill:hover {
                background: rgba(var(--primary-rgb), 0.15);
                transform: translateY(-3px);
                box-shadow: 0 5px 10px rgba(0,0,0,0.1);
            }
            
            .genre-pill:active {
                transform: translateY(-1px);
            }
            
            .genre-count {
                margin-left: 8px;
                background: rgba(var(--primary-rgb), 0.2);
                border-radius: 12px;
                padding: 3px 10px;
                font-size: 0.8rem;
                font-weight: 600;
            }
            
            .genre-pill.selected {
                background: var(--primary-color);
                color: white;
                border-color: var(--primary-color);
                box-shadow: 0 4px 12px rgba(var(--primary-rgb), 0.3);
            }
            
            .genre-pill.selected .genre-count {
                background: rgba(255, 255, 255, 0.25);
                color: white;
            }
            
            /* Genre View Styles */
            .genre-view {
                padding: 1.5rem;
            }
            
            .genre-view-header {
                display: flex;
                align-items: center;
                margin-bottom: 1.5rem;
                flex-wrap: wrap;
                gap: 12px;
            }
            
            .genre-view-title {
                font-size: 1.5rem;
                color: white;
                margin: 0;
                text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
            }
            
            .genre-count-large {
                margin-left: auto;
                background: rgba(255,255,255,0.2);
                color: white;
                padding: 5px 12px;
                border-radius: 999px;
                font-size: 0.9rem;
            }
            
            .back-button {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 8px 16px;
                background: rgba(0,0,0,0.4);
                border-radius: 999px;
                color: white;
                border: 1px solid rgba(255,255,255,0.2);
                font-size: 0.9rem;
                cursor: pointer;
                transition: all 0.2s ease;
            }
            
            .back-button:hover {
                background: rgba(0,0,0,0.6);
                box-shadow: 0 3px 8px rgba(0,0,0,0.3);
            }
            
            .back-icon::before {
                content: "←";
                margin-right: 4px;
            }
            
            .audiobooks-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
                gap: 20px;
            }
            
            .book-card {
                background: var(--card-background);
                border-radius: 12px;
                overflow: hidden;
                cursor: pointer;
                transition: transform 0.3s ease, box-shadow 0.3s ease;
                box-shadow: var(--card-shadow);
                border: 1px solid var(--border-color);
                height: 100%;
                display: flex;
                flex-direction: column;
            }
            
            .book-card:hover {
                transform: translateY(-5px);
                box-shadow: 0 12px 20px rgba(0,0,0,0.15);
            }
            
            .book-card-cover {
                height: 160px;
                background-size: cover;
                background-position: center;
                position: relative;
            }
            
            .card-badge {
                position: absolute;
                padding: 4px 10px;
                border-radius: 999px;
                font-size: 0.7rem;
                font-weight: 600;
                color: white;
            }
            
            .audio-badge {
                top: 10px;
                left: 10px;
                background: var(--accent-color);
            }
            
            .duration-badge {
                bottom: 10px;
                right: 10px;
                background: rgba(0,0,0,0.7);
            }
            
            .book-card-details {
                padding: 15px;
                flex: 1;
                display: flex;
                flex-direction: column;
            }
            
            .book-card-title {
                margin: 0 0 8px 0;
                font-size: 0.95rem;
                color: var(--text-color);
                line-height: 1.3;
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
            }
            
            .book-card-author {
                margin: 0;
                font-size: 0.85rem;
                color: var(--secondary-text);
                font-weight: 500;
            }
            
            @media (max-width: 768px) {
                .genre-navigation {
                    padding: 1.25rem;
                }
                
                .genre-pill {
                    padding: 8px 14px;
                    font-size: 0.85rem;
                }
                
                .audiobooks-grid {
                    grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
                    gap: 15px;
                }
                
                .genre-view {
                    padding: 1rem;
                }
                
                .genre-view-header {
                    margin-bottom: 1rem;
                }
                
                .genre-view-title {
                    font-size: 1.25rem;
                }
            }
        `;
        
        document.head.appendChild(styleElement);
    }
    
    // Add specific styles for genre pills to remove borders
    function updateGenrePillStyles() {
        // Check if the styles already exist
        if (document.getElementById('genre-pill-border-fix')) return;
        
        const styleElement = document.createElement('style');
        styleElement.id = 'genre-pill-border-fix';
        styleElement.textContent = `
            .genre-pill {
                border: none !important;
                box-shadow: 0 3px 8px rgba(var(--primary-rgb), 0.15);
            }
            
            .genre-pill:hover {
                box-shadow: 0 5px 12px rgba(var(--primary-rgb), 0.25);
            }
            
            .genre-pill.selected {
                box-shadow: 0 4px 12px rgba(var(--primary-rgb), 0.4);
            }
        `;
        
        document.head.appendChild(styleElement);
    }
    
    // Count how many books are in a specific genre
    function countBooksInGenre(books, genre) {
        return books.filter(book => 
            (book.categories && book.categories.includes(genre)) ||
            book.genre === genre
        ).length;
    }
    
    // Display the genre view showing all books in a selected genre
    function showGenreView(genre) {
        // Clear previous selected state
        document.querySelectorAll('.genre-pill').forEach(pill => {
            pill.classList.remove('selected');
        });
        
        // Add selected state to current genre pill
        const selectedPill = document.querySelector(`.genre-pill[data-genre="${genre}"]`);
        if (selectedPill) {
            selectedPill.classList.add('selected');
        }
        
        // Filter books by the selected genre
        const filteredBooks = audiobooks.filter(book => 
            (book.categories && book.categories.includes(genre)) ||
            book.genre === genre
        );
        
        // Show loading state
        document.getElementById('current-audiobook').innerHTML = `
            <div class="loading-container slide-up">
                <div class="loading-spinner"></div>
                <p>Loading "${capitalizeCategory(genre)}" audiobooks...</p>
                <small>Preparing your filtered collection</small>
            </div>
        `;
        
        // Clear previous player interval if exists
        if (updateInterval) clearInterval(updateInterval);
        
        setTimeout(() => {
            if (filteredBooks.length > 0) {
                // Select the first book from the filtered collection
                if (currentBook) {
                    previousBooks.push(currentBook);
                }
                currentBook = filteredBooks[0];
                
                // Display the regular book view first
                displayBook(currentBook);
                
                // Then display genre books grid in a separate card
                displayGenreBooksGrid(genre, filteredBooks);
            } else {
                document.getElementById('current-audiobook').innerHTML = `
                    <div class="no-results fade-in">
                        <i class="search-icon"></i>
                        <h3>No audiobooks found</h3>
                        <p>We couldn't find any audiobooks in the "${genre}" category</p>
                        <button class="back-button" id="empty-back-button">Back to main view</button>
                    </div>`;
                
                document.getElementById('empty-back-button').addEventListener('click', () => {
                    displayBook(currentBook);
                });
            }
        }, 500);
    }

    // New function to display genre books in a grid view card
    function displayGenreBooksGrid(genre, genreBooks) {
        // Remove any existing genre grid card first
        const existingCard = document.getElementById('genre-books-grid-card');
        if (existingCard) {
            existingCard.remove();
        }
        
        // Create a new card for the genre books grid
        const genreGridCard = document.createElement('div');
        genreGridCard.id = 'genre-books-grid-card';
        genreGridCard.className = 'genre-books-grid-card fade-in';
        
        // Create header with genre info and navigation (without close button)
        const genreHeader = `
            <div class="genre-grid-header">
                <div class="genre-grid-title-area">
                    <h3 class="genre-grid-title">${capitalizeCategory(genre)}</h3>
                    <span class="genre-count-badge">${genreBooks.length} audiolibri</span>
                </div>
            </div>
        `;
        
        // Create grid of book cards with scroll buttons
        let booksGrid = `
            <div class="books-grid-container">
                <button class="scroll-button scroll-left" id="scroll-left" aria-label="Scroll left">
                    <i class="arrow-left-icon">←</i>
                </button>
                <div class="books-grid" id="books-grid">`;
        
        genreBooks.forEach((book, index) => {
            booksGrid += `
                <div class="book-grid-item" data-index="${index}">
                    <div class="book-grid-cover" style="background-image: url('${book.coverImage}')">
                        <span class="book-grid-duration">${book.formattedDuration}</span>
                    </div>
                    <div class="book-grid-details">
                        <h4 class="book-grid-title">${book.title}</h4>
                        <p class="book-grid-author">${book.author}</p>
                    </div>
                </div>
            `;
        });
        
        booksGrid += `
                </div>
                <button class="scroll-button scroll-right" id="scroll-right" aria-label="Scroll right">
                    <i class="arrow-right-icon">→</i>
                </button>
            </div>
        `;
        
        // Combine header and grid
        genreGridCard.innerHTML = genreHeader + booksGrid;
        
        // Insert the new card BEFORE the current audiobook card
        const currentAudiobookCard = document.getElementById('current-audiobook');
        currentAudiobookCard.parentNode.insertBefore(genreGridCard, currentAudiobookCard);
        
        // Add event listeners for book selection
        document.querySelectorAll('.book-grid-item').forEach(item => {
            item.addEventListener('click', function() {
                const index = parseInt(this.dataset.index);
                if (!isNaN(index) && index >= 0 && index < genreBooks.length) {
                    currentBook = genreBooks[index];
                    displayBook(currentBook);
                    
                    // No need to scroll now that the player is below the grid
                    // Just update the active state in the grid
                    document.querySelectorAll('.book-grid-item').forEach(gridItem => {
                        gridItem.classList.remove('active');
                    });
                    this.classList.add('active');
                }
            });
        });
        
        // Add scroll button functionality
        const scrollLeftButton = document.getElementById('scroll-left');
        const scrollRightButton = document.getElementById('scroll-right');
        const booksGridElement = document.getElementById('books-grid');
        
        // Initially check if scrolling is needed and hide buttons if not
        setTimeout(() => {
            updateScrollButtonsVisibility(booksGridElement, scrollLeftButton, scrollRightButton);
        }, 100);
        
        scrollLeftButton.addEventListener('click', () => {
            // Scroll left by a specific amount (3 items)
            const itemWidth = booksGridElement.querySelector('.book-grid-item').offsetWidth + 20; // width + margin
            booksGridElement.scrollBy({ left: -itemWidth * 3, behavior: 'smooth' });
        });
        
        scrollRightButton.addEventListener('click', () => {
            // Scroll right by a specific amount (3 items)
            const itemWidth = booksGridElement.querySelector('.book-grid-item').offsetWidth + 20; // width + margin
            booksGridElement.scrollBy({ left: itemWidth * 3, behavior: 'smooth' });
        });
        
        // Update button visibility on scroll
        booksGridElement.addEventListener('scroll', () => {
            updateScrollButtonsVisibility(booksGridElement, scrollLeftButton, scrollRightButton);
        });
        
        // Add CSS styles for the grid card
        addGenreGridStyles();
    }
    
    // Helper function to update scroll button visibility
    function updateScrollButtonsVisibility(scrollContainer, leftButton, rightButton) {
        // Show/hide left button based on scroll position
        if (scrollContainer.scrollLeft <= 20) {
            leftButton.classList.add('hidden');
        } else {
            leftButton.classList.remove('hidden');
        }
        
        // Show/hide right button based on whether there's more content to scroll
        const maxScrollLeft = scrollContainer.scrollWidth - scrollContainer.clientWidth - 20;
        if (scrollContainer.scrollLeft >= maxScrollLeft) {
            rightButton.classList.add('hidden');
        } else {
            rightButton.classList.remove('hidden');
        }
    }
    
    // Add styles for the genre grid card
    function addGenreGridStyles() {
        // Check if styles already exist
        if (document.getElementById('genre-grid-styles')) return;
        
        const styleElement = document.createElement('style');
        styleElement.id = 'genre-grid-styles';
        styleElement.textContent = `
            .genre-books-grid-card {
                background: var(--card-background);
                border-radius:
                0px;
                padding:
                1.5rem;
                margin-bottom: 1.2rem;
                box-shadow: none;
                border: 0px solid var(--border-color);
                transition:
                all 0.3s ease;
            }
            
            .genre-grid-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 1.5rem;
            }
            
            .genre-grid-title-area {
                display: flex;
                align-items: center;
                gap: 12px;
                flex-wrap: wrap;
            }
            
            .genre-grid-title {
                font-size: 1.5rem;
                margin: 0;
                color: var(--header-color);
            }
            
            .genre-count-badge {
                background: rgba(var(--primary-rgb), 0.1);
                color: var(--primary-color);
                padding: 5px 12px;
                border-radius: 999px;
                font-size: 0.85rem;
                font-weight: 500;
            }
            
            /* Horizontal scrolling container */
            .books-grid-container {
                position: relative;
                display: flex;
                align-items: center;
                width: 100%;
            }
            
            .books-grid {
                display: flex;
                flex-wrap: nowrap;
                overflow-x: auto;
                scroll-behavior: smooth;
                -webkit-overflow-scrolling: touch;
                padding: 10px 0;
                gap: 16px;
                scrollbar-width: none; /* Firefox */
                -ms-overflow-style: none; /* IE and Edge */
            }
            
            /* Hide scrollbar for Chrome, Safari and Opera */
            .books-grid::-webkit-scrollbar {
                display: none;
            }
            
            /* Scroll buttons */
            .scroll-button {
                position: absolute;
                z-index: 10;
                width: 40px;
                height: 40px;
                border-radius: 50%;
                background: var(--card-background);
                color: var(--primary-color);
                border: 1px solid rgba(var(--primary-rgb), 0.3);
                box-shadow: 0 4px 12px rgba(0,0,0,0.15);
                display: flex;
                align-items: center;
                justify-content: center;
                cursor: pointer;
                transition: all 0.2s ease;
                opacity: 0.9;
            }
            
            .scroll-button:hover {
                background: rgba(var(--primary-rgb), 0.1);
                transform: scale(1.1);
                opacity: 1;
            }
            
            .scroll-button.hidden {
                opacity: 0;
                visibility: hidden;
                transform: scale(0.8);
            }
            
            .scroll-left {
                left: -10px;
            }
            
            .scroll-right {
                right: -10px;
            }
            
            .arrow-left-icon, .arrow-right-icon {
                font-size: 1.2rem;
                font-weight: 700;
            }
            
            .book-grid-item {
                flex: 0 0 180px;
                background: rgba(var(--card-background-rgb), 0.5);
                border: 1px solid var(--border-color);
                border-radius: 12px;
                overflow: hidden;
                cursor: pointer;
                transition: all 0.3s ease;
                height: 100%;
                display: flex;
                flex-direction: column;
            }
            
            .book-grid-item:hover {
                transform: translateY(-8px);
                box-shadow: 0 12px 20px rgba(0,0,0,0.1);
            }
            
            .book-grid-cover {
                height: 120px;
                background-size: cover;
                background-position: center;
                position: relative;
            }
            
            .book-grid-duration {
                position: absolute;
                bottom: 8px;
                right: 8px;
                background: rgba(0,0,0,0.75);
                color: white;
                padding: 3px 8px;
                border-radius: 4px;
                font-size: 0.75rem;
            }
            
            .book-grid-details {
                padding: 12px;
                flex: 1;
                display: flex;
                flex-direction: column;
            }
            
            .book-grid-title {
                margin: 0 0 6px 0;
                font-size: 0.95rem;
                font-weight: 600;
                color: var(--text-color);
                display: -webkit-box;
                -webkit-line-clamp: 2;
                -webkit-box-orient: vertical;
                overflow: hidden;
                line-height: 1.3;
            }
            
            .book-grid-author {
                margin: 0;
                font-size: 0.8rem;
                color: var(--secondary-text);
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            
            /* Animation classes */
            .fade-in {
                animation: fadeIn 0.4s ease forwards;
            }
            
            .fade-out {
                animation: fadeOut 0.3s ease forwards;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            @keyframes fadeOut {
                from { opacity: 1; transform: translateY(0); }
                to { opacity: 0; transform: translateY(10px); }
            }
            
            @media (max-width: 768px) {
                .genre-books-grid-card {
                    padding: 1rem;
                    margin: 1rem 0;
                }
                
                .genre-grid-title {
                    font-size: 1.25rem;
                }
                
                .book-grid-item {
                    flex: 0 0 140px;
                }
                
                .book-grid-cover {
                    height: 100px;
                }
                
                .scroll-button {
                    width: 36px;
                    height: 36px;
                }
                
                .arrow-left-icon, .arrow-right-icon {
                    font-size: 1rem;
                }
            }
        `;
        
        document.head.appendChild(styleElement);
    }

    function resetPlayerState() {
        playerState = {
            currentTime: 0,
            duration: 0,
            isPlaying: false,
            volume: 100
        };
    }
    
    function displayBook(book) {
        const bookCard = document.getElementById('current-audiobook');
        
        // Set background image with a gradient overlay
        bookCard.style.backgroundImage = `url('${book.coverImage}')`;
        
        // Check if audio file is available
        const audioAvailable = book.audioUrl ? true : false;
        const audioStatus = audioAvailable ? 
            `<span class="audio-status available"><i class="audio-icon"></i>Audio available</span>` : 
            ``;
        
        // Create trimmed description (max 300 characters)
        const trimmedDescription = book.description.length > 300 
            ? book.description.substring(0, 300) + '...' 
            : book.description;
        
        // Create channel link with icon
        const channelHtml = book.channelUrl 
            ? `<a href="${book.channelUrl}" target="_blank" rel="noopener" class="channel-link">
                <img src="https://www.youtube.com/s/desktop/7c155e84/img/favicon_144x144.png" alt="YouTube" class="channel-icon">
                ${book.channel || 'YouTube Channel'}
              </a>` 
            : `${book.channel || ''}`;
            
        // Format upload date if available
        const uploadDate = book.uploadDate ? 
            formatUploadDate(book.uploadDate) : '';
            
        // Create category tags
        let categoriesHtml = '';
        if (book.categories && book.categories.length > 0) {
            categoriesHtml = `
            <div class="book-categories">
                ${book.categories.map(category => 
                    `<span class="category-tag">${capitalizeCategory(category)}</span>`
                ).join('')}
            </div>`;
        }
        
        // Format duration as a styled element
        const durationHtml = `<span class="duration-badge"><i class="time-icon"></i>${book.formattedDuration}</span>`;
        
        // Improved layout with better player interface
        bookCard.innerHTML = `
            <div class="card-overlay">
                <div class="media-container slide-up">
                    <div id="youtube-player"></div>
                    <audio id="audio-player" controls></audio>
                    <div class="player-controls">
                        <div class="controls-row">
                            <button id="rewind-button" class="control-button" aria-label="Rewind 10 seconds">
                                <i class="rewind-icon"></i>
                            </button>
                            <button id="play-pause" class="control-button large" aria-label="Play/Pause">
                                <i class="play-icon"></i>
                            </button>
                            <button id="forward-button" class="control-button" aria-label="Forward 10 seconds">
                                <i class="forward-icon"></i>
                            </button>
                        </div>
                        <div class="progress-container" id="progress-container">
                            <div class="progress-bar" id="progress-bar"></div>
                            <div class="progress-handle" id="progress-handle"></div>
                        </div>
                        <div class="time-display">
                            <span id="current-time">0:00</span>
                            <span id="total-time">${formatTimeDisplay(book.duration)}</span>
                        </div>
                        <div class="volume-control">
                            <i class="volume-icon"></i>
                            <input type="range" id="volume-slider" min="0" max="100" value="100" aria-label="Volume control">
                        </div>
                    </div>
                </div>
                <div class="book-details fade-in">
                    <div class="book-text-content">
                        <h2>${book.title}</h2>
                        <h3>${book.author}</h3>
                        ${categoriesHtml}
                        <p>${trimmedDescription}</p>
                        <div class="meta-inline">
                            ${audioStatus}
                            <div class="meta-item"><i class="channel-icon-small"></i>Canale ${channelHtml}</div>
                            <div class="meta-item"><i class="duration-icon"></i>Durata ${durationHtml}</div>
                            ${uploadDate ? `<div class="meta-item">Pubblicato il ${uploadDate}</div>` : ''}
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Set up audio player if audio is available
        const audioPlayer = document.getElementById('audio-player');
        if (audioAvailable) {
            audioPlayer.src = book.audioUrl;
            audioPlayer.style.display = 'block';
        } else {
            audioPlayer.style.display = 'none';
        }
        
        // Set up player controls
        setupPlayerControls(book);
        
        // Set up YouTube player if video ID is available
        if (book.videoId) {
            document.getElementById('youtube-player').innerHTML = '';
            loadYouTubeVideo(book.videoId);
        } else {
            document.getElementById('youtube-player').innerHTML = '';
        }
    }
    
    function setupPlayerControls(book) {
        const playPauseButton = document.getElementById('play-pause');
        const rewindButton = document.getElementById('rewind-button');
        const forwardButton = document.getElementById('forward-button');
        const volumeSlider = document.getElementById('volume-slider');
        const progressBar = document.getElementById('progress-bar');
        const progressHandle = document.getElementById('progress-handle');
        const progressContainer = document.getElementById('progress-container');
        const currentTimeDisplay = document.getElementById('current-time');
        
        // Reset player state
        playerState.duration = book.duration;
        updateProgressBar(0);
        
        // Volume control
        volumeSlider.addEventListener('input', function() {
            const volume = this.value;
            playerState.volume = volume;
            if (youtubePlayer && youtubePlayer.setVolume) {
                youtubePlayer.setVolume(volume);
            }
        });
        
        // Play/Pause button
        playPauseButton.addEventListener('click', function() {
            if (!youtubePlayer) return;
            
            if (playerState.isPlaying) {
                youtubePlayer.pauseVideo();
                this.innerHTML = '<i class="play-icon"></i>';
                playerState.isPlaying = false;
            } else {
                youtubePlayer.playVideo();
                this.innerHTML = '<i class="pause-icon"></i>';
                playerState.isPlaying = true;
            }
        });
        
        // Rewind 10 seconds button
        rewindButton.addEventListener('click', function() {
            if (!youtubePlayer) return;
            const newTime = Math.max(0, youtubePlayer.getCurrentTime() - 10);
            youtubePlayer.seekTo(newTime);
        });
        
        // Forward 10 seconds button
        forwardButton.addEventListener('click', function() {
            if (!youtubePlayer) return;
            const newTime = Math.min(playerState.duration, youtubePlayer.getCurrentTime() + 10);
            youtubePlayer.seekTo(newTime);
        });
        
        // Progress bar click handling
        progressContainer.addEventListener('click', function(e) {
            if (!youtubePlayer) return;
            
            const rect = this.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const width = rect.width;
            const percentage = x / width;
            const seekTime = percentage * playerState.duration;
            
            youtubePlayer.seekTo(seekTime);
            updateProgressBar(percentage * 100);
        });
        
        // Update progress every second
        if (updateInterval) clearInterval(updateInterval);
        updateInterval = setInterval(() => {
            if (youtubePlayer && youtubePlayer.getCurrentTime) {
                const currentTime = youtubePlayer.getCurrentTime();
                playerState.currentTime = currentTime;
                
                // Update UI elements
                const percentage = (currentTime / playerState.duration) * 100;
                updateProgressBar(percentage);
                currentTimeDisplay.textContent = formatTimeDisplay(currentTime);
            }
        }, 1000);
    }
    
    function updateProgressBar(percentage) {
        const progressBar = document.getElementById('progress-bar');
        const progressHandle = document.getElementById('progress-handle');
        
        if (progressBar && progressHandle) {
            progressBar.style.width = `${percentage}%`;
            progressHandle.style.left = `${percentage}%`;
        }
    }
    
    // Initialize YouTube player
    window.onYouTubeIframeAPIReady = function() {
        // The API will call this function when it's ready
        if (currentBook && currentBook.videoId) {
            loadYouTubeVideo(currentBook.videoId);
        }
    };
    
    function loadYouTubeVideo(videoId) {
        // Clear previous player
        if (youtubePlayer) {
            youtubePlayer.destroy();
        }
        
        // Create a new player
        youtubePlayer = new YT.Player('youtube-player', {
            height: '180',
            width: '320',
            videoId: videoId,
            playerVars: {
                'playsinline': 1,
                'autoplay': 1,
                'controls': 0, // Hide default controls
                'rel': 0,
                'modestbranding': 1
            },
            events: {
                'onReady': onPlayerReady,
                'onStateChange': onPlayerStateChange
            }
        });
    }
    
    function onPlayerReady(event) {
        // Play the video when ready
        event.target.playVideo();
        
        // Set volume based on current playerState
        event.target.setVolume(playerState.volume);
        
        // Update player state
        playerState.isPlaying = true;
        playerState.duration = event.target.getDuration();
        
        // Update UI
        document.getElementById('play-pause').innerHTML = '<i class="pause-icon"></i>';
        document.getElementById('total-time').textContent = formatTimeDisplay(playerState.duration);
        
        // Hide audio player when YouTube is available
        document.getElementById('audio-player').style.display = 'none';
    }
    
    function onPlayerStateChange(event) {
        // Update play/pause button based on player state
        const playPauseButton = document.getElementById('play-pause');
        
        if (event.data === YT.PlayerState.PLAYING) {
            playPauseButton.innerHTML = '<i class="pause-icon"></i>';
            playerState.isPlaying = true;
        } else if (event.data === YT.PlayerState.PAUSED || event.data === YT.PlayerState.ENDED) {
            playPauseButton.innerHTML = '<i class="play-icon"></i>';
            playerState.isPlaying = false;
        }
    }
    
    function performSearch() {
        const searchTerm = document.getElementById('search').value.toLowerCase();
        if (!searchTerm) {
            return;
        }
        
        // Clear any selected genre pills
        document.querySelectorAll('.genre-pill').forEach(pill => {
            pill.classList.remove('selected');
        });
        
        // Show loading state while searching
        document.getElementById('current-audiobook').innerHTML = `
            <div class="loading-container slide-up">
                <div class="loading-spinner"></div>
                <p>Searching for "${searchTerm}"...</p>
                <small>Looking through our audiobook collection</small>
            </div>
        `;
        
        // Clear previous interval
        if (updateInterval) clearInterval(updateInterval);
        
        // Short timeout to allow loading state to render before potentially intensive search
        setTimeout(() => {
            const results = audiobooks.filter(book => 
                (book.title && book.title.toLowerCase().includes(searchTerm)) ||
                (book.author && book.author.toLowerCase().includes(searchTerm)) ||
                (book.description && book.description.toLowerCase().includes(searchTerm)) ||
                (book.categories && book.categories.some(cat => cat.toLowerCase().includes(searchTerm))) ||
                (book.tags && book.tags.some(tag => tag.toLowerCase().includes(searchTerm)))
            );
            
            if (results.length > 0) {
                if (currentBook) {
                    previousBooks.push(currentBook); // Save current book before showing search result
                }
                currentBook = results[0];
                displayBook(currentBook);
            } else {
                document.getElementById('current-audiobook').innerHTML = `
                    <div class="no-results fade-in">
                        <i class="search-icon"></i>
                        <h3>No matching audiobooks found</h3>
                        <p>We couldn't find any audiobooks matching "${searchTerm}"</p>
                        <button class="back-button" id="search-back-button">Back to main view</button>
                    </div>`;
                    
                // Add event listener for the back button
                document.getElementById('search-back-button').addEventListener('click', () => {
                    if (previousBooks.length > 0) {
                        currentBook = previousBooks.pop();
                    }
                    displayBook(currentBook);
                });
            }
        }, 500);
    }
    
    function formatTimeDisplay(seconds) {
        if (!seconds) return "0:00";
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
        } else {
            return `${minutes}:${secs.toString().padStart(2, '0')}`;
        }
    }
    
    function formatDuration(seconds) {
        if (!seconds) return "Durata sconosciuta";
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        if (hours > 0) {
            return `${hours}h ${minutes}m`;
        } else {
            return `${minutes}m`;
        }
    }
    
    function formatUploadDate(dateString) {
        if (!dateString || dateString.length !== 8) return "";
        
        const year = dateString.substring(0, 4);
        const month = dateString.substring(4, 6);
        const day = dateString.substring(6, 8);
        
        const date = new Date(`${year}-${month}-${day}`);
        return date.toLocaleDateString(undefined, { 
            year: 'numeric', 
            month: 'short', 
            day: 'numeric' 
        });
    }
    
    function extractVideoId(url) {
        if (!url) return null;
        
        // Extract YouTube video ID from URL
        const regExp = /^.*(youtu.be\/|v\/|u\/\w\/|embed\/|watch\?v=|&v=)([^#&?]*).*/;
        const match = url.match(regExp);
        
        return (match && match[2].length === 11) ? match[2] : null;
    }

    // Changelog functionality
    function initializeChangelog() {
        const changelogCard = document.getElementById('changelog-card');
        const changelogToggle = document.getElementById('changelog-toggle');
        const changelogContent = document.getElementById('changelog-content');
        
        // Check if user preference for collapsing is stored
        const isCollapsed = localStorage.getItem('changelogCollapsed') === 'true';
        if (isCollapsed) {
            changelogCard.classList.add('collapsed');
            changelogToggle.querySelector('.collapse-icon').textContent = '+';
        }
        
        // Toggle changelog visibility
        changelogToggle.addEventListener('click', () => {
            changelogCard.classList.toggle('collapsed');
            const isNowCollapsed = changelogCard.classList.contains('collapsed');
            localStorage.setItem('changelogCollapsed', isNowCollapsed);
            changelogToggle.querySelector('.collapse-icon').textContent = isNowCollapsed ? '+' : '−';
        });
        
        // Load changelog data
        document.getElementById('changelog-content').innerHTML = `
            <div class="loading-spinner small"></div>
            <p>Caricamento aggiornamenti...</p>
        `;
        
        // Try loading the changelog data
        fetchChangelog();
    }

    function fetchChangelog() {
        // Set a timeout for the fetch
        const timeoutPromise = new Promise((_, reject) => 
            setTimeout(() => reject(new Error('Timeout')), 8000)
        );
        
        // Fetch with timeout handling
        Promise.race([
            fetch(config.changelogPath),
            timeoutPromise
        ])
        .then(response => {
            if (!response.ok) {
                throw new Error(`Network response was not ok: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (!data || !data.entries || !Array.isArray(data.entries)) {
                throw new Error('Invalid data format');
            }
            displayChangelog(data);
        })
        .catch(error => {
            console.error('Error loading changelog:', error);
            document.getElementById('changelog-content').innerHTML = `
                <div class="error-message small">
                    <p>Impossibile caricare gli aggiornamenti: ${error.message || 'Unknown error'}</p>
                    <button id="retry-changelog" class="control-button small">Riprova</button>
                </div>
            `;
            
            // Add retry button functionality
            document.getElementById('retry-changelog')?.addEventListener('click', () => {
                document.getElementById('changelog-content').innerHTML = `
                    <div class="loading-spinner small"></div>
                    <p>Caricamento aggiornamenti...</p>
                `;
                fetchChangelog();
            });
        });
    }

    function displayChangelog(data) {
        const changelogContent = document.getElementById('changelog-content');
        const entries = data.entries.slice(0, config.maxChangelogEntries); // Limit number of entries
        
        if (!entries || entries.length === 0) {
            changelogContent.innerHTML = '<p>Nessun aggiornamento disponibile.</p>';
            return;
        }
        
        let html = '';
        entries.forEach(entry => {
            const date = new Date(entry.date);
            const formattedDate = date.toLocaleDateString('it-IT', { 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
            });
            
            html += `
                <div class="changelog-entry">
                    <div class="changelog-date">${formattedDate}</div>
                    <h3 class="changelog-title">${entry.title}</h3>
                    <p class="changelog-description">${entry.description || ''}</p>
                    ${renderChangelogItems(entry.changes)}
                </div>
            `;
        });
        
        changelogContent.innerHTML = html;
    }
    
    // Add the missing renderChangelogItems function
    function renderChangelogItems(changes) {
        if (!changes || !Array.isArray(changes) || changes.length === 0) {
            return '';
        }
        
        // Add a style tag for the changelog items
        const styleTag = `
        <style>
            .changelog-items {
                padding-left: 0;
                list-style-type: none;
                margin-top: 10px;
            }
            .changelog-items li {
                margin-bottom: 6px;
                display: flex;
                align-items: flex-start;
            }
            .change-icon {
                display: inline-block;
                width: 22px;
                text-align: center;
                margin-right: 10px;
            }
            .change-content {
                font-size: 0.9em;
                line-height: 1.4;
                flex: 1;
                padding-top: 2px;
            }
            .change-type-feature .change-content {
                color: var(--accent-color, #10b981);
            }
            .change-type-fix .change-content {
                color: var(--fix-color, #f59e0b);
            }
        </style>`;
        
        let html = styleTag + '<ul class="changelog-items">';
        changes.forEach(item => {
            // Check if item is a string or has a type property
            if (typeof item === 'string') {
                html += `
                    <li>
                        <span class="change-icon">•</span>
                        <span class="change-content">${item}</span>
                    </li>
                `;
            } else if (item && typeof item === 'object') {
                const type = item.type || 'other';
                const content = item.text || item.content || '';
                html += `
                    <li class="change-type-${type.toLowerCase()}">
                        ${getChangeTypeIcon(type)}
                        <span class="change-content">${content}</span>
                    </li>
                `;
            }
        });
        html += '</ul>';
        
        return html;
    }

    // Helper function to get appropriate icon for change types
    function getChangeTypeIcon(type) {
        const lowerType = type.toLowerCase();
        switch (lowerType) {
            case 'feature':
            case 'new':
                return '<span class="change-icon">✨</span>';
            case 'fix':
            case 'bugfix':
                return '<span class="change-icon">🐛</span>';
            case 'improvement':
            case 'enhance':
                return '<span class="change-icon">⚡️</span>';
            case 'security':
                return '<span class="change-icon">🔒</span>';
            case 'deprecate':
            case 'deprecated':
                return '<span class="change-icon">⚠️</span>';
            case 'remove':
            case 'removed':
                return '<span class="change-icon">🗑️</span>';
            case 'docs':
            case 'documentation':
                return '<span class="change-icon">📝</span>';
            default:
                return '<span class="change-icon">•</span>';
        }
    }

    // Initialize changelog if enabled in config
    if (config.enableChangelog) {
        initializeChangelog();
    }
});