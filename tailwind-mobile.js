// Mobile UI enhancements with Tailwind integration
document.addEventListener('DOMContentLoaded', () => {
    // Apply Tailwind classes dynamically based on screen size
    applyResponsiveTailwindClasses();
    
    // Optimize for mobile touch
    enhanceTouchInteractions();
    
    // Setup responsive behaviors
    setupResponsiveBehaviors();
    
    // Listen for resize events with debouncing
    window.addEventListener('resize', debounce(() => {
        applyResponsiveTailwindClasses();
    }, 250));
});

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
