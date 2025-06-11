// Mobile UI enhancements with Tailwind integration - EN 301 549 Compliant
document.addEventListener('DOMContentLoaded', () => {
    // Apply Tailwind classes dynamically based on screen size
    applyResponsiveTailwindClasses();
    
    // Optimize for mobile touch
    enhanceTouchInteractions();
    
    // Setup responsive behaviors
    setupResponsiveBehaviors();
    
    // EN 301 549: Initialize accessibility features
    initializeAccessibilityFeatures();
    
    // Listen for resize events with debouncing
    window.addEventListener('resize', debounce(() => {
        applyResponsiveTailwindClasses();
    }, 250));
});

// EN 301 549: Initialize accessibility features
function initializeAccessibilityFeatures() {
    // Create announcement region for screen readers
    const announceRegion = document.createElement('div');
    announceRegion.setAttribute('aria-live', 'polite');
    announceRegion.setAttribute('aria-atomic', 'true');
    announceRegion.className = 'tw-sr-only';
    announceRegion.id = 'mobile-announce-region';
    document.body.appendChild(announceRegion);
    
    // Function to announce to screen readers
    window.mobileAnnounce = function(message) {
        announceRegion.textContent = message;
        setTimeout(() => {
            announceRegion.textContent = '';
        }, 1000);
    };
    
    // Add keyboard navigation support for mobile elements
    setupMobileKeyboardNavigation();
    
    // Monitor for orientation changes and announce them
    window.addEventListener('orientationchange', () => {
        setTimeout(() => {
            const orientation = screen.orientation?.angle === 90 || screen.orientation?.angle === 270 
                ? 'orizzontale' : 'verticale';
            mobileAnnounce(`Orientamento cambiato in ${orientation}`);
        }, 500);
    });
}

// EN 301 549: Keyboard navigation for mobile elements
function setupMobileKeyboardNavigation() {
    // Enhanced keyboard support for mobile navigation
    document.addEventListener('keydown', (e) => {
        const activeElement = document.activeElement;
        
        // Handle arrow key navigation in horizontal scrollers
        if (activeElement && activeElement.closest('.tw-mobile-scroll')) {
            const container = activeElement.closest('.tw-mobile-scroll');
            const items = container.querySelectorAll('.tw-mobile-scroll-item, .scroll-item');
            const currentIndex = Array.from(items).indexOf(activeElement);
            
            switch (e.key) {
                case 'ArrowRight':
                    e.preventDefault();
                    if (currentIndex < items.length - 1) {
                        items[currentIndex + 1].focus();
                        items[currentIndex + 1].scrollIntoView({ behavior: 'smooth', inline: 'center' });
                    }
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    if (currentIndex > 0) {
                        items[currentIndex - 1].focus();
                        items[currentIndex - 1].scrollIntoView({ behavior: 'smooth', inline: 'center' });
                    }
                    break;
                case 'Home':
                    e.preventDefault();
                    if (items.length > 0) {
                        items[0].focus();
                        items[0].scrollIntoView({ behavior: 'smooth', inline: 'center' });
                    }
                    break;
                case 'End':
                    e.preventDefault();
                    if (items.length > 0) {
                        items[items.length - 1].focus();
                        items[items.length - 1].scrollIntoView({ behavior: 'smooth', inline: 'center' });
                    }
                    break;
            }
        }
    });
}

// Apply Tailwind classes based on screen size
function applyResponsiveTailwindClasses() {
    const isMobile = window.innerWidth <= 768;
    const isSmallMobile = window.innerWidth <= 480;
    
    // Target the main content container
    const mainContainer = document.querySelector('.main-container');
    if (mainContainer) {
        if (isMobile) {
            // Add mobile Tailwind classes
            mainContainer.classList.add('px-2', 'max-w-full');
            mainContainer.classList.remove('px-4', 'px-6');
        } else {
            // Revert to desktop classes
            mainContainer.classList.remove('px-2', 'max-w-full');
            mainContainer.classList.add('px-4');
        }
    }
    
    // Optimize the audiobook grid for mobile
    const audiobookGrid = document.querySelector('.audiobook-grid');
    if (audiobookGrid) {
        if (isSmallMobile) {
            // 2 columns for very small screens
            audiobookGrid.classList.add('grid-cols-2', 'gap-2');
            audiobookGrid.classList.remove('grid-cols-3', 'grid-cols-4', 'gap-4', 'gap-6');
        } else if (isMobile) {
            // 3 columns for larger mobile screens
            audiobookGrid.classList.add('grid-cols-3', 'gap-3');
            audiobookGrid.classList.remove('grid-cols-2', 'grid-cols-4', 'gap-2', 'gap-6');
        } else {
            // Default desktop grid
            audiobookGrid.classList.add('grid-cols-4', 'gap-4');
            audiobookGrid.classList.remove('grid-cols-2', 'grid-cols-3', 'gap-2', 'gap-3');
        }
    }
    
    // Apply touch-optimized classes to buttons on mobile
    const actionButtons = document.querySelectorAll('.action-button');
    actionButtons.forEach(button => {
        if (isMobile) {
            button.classList.add('py-2', 'active:scale-95', 'touch-manipulation');
            button.classList.remove('py-3');
        } else {
            button.classList.remove('py-2', 'active:scale-95', 'touch-manipulation');
            button.classList.add('py-3');
        }
    });
}

// Enhance touch interactions for mobile devices
function enhanceTouchInteractions() {
    // Add touch-action: manipulation to prevent delays
    document.querySelectorAll('a, button, .clickable').forEach(element => {
        element.style.touchAction = 'manipulation';
    });
    
    // Add active state for touch feedback
    document.querySelectorAll('.genre-pill, .audiobook-card, .action-button').forEach(element => {
        element.addEventListener('touchstart', () => {
            element.classList.add('active');
        }, { passive: true });
        
        element.addEventListener('touchend', () => {
            element.classList.remove('active');
        }, { passive: true });
    });
}

// Setup responsive behaviors
function setupResponsiveBehaviors() {
    // Check for iOS device to apply special iOS fixes
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    if (isIOS) {
        document.documentElement.classList.add('ios-device');
        document.body.classList.add('ios-body');
        
        // Aggiungi classi iOS specifiche ai contenitori
        document.querySelectorAll('.mobile-categories-container').forEach(container => {
            container.classList.add('ios-scroll', 'ios-momentum-scroll');
        });
        
        document.querySelectorAll('.genre-pill').forEach(pill => {
            pill.classList.add('tap-highlight-none', 'ios-touch-target');
        });
        
        document.querySelectorAll('button, a').forEach(element => {
            element.classList.add('tap-highlight-none');
        });
        
        // Fix for iOS momentum scrolling in overflow containers
        document.querySelectorAll('.scroll-container, .mobile-scroll').forEach(container => {
            container.classList.add('ios-momentum-scroll');
        });
    }
    
    // Setup scroll containers with snap points
    document.querySelectorAll('.horizontal-scroll').forEach(container => {
        // Apply Tailwind scroll snap classes
        container.classList.add('snap-x', 'snap-mandatory', 'scroll-smooth');
        
        // Add snap alignment to children
        container.querySelectorAll('.scroll-item').forEach(item => {
            item.classList.add('snap-start');
        });
    });
}

// Debounce utility for resize events
function debounce(func, delay) {
    let timeout;
    return function() {
        const context = this;
        const args = arguments;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), delay);
    };
}
