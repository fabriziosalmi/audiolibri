// Additional mobile genre navigation enhancements

document.addEventListener('DOMContentLoaded', () => {
    // Fix for shadow rendering on mobile devices
    fixMobileShadowRendering();
    
    // Listen for orientation changes
    window.addEventListener('orientationchange', () => {
        // Small delay to let the orientation change complete
        setTimeout(() => {
            updateGenrePillsForMobile();
        }, 200);
    });
    
    // Also check on initial load and resize
    updateGenrePillsForMobile();
    window.addEventListener('resize', debounce(updateGenrePillsForMobile, 250));
    
    // Initialize EN 301 549 compliant features
    initEN301549Features();
});

// Function to fix shadow rendering issues on mobile
function fixMobileShadowRendering() {
    // Check if we're on a mobile device with potential shadow rendering issues
    const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    
    if (isMobile) {
        // Add a special class to the body for targeting
        document.body.classList.add('mobile-device');
        
        // Force a reflow of genre pills to fix shadow rendering
        document.querySelectorAll('.genre-pill').forEach(pill => {
            // Add a small delay to ensure rendering is complete
            setTimeout(() => {
                pill.style.transform = 'translateZ(0)';
            }, 100);
        });
    }
}

// Function to update genre pills for optimal mobile display
function updateGenrePillsForMobile() {
    const isPortrait = window.innerHeight > window.innerWidth;
    const isSmallScreen = window.innerWidth <= 480;
    
    // Add appropriate classes to body
    if (isPortrait && isSmallScreen) {
        document.body.classList.add('portrait-mobile');
    } else {
        document.body.classList.remove('portrait-mobile');
    }
    
    // Get all genre pills and optimize for mobile if needed
    const genrePills = document.querySelectorAll('.genre-pill');
    
    if (isSmallScreen) {
        genrePills.forEach(pill => {
            const genreName = pill.querySelector('.genre-name');
            const genreCount = pill.querySelector('.genre-count');
            
            // Ensure text doesn't overflow by adding ellipsis if needed
            if (genreName && genreName.scrollWidth > genreName.clientWidth) {
                genreName.title = genreName.textContent; // Add tooltip with full text
            }
        });
    }
}

// Simple debounce function to limit function calls
function debounce(func, wait) {
    let timeout;
    return function() {
        const context = this;
        const args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(() => {
            func.apply(context, args);
        }, wait);
    };
}

// EN 301 549: Initialize European accessibility standard features
function initEN301549Features() {
    // Enhanced keyboard navigation for European accessibility requirements
    initEuropeanKeyboardNavigation();
    
    // Cognitive accessibility features
    initCognitiveAccessibility();
    
    // Multi-language support preparation
    initInternationalizationSupport();
    
    // Enhanced error handling and user guidance
    initErrorHandlingEnhancements();
}

// EN 301 549: European keyboard navigation standards
function initEuropeanKeyboardNavigation() {
    // Add keyboard shortcuts info panel
    const shortcutsInfo = document.createElement('div');
    shortcutsInfo.id = 'keyboard-shortcuts-info';
    shortcutsInfo.className = 'sr-only';
    shortcutsInfo.setAttribute('aria-live', 'polite');
    shortcutsInfo.innerHTML = `
        <div>Scorciatoie da tastiera disponibili:
        Alt+M: Menu principale,
        Alt+S: Ricerca,
        Spazio: Riproduci/Pausa,
        Frecce: Navigazione,
        Esc: Chiudi dialoghi</div>
    `;
    document.body.appendChild(shortcutsInfo);
    
    // Help shortcut (Alt+H) to announce available shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.altKey && e.key === 'h') {
            e.preventDefault();
            announceKeyboardShortcuts();
        }
        
        // Alt+M for main menu/navigation
        if (e.altKey && e.key === 'm') {
            e.preventDefault();
            focusMainNavigation();
        }
        
        // Alt+S for search
        if (e.altKey && e.key === 's') {
            e.preventDefault();
            focusSearchInput();
        }
    });
}

// EN 301 549: Cognitive accessibility features
function initCognitiveAccessibility() {
    // Add session timeout warning (required for European accessibility)
    let sessionTimeoutWarning = null;
    let sessionTimer = null;
    
    function resetSessionTimer() {
        if (sessionTimer) clearTimeout(sessionTimer);
        if (sessionTimeoutWarning) {
            sessionTimeoutWarning.remove();
            sessionTimeoutWarning = null;
        }
        
        // Set 20-minute warning (EU requirement for session timeouts)
        sessionTimer = setTimeout(() => {
            showSessionTimeoutWarning();
        }, 20 * 60 * 1000); // 20 minutes
    }
    
    function showSessionTimeoutWarning() {
        sessionTimeoutWarning = document.createElement('div');
        sessionTimeoutWarning.className = 'session-timeout-warning';
        sessionTimeoutWarning.setAttribute('role', 'alert');
        sessionTimeoutWarning.setAttribute('aria-live', 'assertive');
        sessionTimeoutWarning.innerHTML = `
            <div class="timeout-content">
                <h3>Avviso di Sessione</h3>
                <p>La tua sessione scadrà tra 10 minuti per inattività.</p>
                <button onclick="extendSession()" class="extend-session-btn">
                    Estendi Sessione
                </button>
                <button onclick="dismissTimeoutWarning()" class="dismiss-btn">
                    Continua
                </button>
            </div>
        `;
        document.body.appendChild(sessionTimeoutWarning);
        
        // Focus on extend session button
        setTimeout(() => {
            sessionTimeoutWarning.querySelector('.extend-session-btn').focus();
        }, 100);
    }
    
    // Global functions for session management
    window.extendSession = function() {
        if (sessionTimeoutWarning) {
            sessionTimeoutWarning.remove();
            sessionTimeoutWarning = null;
        }
        resetSessionTimer();
        if (window.announceToScreenReader) {
            announceToScreenReader('Sessione estesa con successo');
        }
    };
    
    window.dismissTimeoutWarning = function() {
        if (sessionTimeoutWarning) {
            sessionTimeoutWarning.remove();
            sessionTimeoutWarning = null;
        }
    };
    
    // Reset timer on user activity
    ['click', 'keydown', 'scroll', 'touchstart'].forEach(event => {
        document.addEventListener(event, resetSessionTimer, { passive: true });
    });
    
    // Initial timer start
    resetSessionTimer();
}

// EN 301 549: Internationalization support preparation
function initInternationalizationSupport() {
    // Detect browser language and announce if different from content
    const browserLang = navigator.language.split('-')[0];
    const contentLang = document.documentElement.lang;
    
    if (browserLang !== contentLang && browserLang !== 'it') {
        // Announce language mismatch for screen readers
        setTimeout(() => {
            if (window.announceToScreenReader) {
                announceToScreenReader(`Contenuto in italiano, lingua del browser: ${browserLang}`);
            }
        }, 2000);
    }
    
    // Add language switching capability (for future expansion)
    const langSwitcher = document.createElement('div');
    langSwitcher.id = 'language-switcher';
    langSwitcher.className = 'sr-only'; // Hidden for now, can be made visible later
    langSwitcher.innerHTML = `
        <label for="lang-select">Seleziona lingua:</label>
        <select id="lang-select" aria-label="Selezione lingua del sito">
            <option value="it" selected>Italiano</option>
            <option value="en" disabled>English (coming soon)</option>
            <option value="fr" disabled>Français (coming soon)</option>
            <option value="de" disabled>Deutsch (coming soon)</option>
            <option value="es" disabled>Español (coming soon)</option>
        </select>
    `;
    
    // Add to page (hidden for now)
    document.body.appendChild(langSwitcher);
}

// EN 301 549: Enhanced error handling
function initErrorHandlingEnhancements() {
    // Global error handler with accessibility announcements
    window.addEventListener('error', (e) => {
        console.error('Application error:', e.error);
        
        // Announce error to screen readers
        if (window.announceToScreenReader) {
            announceToScreenReader('Si è verificato un errore. Prova a ricaricare la pagina.');
        }
        
        // Show user-friendly error message
        showAccessibleErrorMessage('Errore dell\'applicazione', 
            'Si è verificato un errore tecnico. Ricarica la pagina o contatta il supporto se il problema persiste.');
    });
    
    // Promise rejection handler
    window.addEventListener('unhandledrejection', (e) => {
        console.error('Unhandled promise rejection:', e.reason);
        if (window.announceToScreenReader) {
            announceToScreenReader('Errore di caricamento. Verifica la connessione.');
        }
    });
}

// EN 301 549: Accessible error message display
function showAccessibleErrorMessage(title, message) {
    const errorDialog = document.createElement('div');
    errorDialog.className = 'accessible-error-dialog';
    errorDialog.setAttribute('role', 'alertdialog');
    errorDialog.setAttribute('aria-labelledby', 'error-title');
    errorDialog.setAttribute('aria-describedby', 'error-message');
    errorDialog.innerHTML = `
        <div class="error-dialog-content">
            <h2 id="error-title">${title}</h2>
            <p id="error-message">${message}</p>
            <div class="error-actions">
                <button onclick="location.reload()" class="primary-action">
                    Ricarica Pagina
                </button>
                <button onclick="this.closest('.accessible-error-dialog').remove()" class="secondary-action">
                    Chiudi
                </button>
            </div>
        </div>
        <div class="error-backdrop"></div>
    `;
    
    document.body.appendChild(errorDialog);
    
    // Focus on primary action
    setTimeout(() => {
        errorDialog.querySelector('.primary-action').focus();
    }, 100);
    
    // ESC key to close
    const escHandler = (e) => {
        if (e.key === 'Escape') {
            errorDialog.remove();
            document.removeEventListener('keydown', escHandler);
        }
    };
    document.addEventListener('keydown', escHandler);
}

// Helper functions for keyboard shortcuts
function announceKeyboardShortcuts() {
    const shortcuts = document.getElementById('keyboard-shortcuts-info');
    if (shortcuts && window.announceToScreenReader) {
        announceToScreenReader(shortcuts.textContent);
    }
}

function focusMainNavigation() {
    const nav = document.querySelector('nav, [role="navigation"], header');
    if (nav) {
        nav.focus();
        if (window.announceToScreenReader) {
            announceToScreenReader('Navigazione principale attivata');
        }
    }
}

function focusSearchInput() {
    const searchInput = document.getElementById('search') || document.querySelector('input[type="search"]');
    if (searchInput) {
        searchInput.focus();
        if (window.announceToScreenReader) {
            announceToScreenReader('Campo di ricerca attivato');
        }
    }
}
