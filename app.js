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
    let heroErrorRetries = 0;
    
    // Load theme preference from localStorage, fallback to system preference
    const savedTheme = localStorage.getItem('prefersDarkMode');
    let prefersDarkMode = savedTheme !== null 
        ? savedTheme === 'true' 
        : window.matchMedia('(prefers-color-scheme: dark)').matches;
    
    /**
     * Sanitize text to prevent XSS attacks
     * @param {string} text - The text to sanitize
     * @returns {string} Sanitized text
     */
    function sanitizeText(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // WCAG: Create aria-live region for announcements
    const announceRegion = document.createElement('div');
    announceRegion.setAttribute('aria-live', 'polite');
    announceRegion.setAttribute('aria-atomic', 'true');
    announceRegion.className = 'sr-only';
    announceRegion.id = 'announce-region';
    document.body.appendChild(announceRegion);
    
    // Function to announce messages to screen readers
    /**
     * Announce a message to screen readers via aria-live region
     * @param {string} message - The message to announce
     * @returns {void}
     */
    function announceToScreenReader(message) {
        announceRegion.textContent = message;
        // Clear after announcement to avoid repetition
        setTimeout(() => {
            announceRegion.textContent = '';
        }, 1000);
    }
    
    // Show loading state immediately
    const loadingContent = `
        <div class="loading-container slide-up" role="status" aria-live="polite">
            <div class="loading-spinner" aria-hidden="true"></div>
            <p>Caricamento della tua libreria di audiolibri...</p>
            <small>Attendi mentre prepariamo la tua collezione</small>
        </div>
    `;
    document.getElementById('current-audiobook').innerHTML = loadingContent;
    
    // Theme toggle functionality
    const themeToggle = document.getElementById('theme-toggle');
    const themeLabel = document.getElementById('theme-label');
    themeToggle.addEventListener('click', toggleTheme);
    
    // WCAG: Add keyboard support for theme toggle
    themeToggle.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            toggleTheme();
        }
    });
    
    // Set up search functionality
    const searchInput = document.getElementById('search');
    const searchButton = document.getElementById('search-button');
    
    // Debounce timer for search input
    let searchDebounceTimer = null;
    
    // Add event listeners for search
    searchButton.addEventListener('click', performSearch);
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            // Clear any pending debounced search
            if (searchDebounceTimer) {
                clearTimeout(searchDebounceTimer);
                searchDebounceTimer = null;
            }
            performSearch();
        }
    });
    
    // Add debounced search on input (optional - searches as you type)
    searchInput.addEventListener('input', function() {
        if (searchDebounceTimer) {
            clearTimeout(searchDebounceTimer);
        }
        // Only auto-search if there are at least 3 characters
        const searchTerm = this.value.trim();
        if (searchTerm.length >= 3) {
            searchDebounceTimer = setTimeout(() => {
                performSearch();
            }, 500); // 500ms delay
        }
    });
    
    // WCAG: Add keyboard support for search button
    searchButton.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            performSearch();
        }
    });

    // Solidify the sticky top bar once the page is scrolled.
    const siteHeader = document.getElementById('site-header');
    if (siteHeader) {
        const onScroll = () => siteHeader.classList.toggle('is-scrolled', window.scrollY > 12);
        window.addEventListener('scroll', onScroll, { passive: true });
        onScroll();
    }

    // Main-nav: Home resets to the top and closes any open search / genre view.
    document.querySelector('[data-nav="home"]')?.addEventListener('click', (e) => {
        e.preventDefault();
        document.getElementById('search-results-card')?.remove();
        document.getElementById('genre-books-grid-card')?.remove();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // Desktop has no touch, so map vertical wheel to horizontal scroll over the
    // genre strip. Only intercept while the strip can still scroll that way, so
    // at the ends the page scrolls normally.
    document.addEventListener('wheel', (e) => {
        const strip = e.target.closest && e.target.closest('.genre-list');
        if (!strip || strip.scrollWidth <= strip.clientWidth) return;
        const max = strip.scrollWidth - strip.clientWidth;
        if ((e.deltaY < 0 && strip.scrollLeft > 0) || (e.deltaY > 0 && strip.scrollLeft < max)) {
            strip.scrollLeft += e.deltaY;
            e.preventDefault();
        }
    }, { passive: false });
    
    function toggleTheme() {
        prefersDarkMode = !prefersDarkMode;
        document.documentElement.dataset.theme = prefersDarkMode ? 'dark' : 'light';
        localStorage.setItem('prefersDarkMode', prefersDarkMode);
        themeLabel.textContent = prefersDarkMode ? 'Tema chiaro' : 'Tema scuro';
        themeToggle.setAttribute('aria-label', prefersDarkMode ? 'Passa al tema chiaro' : 'Passa al tema scuro');
        announceToScreenReader(prefersDarkMode ? 'Tema scuro attivato' : 'Tema chiaro attivato');
    }
    
    // Initialize theme toggle text and aria-label
    themeLabel.textContent = prefersDarkMode ? 'Tema chiaro' : 'Tema scuro';
    themeToggle.setAttribute('aria-label', 
        prefersDarkMode ? 'Cambia al tema chiaro' : 'Cambia al tema scuro'
    );
    
    // Cache configuration (bump CACHE_VERSION on any augmented.json data change
    // so clients drop their stale localStorage copy and refetch).
    const CACHE_VERSION = '1.1';
    const CACHE_KEY = 'audiobooksData';
    const CACHE_VERSION_KEY = 'audiobooksDataVersion';
    const CACHE_TIMESTAMP_KEY = 'audiobooksDataTimestamp';
    const CACHE_EXPIRY_HOURS = 24; // Cache expires after 24 hours
    
    // Function to check if cache is valid
    function isCacheValid() {
        try {
            const cachedVersion = localStorage.getItem(CACHE_VERSION_KEY);
            const cachedTimestamp = localStorage.getItem(CACHE_TIMESTAMP_KEY);
            
            if (!cachedVersion || !cachedTimestamp) return false;
            if (cachedVersion !== CACHE_VERSION) return false;
            
            const cacheAge = Date.now() - parseInt(cachedTimestamp);
            const maxAge = CACHE_EXPIRY_HOURS * 60 * 60 * 1000;
            
            return cacheAge < maxAge;
        } catch (e) {
            return false;
        }
    }
    
    // Function to load data from cache
    function loadFromCache() {
        try {
            const cachedData = localStorage.getItem(CACHE_KEY);
            if (cachedData) {
                return JSON.parse(cachedData);
            }
        } catch (e) {
            console.error('Error loading from cache:', e);
        }
        return null;
    }
    
    // Function to save data to cache
    function saveToCache(data) {
        try {
            localStorage.setItem(CACHE_KEY, JSON.stringify(data));
            localStorage.setItem(CACHE_VERSION_KEY, CACHE_VERSION);
            localStorage.setItem(CACHE_TIMESTAMP_KEY, Date.now().toString());
        } catch (e) {
            console.warn('Could not save to cache:', e);
            // If localStorage is full, clear old data and try again
            if (e.name === 'QuotaExceededError') {
                try {
                    localStorage.removeItem(CACHE_KEY);
                    localStorage.setItem(CACHE_KEY, JSON.stringify(data));
                    localStorage.setItem(CACHE_VERSION_KEY, CACHE_VERSION);
                    localStorage.setItem(CACHE_TIMESTAMP_KEY, Date.now().toString());
                } catch (e2) {
                    console.error('Still could not save to cache after clearing:', e2);
                }
            }
        }
    }
    
    // Function to process raw data into audiobooks array
    // This function handles both augmented.json (with real_* fields) and audiobooks.json (with basic fields)
    // The fallback logic ensures the app works with either data source
    function processAudiobooksData(data) {
        return Object.entries(data).map(([id, book]) => {
            const baseTitle = book.real_title || book.title || 'Unknown Title';
            return {
                id: id,
                // Disambiguate multi-part series for display ("… — Capitolo 12").
                title: book.part_display ? `${baseTitle} — ${book.part_display}` : baseTitle,
                series: book.series || '',
                part: book.part || null,
                author: book.real_author || 'Unknown Author',
                description: book.real_synopsis || book.description || 'No description available.',
                genre: book.real_genre || '',
                coverImage: book.thumbnail || '',
                audioUrl: book.audio_file || '',
                duration: book.duration || 0,
                formattedDuration: formatDuration(book.duration || 0),
                url: book.url || '',
                channel: book.channel || '',
                channelUrl: book.channel_url || '',
                videoId: extractVideoId(book.url || ''),
                categories: book.real_genre ? [book.real_genre] : (book.categories || []),
                tags: book.tags || [],
                uploadDate: book.upload_date || '',
                viewCount: book.view_count || 0,
                likeCount: book.like_count || 0
            };
        }).filter(book => book.title !== 'Unknown Title' && book.videoId);
    }
    
    // Pick the initial hero from the most-viewed titles — more likely to be a
    // live video and a recognizable classic than a fully random pick over 1793.
    function pickFeaturedBook() {
        if (!audiobooks.length) return null;
        const pool = [...audiobooks].sort((a, b) => (b.viewCount || 0) - (a.viewCount || 0)).slice(0, 80);
        return pool[Math.floor(Math.random() * pool.length)];
    }

    // Run a search from the ?search= query param (the static pages' search form posts here).
    function runSearchFromUrl() {
        const q = new URLSearchParams(location.search).get('search');
        if (q && q.trim()) {
            searchInput.value = q.trim();
            performSearch();
        }
    }

    // Recently-opened books, for the "Continua ad ascoltare" row.
    const RECENTS_KEY = 'recentBooks';
    function getRecentBookIds() {
        try { return JSON.parse(localStorage.getItem(RECENTS_KEY) || '[]'); } catch (e) { return []; }
    }
    function addRecent(id) {
        if (!id) return;
        try {
            const list = [id, ...getRecentBookIds().filter(x => x !== id)].slice(0, 18);
            localStorage.setItem(RECENTS_KEY, JSON.stringify(list));
        } catch (e) { /* storage full / unavailable */ }
    }

    // Load the audiobook data - try cache first, then fetch
    async function loadAudiobooksData() {
        // Check if we have valid cached data
        if (isCacheValid()) {
            const cachedData = loadFromCache();
            if (cachedData) {
                // Use cached data immediately
                audiobooks = processAudiobooksData(cachedData);
                updateLibraryStats(audiobooks);
                
                if (audiobooks.length > 0) {
                    setTimeout(() => {
                        currentBook = pickFeaturedBook();
                        displayBook(currentBook);
                        runSearchFromUrl();
                    }, 300);
                }
                
                // Optionally fetch fresh data in background for next time
                fetchFreshData(true);
                return;
            }
        }
        
        // No valid cache, fetch fresh data
        fetchFreshData(false);
    }
    
    // Function to fetch fresh data from server
    function fetchFreshData(isBackgroundUpdate) {
        // Try loading augmented.json first, then fall back to audiobooks.json.
        // cache:'no-cache' = always revalidate (conditional GET) so a redeployed
        // data file is picked up immediately instead of a stale HTTP-cached copy.
        fetch('augmented.json', { cache: 'no-cache' })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .catch(error => {
                // If augmented.json fails, try audiobooks.json as fallback
                console.warn('Failed to load augmented.json, trying audiobooks.json fallback:', error.message || error);
                return fetch('audiobooks.json', { cache: 'no-cache' })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`Fallback failed - audiobooks.json HTTP error! status: ${response.status}`);
                        }
                        return response.json();
                    })
                    .catch(fallbackError => {
                        // Both files failed to load
                        console.error('Both augmented.json and audiobooks.json failed to load');
                        throw new Error(`Failed to load audiobooks data: ${fallbackError.message || fallbackError}`);
                    });
            })
            .then(data => {
                // Save to cache for next time
                saveToCache(data);
                
                // Only update UI if this isn't a background update
                if (!isBackgroundUpdate) {
                    // Convert the JSON object to an array of audiobooks
                    audiobooks = processAudiobooksData(data);
                    
                    // Calculate and display library statistics
                    updateLibraryStats(audiobooks);
                    
                    if (audiobooks.length > 0) {
                        // Small delay to show the loading state
                        setTimeout(() => {
                            // Popular title as the initial hero (more likely live + recognizable)
                            currentBook = pickFeaturedBook();
                            displayBook(currentBook);
                            runSearchFromUrl();
                        }, 500);
                    } else {
                        document.getElementById('current-audiobook').innerHTML = 
                            `<div class="error-message">
                                <div class="error-icon">!</div>
                                <p>Nessun audiolibro trovato nella libreria.</p>
                                <small>Please check your data source and try again.</small>
                            </div>`;
                    }
                }
            })
            .catch(error => {
                // Only show error if this wasn't a background update
                if (!isBackgroundUpdate) {
                    console.error('Error loading audiobooks:', error);
                    const errorContainer = document.getElementById('current-audiobook');
                    errorContainer.innerHTML = 
                        `<div class="error-message" role="alert">
                            <div class="error-icon" aria-hidden="true">!</div>
                            <p>Errore nel caricamento della libreria di audiolibri.</p>
                            <small id="error-details"></small>
                            <small>Controlla la connessione e riprova più tardi.</small>
                            <button id="retry-button" class="control-button" type="button" style="margin-top: 1rem;">
                                Riprova
                            </button>
                        </div>`;
                    
                    // Safely set error message using textContent to prevent XSS
                    const errorDetails = document.getElementById('error-details');
                    if (errorDetails && error) {
                        errorDetails.textContent = `Dettagli: ${error.message || 'Unknown error'}`;
                    }
                    
                    // Add retry functionality
                    const retryButton = document.getElementById('retry-button');
                    if (retryButton) {
                        retryButton.addEventListener('click', () => {
                            location.reload();
                        });
                    }
                }
            });
    }
    
    // Start loading data
    loadAudiobooksData();
        
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

        // Build the Netflix-style home rows (Popolari / Novità / per genere)
        renderHomeRows(books);

        // Update footer stats
        updateFooterStats(books);
    }

    /**
     * Build the Netflix-style stacked rows on the home view from existing data.
     * @param {Object[]} books - all processed audiobooks
     */
    // Shared hover-arrow scroll affordance for horizontal strips (home rows + genre strip).
    function wireScrollAffordance(vp) {
        if (!vp) return;
        const scroller = vp.querySelector('.nf-row-scroller') || vp.querySelector('.genre-list');
        if (!scroller) return;
        const update = () => {
            const max = scroller.scrollWidth - scroller.clientWidth - 1;
            vp.classList.toggle('can-left', scroller.scrollLeft > 4);
            vp.classList.toggle('can-right', scroller.scrollLeft < max);
        };
        const step = () => Math.max(240, scroller.clientWidth * 0.85);
        vp.querySelector('.nf-row-arrow--left')?.addEventListener('click', () => scroller.scrollBy({ left: -step(), behavior: 'smooth' }));
        vp.querySelector('.nf-row-arrow--right')?.addEventListener('click', () => scroller.scrollBy({ left: step(), behavior: 'smooth' }));
        scroller.addEventListener('scroll', update, { passive: true });
        window.addEventListener('resize', update);
        update();
    }

    function renderHomeRows(books) {
        const mount = document.getElementById('home-rows');
        if (!mount || !books || !books.length) return;

        const byId = new Map(books.map(b => [b.id, b]));

        // Drop viral non-audiobook clips (very short + millions of views) from the home rows.
        const isClip = (b) => (b.duration || 0) < 600 && (b.viewCount || 0) > 1000000;
        const clean = books.filter(b => !isClip(b));

        const byViews = [...clean].sort((a, b) => (b.viewCount || 0) - (a.viewCount || 0));
        const byRecent = [...clean].sort((a, b) => String(b.uploadDate || '').localeCompare(String(a.uploadDate || '')));

        // Top genres by count
        const genreCounts = clean.reduce((acc, b) => {
            (b.categories && b.categories.length ? b.categories : ['Altro']).forEach(g => {
                const k = capitalizeCategory(g);
                acc[k] = (acc[k] || 0) + 1;
            });
            return acc;
        }, {});
        const topGenres = Object.entries(genreCounts)
            .filter(([g]) => g && g.toLowerCase() !== 'altro' && g.toLowerCase() !== 'education')
            .sort((a, b) => b[1] - a[1])
            .slice(0, 5)
            .map(([g]) => g);

        // Top voices/readers (channels) for dedicated rows
        const channelCounts = clean.reduce((acc, b) => {
            if (b.channel) acc[b.channel] = (acc[b.channel] || 0) + 1;
            return acc;
        }, {});
        const topChannels = Object.entries(channelCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 2)
            .map(([c]) => c);

        // "Continua ad ascoltare" from saved history
        const recentBooks = getRecentBookIds().map(id => byId.get(id)).filter(Boolean);

        const rows = [
            recentBooks.length >= 1 ? { title: 'Continua ad ascoltare', books: recentBooks.slice(0, 18) } : null,
            { title: 'Popolari', books: byViews.slice(0, 18) },
            { title: 'Aggiunti di recente', books: byRecent.slice(0, 18) },
            ...topGenres.map(g => ({
                title: g,
                books: clean.filter(b => (b.categories || []).some(c => capitalizeCategory(c) === g)).slice(0, 18)
            })),
            ...topChannels.map(c => ({
                title: `Voci · ${c}`,
                books: clean.filter(b => b.channel === c).sort((a, b) => (b.viewCount || 0) - (a.viewCount || 0)).slice(0, 18)
            }))
        ].filter(r => r && r.books.length >= (r.title === 'Continua ad ascoltare' ? 1 : 4));

        const esc = (s) => sanitizeText(String(s == null ? '' : s));
        const playOverlay = '<span class="nf-card-play" aria-hidden="true"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg></span>';

        const chevron = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d}"/></svg>`;
        mount.innerHTML = rows.map((row) => `
            <section class="nf-row" aria-label="${esc(row.title)}">
                <h3 class="nf-row-title">${esc(row.title)}</h3>
                <div class="nf-row-viewport">
                    <button type="button" class="nf-row-arrow nf-row-arrow--left" aria-label="Scorri indietro" tabindex="-1">${chevron('m15 18-6-6 6-6')}</button>
                    <div class="nf-row-scroller">
                        ${row.books.map(b => {
                            const hue = [...String(b.id)].reduce((h, c) => h + c.charCodeAt(0), 0) % 360;
                            const thumb = b.videoId ? `https://i.ytimg.com/vi/${b.videoId}/mqdefault.jpg` : b.coverImage;
                            const initial = esc((b.title || '?').trim().charAt(0).toUpperCase());
                            return `
                            <button type="button" class="nf-card" data-id="${esc(b.id)}" aria-label="${esc(b.title)} di ${esc(b.author)}">
                                <span class="nf-card-cover" style="--cover-hue:${hue}" data-initial="${initial}">
                                    <img class="nf-card-img" loading="lazy" alt="" src="${thumb}">
                                    ${playOverlay}
                                    <span class="nf-card-duration">${esc(b.formattedDuration)}</span>
                                </span>
                                <span class="nf-card-body">
                                    <span class="nf-card-title">${esc(b.title)}</span>
                                    <span class="nf-card-author">${esc(b.author)}</span>
                                </span>
                            </button>
                            `;
                        }).join('')}
                    </div>
                    <button type="button" class="nf-row-arrow nf-row-arrow--right" aria-label="Scorri avanti" tabindex="-1">${chevron('m9 18 6-6-6-6')}</button>
                </div>
            </section>
        `).join('');

        // Wire card clicks → set as hero + scroll up
        mount.querySelectorAll('.nf-card').forEach(card => {
            card.addEventListener('click', () => {
                const book = byId.get(card.dataset.id);
                if (book) {
                    currentBook = book;
                    addRecent(book.id);
                    displayBook(book);
                    document.getElementById('current-audiobook')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
        });

        // YouTube serves a 120x90 grey placeholder for deleted videos (HTTP 200),
        // so detect it by natural size and fall back to a generated cover.
        mount.querySelectorAll('.nf-card-img').forEach(img => {
            const fallback = () => img.closest('.nf-card-cover')?.classList.add('is-fallback');
            if (img.complete) {
                if (!img.naturalWidth || img.naturalWidth <= 120) fallback();
            }
            img.addEventListener('error', fallback);
            img.addEventListener('load', () => { if (img.naturalWidth <= 120) fallback(); });
        });

        // Row scroll affordance: reveal edge arrows/fades only when there's more to scroll.
        mount.querySelectorAll('.nf-row-viewport').forEach(wireScrollAffordance);

        // Soft staggered reveal of rows as they enter the viewport (progressive
        // enhancement: without JS/IO the rows are simply visible; skipped for reduced motion).
        if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            mount.classList.add('reveal');
            const io = new IntersectionObserver((entries, obs) => {
                entries.forEach(en => {
                    if (en.isIntersecting) { en.target.classList.add('in-view'); obs.unobserve(en.target); }
                });
            }, { rootMargin: '0px 0px -8% 0px' });
            const revealRows = mount.querySelectorAll('.nf-row');
            revealRows.forEach(r => io.observe(r));
            // Safety net: never leave a row stuck hidden (e.g. after an in-page jump).
            setTimeout(() => { io.disconnect(); revealRows.forEach(r => r.classList.add('in-view')); }, 4000);
        }
    }
    
    /**
     * Update footer with library statistics
     * @param {Object[]} books - Array of all audiobook objects
     * @returns {void}
     */
    function updateFooterStats(books) {
        const totalBooks = books.length;
        
        // Count unique authors
        const uniqueAuthors = new Set();
        books.forEach(book => {
            if (book.author && book.author !== 'Unknown Author') {
                uniqueAuthors.add(book.author);
            }
        });
        
        // Calculate total hours
        let totalDurationInSeconds = 0;
        books.forEach(book => {
            if (book.duration) {
                totalDurationInSeconds += book.duration;
            }
        });
        const totalHours = Math.floor(totalDurationInSeconds / 3600);
        
        // Update footer stats
        const footerStats = document.getElementById('library-stats');
        if (footerStats) {
            footerStats.textContent = `${totalBooks.toLocaleString()} audiolibri • ${uniqueAuthors.size.toLocaleString()} autori • ${totalHours.toLocaleString()}+ ore di ascolto`;
        }
        
        // Update current year
        const currentYear = document.getElementById('current-year');
        if (currentYear) {
            currentYear.textContent = new Date().getFullYear();
        }
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

        // Strip shows the top ~10 genres by popularity; the full list (with
        // counts) lives on /generi/, reachable via the "Tutti i generi" pill.
        const filteredGenres = Object.keys(genreCounts)
            .filter(genre => genreCounts[genre] >= 10)
            .sort((a, b) => genreCounts[b] - genreCounts[a])
            .slice(0, 10);

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

        // Genre strip mirrors the home rows: a scroller flanked by edge arrows
        // that appear on hover/when there's more to scroll (see wireScrollAffordance).
        const chevron = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="${d}"/></svg>`;
        genreNavContainer.innerHTML = `
            <div class="nf-row-viewport genre-viewport">
                <button type="button" class="nf-row-arrow nf-row-arrow--left" aria-label="Scorri indietro" tabindex="-1">${chevron('m15 18-6-6 6-6')}</button>
                <div class="genre-list" role="list" aria-label="Generi disponibili"></div>
                <button type="button" class="nf-row-arrow nf-row-arrow--right" aria-label="Scorri avanti" tabindex="-1">${chevron('m9 18 6-6-6-6')}</button>
            </div>
        `;

        const genreList = genreNavContainer.querySelector('.genre-list');

        // Generate navigation for filtered genres
        filteredGenres.forEach(genre => {
            const genrePill = document.createElement('button');
            genrePill.className = 'genre-pill tw-pill snap-start tap-highlight-none';
            genrePill.dataset.genre = genre;
            genrePill.setAttribute('role', 'listitem');
            genrePill.innerHTML = `<span class="genre-name">${capitalizeCategory(genre)}</span>`;
            
            // Add click event listener
            genrePill.addEventListener('click', function() {
                showGenreView(genre);
            });
            
            genreList.appendChild(genrePill);
        });

        // "All genres" pill → the static /generi/ index (full list + counts).
        const allPill = document.createElement('a');
        allPill.className = 'genre-pill genre-pill-all';
        allPill.href = '/generi/';
        allPill.setAttribute('role', 'listitem');
        allPill.innerHTML = `<span class="genre-name">Tutti i generi</span><span class="genre-all-arrow" aria-hidden="true">→</span>`;
        genreList.appendChild(allPill);

        // Reveal edge arrows / wire wheel + click scrolling, same as the home rows.
        wireScrollAffordance(genreNavContainer.querySelector('.nf-row-viewport'));
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
                        <h3>Nessun audiolibro trovato</h3>
                        <p>Nessun audiolibro trovato nella categoria "${genre}"</p>
                        <button class="back-button" id="empty-back-button">Torna alla ricerca</button>
                    </div>`;
                
                document.getElementById('empty-back-button').addEventListener('click', () => {
                    displayBook(currentBook);
                });
            }
        }, 500);
    }

    /**
     * Display a paginated grid of books for a genre — same markup and look as
     * the search results so the two views are unified.
     * @param {string} genre - The genre/category name
     * @param {Object[]} genreBooks - Array of audiobook objects in this genre
     * @returns {void}
     */
    function displayGenreBooksGrid(genre, genreBooks) {
        announceToScreenReader(`${capitalizeCategory(genre)}: ${genreBooks.length} audiolibri trovati`);

        document.getElementById('genre-books-grid-card')?.remove();

        const card = document.createElement('div');
        card.id = 'genre-books-grid-card';
        card.className = 'search-results-card fade-in';
        card.innerHTML = `
            <div class="search-results-header">
                <div class="search-info">
                    <h2 class="search-title">${sanitizeText(capitalizeCategory(genre))}</h2>
                    <span class="results-count">${genreBooks.length} audiolibri</span>
                </div>
                <button class="ghost-btn" id="genre-back-button" type="button">
                    <span class="back-icon"></span> Torna alla home
                </button>
            </div>
            <div class="search-results-container" id="genre-results"></div>
            <div class="pagination-controls" id="genre-pagination"></div>
        `;

        const currentAudiobookCard = document.getElementById('current-audiobook');
        currentAudiobookCard.parentNode.insertBefore(card, currentAudiobookCard);

        document.getElementById('genre-back-button').addEventListener('click', () => {
            card.remove();
            document.querySelectorAll('.genre-pill').forEach(p => p.classList.remove('selected'));
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });

        const perPage = 24;
        const totalPages = Math.ceil(genreBooks.length / perPage);
        let page = 1;

        function renderGenrePage(p) {
            const slice = genreBooks.slice((p - 1) * perPage, (p - 1) * perPage + perPage);
            const container = document.getElementById('genre-results');
            container.innerHTML = `<div class="search-grid">${slice.map(nfCardHTML).join('')}</div>`;
            wireResultCards(container);

            const pag = document.getElementById('genre-pagination');
            if (totalPages > 1) {
                pag.innerHTML = `
                    <button class="pagination-button" ${p === 1 ? 'disabled' : ''} id="genre-prev-button"><span class="prev-icon"></span> Precedente</button>
                    <span class="page-indicator">Pagina ${p} di ${totalPages}</span>
                    <button class="pagination-button" ${p === totalPages ? 'disabled' : ''} id="genre-next-button">Successiva <span class="next-icon"></span></button>
                `;
                document.getElementById('genre-prev-button')?.addEventListener('click', () => { if (page > 1) { page--; renderGenrePage(page); } });
                document.getElementById('genre-next-button')?.addEventListener('click', () => { if (page < totalPages) { page++; renderGenrePage(page); } });
            } else {
                pag.innerHTML = '';
            }
        }
        renderGenrePage(1);
    }

    function resetPlayerState() {
        playerState = {
            currentTime: 0,
            duration: 0,
            isPlaying: false,
            volume: 100
        };
    }
    
    /**
     * Display an audiobook with its metadata, player, and controls
     * @param {Object} book - The audiobook object to display
     * @param {string} book.title - Title of the audiobook
     * @param {string} book.author - Author name
     * @param {string} book.coverImage - URL to cover image
     * @param {string} book.description - Book description
     * @param {string} [book.videoId] - YouTube video ID (optional)
     * @param {string} [book.audioUrl] - Direct audio URL (optional)
     * @param {string[]} [book.categories] - Array of genre categories
     * @param {string} [book.formattedDuration] - Formatted duration string
     * @returns {void}
     */
    function displayBook(book) {
        // WCAG: Announce book change to screen readers
        announceToScreenReader(`Ora in riproduzione: ${book.title} di ${book.author}`);
        
        const bookCard = document.getElementById('current-audiobook');
        
        const audioAvailable = !!book.audioUrl;

        // Escape user-derived (scraped) text before injecting into innerHTML.
        const sanitize = (s) => sanitizeText(String(s == null ? '' : s));

        const trimmedDescription = book.description && book.description.length > 320
            ? book.description.substring(0, 320).trim() + '…'
            : (book.description || '');

        const eyebrow = 'In evidenza';

        const chipsHtml = (book.categories && book.categories.length)
            ? `<div class="hero-chips" role="list" aria-label="Generi">${book.categories.slice(0, 4).map(c => `<span class="hero-chip" role="listitem">${sanitize(capitalizeCategory(c))}</span>`).join('')}</div>`
            : '';

        const ICON = {
            play: '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M8 5v14l11-7z"/></svg>',
            shuffle: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M16 3h5v5"/><path d="M21 3 13 11"/><path d="M16 21h5v-5"/><path d="m21 21-7-7"/><path d="M3 4l6 6"/></svg>',
            mic: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="2" width="6" height="12" rx="3"/><path d="M5 10a7 7 0 0 0 14 0"/><path d="M12 19v3"/></svg>',
            clock: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
            eye: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/></svg>'
        };

        const views = book.viewCount ? book.viewCount.toLocaleString('it-IT') : null;
        const metaHtml = [
            `<span class="hero-meta-item">${ICON.clock}${book.formattedDuration}</span>`,
            views ? `<span class="hero-meta-item">${ICON.eye}${views} visualizzazioni</span>` : '',
            book.channel ? `<span class="hero-meta-item">${ICON.mic}${sanitize(book.channel)}</span>` : ''
        ].filter(Boolean).join('<span class="hero-meta-sep">·</span>');

        const channelCta = book.channelUrl
            ? `<a class="hero-cta hero-cta-secondary" href="${encodeURI(book.channelUrl)}" target="_blank" rel="noopener noreferrer">${ICON.mic} Canale</a>`
            : '';
        
        bookCard.innerHTML = `
            <div class="hero">
                <div class="hero-backdrop" aria-hidden="true"></div>
                <div class="hero-scrim" aria-hidden="true"></div>
                <div class="hero-body">
                    <div class="hero-media slide-up">
                        <div id="youtube-player" role="region" aria-label="Lettore audiolibro"></div>
                        <audio id="audio-player" controls preload="metadata" aria-describedby="audio-description">
                            Il tuo browser non supporta l'elemento audio.
                        </audio>
                        <div id="audio-description" class="sr-only">Lettore audio per ${sanitize(book.title)} di ${sanitize(book.author)}</div>
                        <div class="player-controls" role="region" aria-label="Controlli di riproduzione">
                            <div class="controls-row">
                                <button id="rewind-button" class="control-button" type="button" aria-label="Riavvolgi di 10 secondi">
                                    <i class="rewind-icon" aria-hidden="true"></i><span class="sr-only">Riavvolgi</span>
                                </button>
                                <button id="play-pause" class="control-button large" type="button" aria-label="Riproduci o metti in pausa">
                                    <i class="play-icon" aria-hidden="true"></i><span class="sr-only">Riproduci</span>
                                </button>
                                <button id="forward-button" class="control-button" type="button" aria-label="Avanza di 10 secondi">
                                    <i class="forward-icon" aria-hidden="true"></i><span class="sr-only">Avanza</span>
                                </button>
                            </div>
                            <div class="progress-container" id="progress-container" role="slider" aria-label="Posizione di riproduzione" aria-valuemin="0" aria-valuemax="100" aria-valuenow="0" tabindex="0">
                                <div class="progress-bar" id="progress-bar"></div>
                                <div class="progress-handle" id="progress-handle"></div>
                            </div>
                            <div class="time-display" aria-live="polite" aria-atomic="false">
                                <span id="current-time" aria-label="Tempo corrente">0:00</span>
                                <span aria-hidden="true">/</span>
                                <span id="total-time" aria-label="Durata totale">${formatTimeDisplay(book.duration)}</span>
                            </div>
                            <div class="volume-control">
                                <i class="volume-icon" aria-hidden="true"></i>
                                <label for="volume-slider" class="sr-only">Controllo volume</label>
                                <input type="range" id="volume-slider" min="0" max="100" value="100" aria-label="Volume: 100%" aria-valuemin="0" aria-valuemax="100" aria-valuenow="100">
                            </div>
                        </div>
                    </div>
                    <div class="hero-content fade-in">
                        <span class="hero-eyebrow">${sanitize(eyebrow)}</span>
                        <h2 id="book-title" class="hero-title">${sanitize(book.title)}</h2>
                        <p id="book-author" class="hero-author">di <b>${sanitize(book.author)}</b></p>
                        ${chipsHtml}
                        <p id="book-description" class="hero-synopsis">${sanitize(trimmedDescription)}</p>
                        <div class="hero-meta">${metaHtml}</div>
                        <div class="hero-actions">
                            <button class="hero-cta hero-cta-primary" id="hero-play" type="button">${ICON.play} Ascolta</button>
                            <button class="hero-cta hero-cta-secondary" id="hero-shuffle" type="button">${ICON.shuffle} Casuale</button>
                            ${channelCta}
                        </div>
                    </div>
                </div>
            </div>
        `;

        const heroBackdrop = bookCard.querySelector('.hero-backdrop');
        if (heroBackdrop) heroBackdrop.style.backgroundImage = `url('${book.coverImage}')`;
        
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

        // Hero CTAs
        document.getElementById('hero-play')?.addEventListener('click', () => {
            addRecent(book.id);
            document.getElementById('play-pause')?.click();
        });
        document.getElementById('hero-shuffle')?.addEventListener('click', () => {
            if (audiobooks && audiobooks.length) {
                currentBook = audiobooks[Math.floor(Math.random() * audiobooks.length)];
                displayBook(currentBook);
                document.getElementById('current-audiobook')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    }
    
    /**
     * Initialize player controls for YouTube video player
     * Sets up play/pause, seek, progress bar, and volume controls
     * @param {Object} book - The audiobook object being played
     * @returns {void}
     */
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
        try {
            // The API will call this function when it's ready
            if (currentBook && currentBook.videoId) {
                loadYouTubeVideo(currentBook.videoId);
            }
        } catch (error) {
            console.error('YouTube API initialization failed:', error);
            showYouTubeError('Errore durante l\'inizializzazione del lettore video');
        }
    };
    
    /**
     * Load and initialize a YouTube video player
     * @param {string} videoId - The YouTube video ID
     * @returns {void}
     */
    function loadYouTubeVideo(videoId) {
        try {
            // Check if YouTube API is available
            if (typeof YT === 'undefined' || typeof YT.Player === 'undefined') {
                showYouTubeError('L\'API di YouTube non è disponibile. Controlla la connessione.');
                return;
            }
            
            // Clear previous player
            if (youtubePlayer) {
                try {
                    youtubePlayer.destroy();
                } catch (e) {
                    console.warn('Could not destroy previous player:', e);
                }
            }
            
            // Create a new player
            youtubePlayer = new YT.Player('youtube-player', {
                height: '180',
                width: '320',
                videoId: videoId,
                host: 'https://www.youtube-nocookie.com',
                playerVars: {
                    'playsinline': 1,
                    'autoplay': 1,
                    'controls': 0, // Hide default controls
                    'rel': 0,
                    'modestbranding': 1
                },
                events: {
                    'onReady': onPlayerReady,
                    'onStateChange': onPlayerStateChange,
                    'onError': onPlayerError
                }
            });
        } catch (error) {
            console.error('Error loading YouTube video:', error);
            showYouTubeError('Impossibile caricare il video. Riprova più tardi.');
        }
    }
    
    function onPlayerReady(event) {
        // Play the video when ready
        event.target.playVideo();
        
        // Set volume based on current playerState
        event.target.setVolume(playerState.volume);
        
        // Update player state
        playerState.isPlaying = true;
        playerState.duration = event.target.getDuration();
        
        // Announce to screen readers
        announceToScreenReader('Riproduzione avviata');
        
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
            heroErrorRetries = 0;
            announceToScreenReader('Riproduzione in corso');
        } else if (event.data === YT.PlayerState.PAUSED) {
            playPauseButton.innerHTML = '<i class="play-icon"></i>';
            playerState.isPlaying = false;
            announceToScreenReader('Riproduzione in pausa');
        } else if (event.data === YT.PlayerState.ENDED) {
            playPauseButton.innerHTML = '<i class="play-icon"></i>';
            playerState.isPlaying = false;
            announceToScreenReader('Riproduzione terminata');
        }
    }
    
    function onPlayerError(event) {
        // Handle YouTube player errors
        const errorMessages = {
            2: 'Richiesta non valida. Controlla l\'URL del video.',
            5: 'Errore del lettore HTML5.',
            100: 'Video non trovato o rimosso.',
            101: 'Il proprietario del video non consente la riproduzione incorporata.',
            150: 'Il proprietario del video non consente la riproduzione incorporata.'
        };
        
        const errorCode = event.data;
        const errorMessage = errorMessages[errorCode] || 'Errore sconosciuto durante la riproduzione.';
        
        console.error('YouTube Player Error:', errorCode, errorMessage);

        // Video removed / embedding disabled: silently advance to another featured
        // title instead of leaving "video non disponibile" as the first impression.
        const unavailable = [100, 101, 150].includes(errorCode);
        if (unavailable && heroErrorRetries < 6 && audiobooks.length > 1) {
            heroErrorRetries++;
            const next = pickFeaturedBook();
            if (next && next !== currentBook) {
                currentBook = next;
                displayBook(currentBook);
                return;
            }
        }
        showYouTubeError(errorMessage);
    }
    
    function showYouTubeError(message) {
        const playerContainer = document.getElementById('youtube-player');
        if (playerContainer) {
            playerContainer.innerHTML = `
                <div style="
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    height: 180px;
                    background: rgba(0,0,0,0.1);
                    border-radius: 8px;
                    padding: 1rem;
                    text-align: center;
                ">
                    <span style="font-size: 2rem; margin-bottom: 0.5rem;">⚠️</span>
                    <p style="margin: 0; color: var(--text-color); font-size: 0.9rem;">${message}</p>
                </div>
            `;
        }
    }
    
    /**
     * Perform search across audiobooks by title, author, and description
     * Minimum 3 characters required, debounced at 500ms
     * @returns {void}
     */
    function performSearch() {
        const searchTerm = searchInput.value.trim();
        
        // WCAG: Announce search start to screen readers
        if (!searchTerm) {
            announceToScreenReader('Inserisci un termine di ricerca');
            searchInput.focus();
            return;
        }
        
        const searchTermLower = searchTerm.toLowerCase();
        announceToScreenReader(`Ricerca in corso per: ${searchTerm}`);
        
        // Filter audiobooks based on search term
        const results = audiobooks.filter(book =>
            book.title.toLowerCase().includes(searchTermLower) ||
            book.author.toLowerCase().includes(searchTermLower) ||
            (book.description && book.description.toLowerCase().includes(searchTermLower)) ||
            (book.tags && book.tags.some(tag => tag.toLowerCase().includes(searchTermLower))) ||
            (book.genre && book.genre.toLowerCase().includes(searchTermLower))
        );
        
        // Show loading state with proper accessibility
        const loadingContent = `
            <div class="loading-container slide-up" role="status" aria-live="polite">
                <div class="loading-spinner" aria-hidden="true"></div>
                <p>Ricerca in corso per "${searchTerm}"...</p>
                <small>Ricerca audiolibri corrispondenti</small>
            </div>
        `;
        document.getElementById('current-audiobook').innerHTML = loadingContent;
        
        // Clear previous player interval if exists
        if (updateInterval) clearInterval(updateInterval);
        
        setTimeout(() => {
            if (results.length > 0) {
                // Announce results count
                announceToScreenReader(`Trovati ${results.length} audiolibri per la ricerca: ${searchTerm}`);
                displaySearchResults(searchTerm, results);
            } else {
                // Announce no results
                announceToScreenReader(`Nessun risultato trovato per: ${searchTerm}`);
                
                // Show no results message with better accessibility
                const noResultsContent = `
                    <div class="no-results fade-in" role="status" aria-live="polite">
                        <i class="search-icon" aria-hidden="true"></i>
                        <h3>Nessun audiolibro trovato</h3>
                        <p>Non sono stati trovati audiolibri per "${searchTerm}"</p>
                        <button class="back-button" id="empty-back-button" type="button" aria-label="Torna alla ricerca principale">
                            Torna alla ricerca
                        </button>
                    </div>`;
                document.getElementById('current-audiobook').innerHTML = noResultsContent;
                
                const backButton = document.getElementById('empty-back-button');
                backButton.addEventListener('click', () => {
                    announceToScreenReader('Tornando alla ricerca principale');
                    if (currentBook) {
                        displayBook(currentBook);
                    } else if (audiobooks.length > 0) {
                        // If no current book, display a random one
                        const randomIndex = Math.floor(Math.random() * audiobooks.length);
                        currentBook = audiobooks[randomIndex];
                        displayBook(currentBook);
                    }
                });
                
                // WCAG: Add keyboard support for back button
                backButton.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault();
                        backButton.click();
                    }
                });
                
                // Focus the back button for better UX
                setTimeout(() => backButton.focus(), 100);
            }
        }, 500);
    }
    
    // Function to display search results
    /**
     * Build the markup for a single Netflix-style result card (shared by the
     * search results and the genre/author grid so they stay identical).
     * @param {Object} book - audiobook object
     * @returns {string} HTML string for one .nf-card button
     */
    function nfCardHTML(book) {
        const esc = (s) => sanitizeText(String(s == null ? '' : s));
        const hue = [...String(book.id)].reduce((h, c) => h + c.charCodeAt(0), 0) % 360;
        const thumb = book.videoId ? `https://i.ytimg.com/vi/${book.videoId}/mqdefault.jpg` : book.coverImage;
        const initial = esc((book.title || '?').trim().charAt(0).toUpperCase());
        return `
            <button type="button" class="nf-card" data-id="${esc(book.id)}" aria-label="${esc(book.title)} di ${esc(book.author)}">
                <span class="nf-card-cover" style="--cover-hue:${hue}" data-initial="${initial}">
                    <img class="nf-card-img" loading="lazy" alt="" src="${thumb}">
                    <span class="nf-card-play" aria-hidden="true"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg></span>
                    <span class="nf-card-duration">${esc(book.formattedDuration)}</span>
                </span>
                <span class="nf-card-body">
                    <span class="nf-card-title">${esc(book.title)}</span>
                    <span class="nf-card-author">${esc(book.author)}</span>
                </span>
            </button>`;
    }

    /**
     * Wire card clicks + deleted-thumbnail fallback for an .nf-card grid.
     * @param {HTMLElement} container - element containing the .nf-card buttons
     * @returns {void}
     */
    function wireResultCards(container) {
        container.querySelectorAll('.nf-card').forEach(card => {
            card.addEventListener('click', () => {
                const book = audiobooks.find(b => b.id === card.dataset.id);
                if (!book) return;
                if (currentBook) previousBooks.push(currentBook);
                currentBook = book;
                addRecent(book.id);
                displayBook(book);
                document.getElementById('current-audiobook')?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        });
        container.querySelectorAll('.nf-card-img').forEach(img => {
            const fb = () => img.closest('.nf-card-cover')?.classList.add('is-fallback');
            if (img.complete) { if (!img.naturalWidth || img.naturalWidth <= 120) fb(); }
            img.addEventListener('error', fb);
            img.addEventListener('load', () => { if (img.naturalWidth <= 120) fb(); });
        });
    }

    /**
     * Display search results in a paginated grid
     * @param {string} searchTerm - The search query string (will be sanitized)
     * @param {Object[]} results - Array of matching audiobook objects
     * @returns {void}
     */
    function displaySearchResults(searchTerm, results) {
        // Announce search results to screen readers
        announceToScreenReader(`${results.length} audiolibri trovati per "${searchTerm}"`);
        
        // Remove any existing search results card first
        const existingCard = document.getElementById('search-results-card');
        if (existingCard) {
            existingCard.remove();
        }
        
        // Set up pagination
        const resultsPerPage = 24;
        let currentPage = 1;
        const totalPages = Math.ceil(results.length / resultsPerPage);
        
        // Display the first book from search results
        if (results.length > 0) {
            if (currentBook) {
                previousBooks.push(currentBook);
            }
            currentBook = results[0];
            displayBook(currentBook);
        }
        
        // Create a new card for the search results
        const searchResultsCard = document.createElement('div');
        searchResultsCard.id = 'search-results-card';
        searchResultsCard.className = 'search-results-card fade-in';
        
        // Sanitize search term for display
        const sanitizedSearchTerm = sanitizeText(searchTerm);
        
        // Create header with search info
        searchResultsCard.innerHTML = `
            <div class="search-results-header">
                <div class="search-info">
                    <h2 class="search-title">Risultati per "${sanitizedSearchTerm}"</h2>
                    <span class="results-count">${results.length} audiolibri trovati</span>
                </div>
                <button class="ghost-btn" id="search-back-button" type="button">
                    <span class="back-icon"></span> Torna alla ricerca
                </button>
            </div>
            <div class="search-results-container" id="search-results"></div>
            <div class="pagination-controls" id="pagination-controls"></div>
        `;
        
        // Insert the search results card before the current audiobook card
        const currentAudiobookCard = document.querySelector('.single-card');
        if (currentAudiobookCard && currentAudiobookCard.parentNode) {
            currentAudiobookCard.parentNode.insertBefore(searchResultsCard, currentAudiobookCard);
        }
        
        // Add event listener to back button
        document.getElementById('search-back-button').addEventListener('click', () => {
            // Remove the search results card
            searchResultsCard.remove();
            
            // Display the previous book or current book
            if (previousBooks.length > 0) {
                currentBook = previousBooks.pop();
                displayBook(currentBook);
            } else if (currentBook) {
                displayBook(currentBook);
            }
        });
        
        // Function to render a specific page of results
        function renderPage(page) {
            const start = (page - 1) * resultsPerPage;
            const end = start + resultsPerPage;
            const booksToDisplay = results.slice(start, end);
            
            // Get the search results container
            const resultsContainer = document.getElementById('search-results');
            
            // Grid of result cards (shared markup + wiring with the genre view).
            resultsContainer.innerHTML = `<div class="search-grid">${booksToDisplay.map(nfCardHTML).join('')}</div>`;
            wireResultCards(resultsContainer);

            // Update pagination controls
            const paginationControls = document.getElementById('pagination-controls');
            if (totalPages > 1) {
                paginationControls.innerHTML = `
                    <button class="pagination-button" ${page === 1 ? 'disabled' : ''} id="prev-page-button">
                        <span class="prev-icon"></span> Precedente
                    </button>
                    <span class="page-indicator">Pagina ${page} di ${totalPages}</span>
                    <button class="pagination-button" ${page === totalPages ? 'disabled' : ''} id="next-page-button">
                        Successiva <span class="next-icon"></span>
                    </button>
                `;
                
                // Add event listeners to pagination buttons
                const prevButton = document.getElementById('prev-page-button');
                const nextButton = document.getElementById('next-page-button');
                
                if (prevButton) {
                    prevButton.addEventListener('click', () => {
                        if (currentPage > 1) {
                            currentPage--;
                            renderPage(currentPage);
                        }
                    });
                }
                
                if (nextButton) {
                    nextButton.addEventListener('click', () => {
                        if (currentPage < totalPages) {
                            currentPage++;
                            renderPage(currentPage);
                        }
                    });
                }
            } else {
                paginationControls.innerHTML = '';
            }
        }
        
        // Render the first page of results
        renderPage(currentPage);
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
    
    
    // Cleanup on page unload to prevent memory leaks
    window.addEventListener('beforeunload', () => {
        if (updateInterval) {
            clearInterval(updateInterval);
        }
        if (youtubePlayer && youtubePlayer.destroy) {
            youtubePlayer.destroy();
        }
    });

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
    
    // Cleanup on page unload to prevent memory leaks
    window.addEventListener('beforeunload', () => {
        if (updateInterval) {
            clearInterval(updateInterval);
        }
        if (youtubePlayer && youtubePlayer.destroy) {
            youtubePlayer.destroy();
        }
    });
    
    // Keyboard shortcuts for player controls
    document.addEventListener('keydown', (e) => {
        // Don't trigger if user is typing in an input field
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
            return;
        }
        
        const playPauseButton = document.getElementById('play-pause');
        const rewindButton = document.getElementById('rewind-button');
        const forwardButton = document.getElementById('forward-button');
        
        switch(e.key) {
            case ' ': // Spacebar - play/pause
                e.preventDefault();
                if (playPauseButton) playPauseButton.click();
                announceToScreenReader(playerState.isPlaying ? 'Pausa' : 'Riproduci');
                break;
            case 'ArrowLeft': // Left arrow - rewind 10s
                e.preventDefault();
                if (rewindButton) rewindButton.click();
                announceToScreenReader('Riavvolgi 10 secondi');
                break;
            case 'ArrowRight': // Right arrow - forward 10s
                e.preventDefault();
                if (forwardButton) forwardButton.click();
                announceToScreenReader('Avanza 10 secondi');
                break;
            case 'ArrowUp': // Up arrow - volume up
                e.preventDefault();
                const volumeSlider = document.getElementById('volume-slider');
                if (volumeSlider) {
                    const newVolume = Math.min(100, parseInt(volumeSlider.value) + 10);
                    volumeSlider.value = newVolume;
                    volumeSlider.dispatchEvent(new Event('input'));
                    announceToScreenReader(`Volume: ${newVolume}%`);
                }
                break;
            case 'ArrowDown': // Down arrow - volume down
                e.preventDefault();
                const volumeSliderDown = document.getElementById('volume-slider');
                if (volumeSliderDown) {
                    const newVolume = Math.max(0, parseInt(volumeSliderDown.value) - 10);
                    volumeSliderDown.value = newVolume;
                    volumeSliderDown.dispatchEvent(new Event('input'));
                    announceToScreenReader(`Volume: ${newVolume}%`);
                }
                break;
            case 'm': // M - mute/unmute
                e.preventDefault();
                const volumeSliderMute = document.getElementById('volume-slider');
                if (volumeSliderMute) {
                    const isMuted = volumeSliderMute.value === '0';
                    volumeSliderMute.value = isMuted ? playerState.volume : 0;
                    volumeSliderMute.dispatchEvent(new Event('input'));
                    announceToScreenReader(isMuted ? 'Audio attivato' : 'Audio disattivato');
                }
                break;
        }
    });
});