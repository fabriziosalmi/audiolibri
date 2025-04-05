// app.js
let player;

document.addEventListener('DOMContentLoaded', () => {
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
            prefersDarkMode = true;
        }
        themeLabel.textContent = prefersDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode';
    }
    
    // Initialize theme toggle text
    themeLabel.textContent = prefersDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode';
    
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
                    coverImage: book.thumbnail || 'https://via.placeholder.com/400x225?text=No+Cover+Available',
                    audioUrl: book.audio_file || '',
                    duration: book.duration || 0,
                    formattedDuration: formatDuration(book.duration || 0),
                    url: book.url || '',
                    channel: book.channel || '',
                    channelUrl: book.channel_url || '',
                    videoId: extractVideoId(book.url || ''),
                    categories: book.categories || [],
                    tags: book.tags || [],
                    uploadDate: book.upload_date || ''
                };
            }).filter(book => book.title !== 'Unknown Title' && book.videoId); // Filter out entries without titles and video IDs
            
            if (audiobooks.length > 0) {
                // Small delay to show the loading state
                setTimeout(() => loadRandomBook(), 500);
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
    
    // Set up event listeners
    document.getElementById('search-button').addEventListener('click', performSearch);
    document.getElementById('random-button').addEventListener('click', loadRandomBook);
    document.getElementById('previous-button').addEventListener('click', loadPreviousBook);
    
    // Set up search with Enter key
    document.getElementById('search').addEventListener('keyup', (event) => {
        if (event.key === 'Enter') {
            performSearch();
        }
    });
    
    // Listen for system theme changes
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', e => {
        prefersDarkMode = e.matches;
        themeLabel.textContent = prefersDarkMode ? 'Switch to Light Mode' : 'Switch to Dark Mode';
    });
    
    function loadRandomBook() {
        if (audiobooks.length === 0) return;
        
        // Show loading state while getting the next book
        document.getElementById('current-audiobook').innerHTML = `
            <div class="loading-container slide-up">
                <div class="loading-spinner"></div>
                <p>Preparing your audiobook...</p>
            </div>
        `;
        
        if (currentBook) {
            previousBooks.push(currentBook); // Save current book before loading a new one
        }
        
        // Reset player state
        resetPlayerState();
        
        // Clear previous interval if exists
        if (updateInterval) clearInterval(updateInterval);
        
        const randomIndex = Math.floor(Math.random() * audiobooks.length);
        currentBook = audiobooks[randomIndex];
        
        // Short delay to show the loading animation
        setTimeout(() => {
            displayBook(currentBook);
            document.getElementById('previous-button').disabled = previousBooks.length === 0;
        }, 300);
    }
    
    function loadPreviousBook() {
        if (previousBooks.length === 0) return;
        
        // Show loading state
        document.getElementById('current-audiobook').innerHTML = `
            <div class="loading-container slide-up">
                <div class="loading-spinner"></div>
                <p>Loading previous audiobook...</p>
            </div>
        `;
        
        // Reset player state
        resetPlayerState();
        
        // Clear previous interval
        if (updateInterval) clearInterval(updateInterval);
        
        currentBook = previousBooks.pop();
        
        // Short delay to show loading animation
        setTimeout(() => {
            displayBook(currentBook);
            document.getElementById('previous-button').disabled = previousBooks.length === 0;
        }, 300);
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
                    `<span class="category-tag">${category}</span>`
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
                            <div class="meta-item"><i class="channel-icon-small"></i>Channel: ${channelHtml}</div>
                            <div class="meta-item"><i class="duration-icon"></i>Duration: ${durationHtml}</div>
                            ${uploadDate ? `<div class="meta-item">Published: ${uploadDate}</div>` : ''}
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
            loadRandomBook();
            return;
        }
        
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
                document.getElementById('previous-button').disabled = previousBooks.length === 0;
            } else {
                document.getElementById('current-audiobook').innerHTML = `
                    <div class="no-results fade-in">
                        <i class="search-icon"></i>
                        <h3>No matching audiobooks found</h3>
                        <p>We couldn't find any audiobooks matching "${searchTerm}"</p>
                        <button id="try-random" class="control-button">Try a random book instead</button>
                    </div>`;
                
                // Add event listener for the "try random" button
                document.getElementById('try-random').addEventListener('click', loadRandomBook);
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
        if (!seconds) return "Unknown duration";
        
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
});