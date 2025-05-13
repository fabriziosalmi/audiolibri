// Enhanced mobile navigation script

document.addEventListener('DOMContentLoaded', () => {
    initEnhancedMobileNavigation();
});

function initEnhancedMobileNavigation() {
    // Wait for the mobile categories container to be available
    const checkForContainer = setInterval(() => {
        const mobileContainer = document.querySelector('.mobile-categories-container');
        if (mobileContainer) {
            clearInterval(checkForContainer);
            setupMobileNavigation(mobileContainer);
        }
    }, 100);
}

function setupMobileNavigation(container) {
    // Enhanced scroll event tracking
    container.addEventListener('scroll', function() {
        handleScrollIndicators(this);
    });
    
    // Initial check
    handleScrollIndicators(container);
    
    // Handle swipe gestures for better navigation
    setupSwipeNavigation(container);
    
    // Add button to scroll to start
    addNavigationControls(container);
    
    // Check if scroll is needed, hide gradients if not
    checkIfScrollNeeded(container);
    
    // Recheck on window resize and orientation change
    window.addEventListener('resize', () => {
        checkIfScrollNeeded(container);
    });
    
    window.addEventListener('orientationchange', () => {
        // Small delay to let the orientation change complete
        setTimeout(() => {
            checkIfScrollNeeded(container);
        }, 100);
    });
    
    // Initial orientation check
    checkIfScrollNeeded(container);
}

function handleScrollIndicators(container) {
    // Show left gradient when scrolled
    if (container.scrollLeft > 10) {
        container.classList.add('scrolled-right');
    } else {
        container.classList.remove('scrolled-right');
    }
    
    // Check if we're at the end of scroll
    const isAtEnd = container.scrollWidth - container.scrollLeft <= container.clientWidth + 5;
    if (isAtEnd) {
        container.classList.add('scrolled-end');
    } else {
        container.classList.remove('scrolled-end');
    }
}

function setupSwipeNavigation(container) {
    let touchStartX = 0;
    let initialScrollLeft = 0;
    
    container.addEventListener('touchstart', (e) => {
        touchStartX = e.touches[0].clientX;
        initialScrollLeft = container.scrollLeft;
        container.classList.add('touching');
    }, { passive: true });
    
    container.addEventListener('touchend', () => {
        container.classList.remove('touching');
    }, { passive: true });
}

function addNavigationControls(container) {
    // Only add navigation for wider screens where many genres might be off-screen
    if (window.innerWidth >= 480) {
        const genreList = container.querySelector('.genre-list');
        if (genreList && genreList.children.length > 5) {
            const scrollRightBtn = document.createElement('button');
            scrollRightBtn.className = 'mobile-nav-control right-nav';
            scrollRightBtn.setAttribute('aria-label', 'Scroll right');
            scrollRightBtn.innerHTML = '<span>›</span>';
            
            scrollRightBtn.addEventListener('click', () => {
                container.scrollBy({ left: 200, behavior: 'smooth' });
            });
            
            const scrollLeftBtn = document.createElement('button');
            scrollLeftBtn.className = 'mobile-nav-control left-nav';
            scrollLeftBtn.setAttribute('aria-label', 'Scroll left');
            scrollLeftBtn.innerHTML = '<span>‹</span>';
            
            scrollLeftBtn.addEventListener('click', () => {
                container.scrollBy({ left: -200, behavior: 'smooth' });
            });
            
            // Add them to the DOM
            const navParent = container.parentElement;
            navParent.style.position = 'relative';
            navParent.appendChild(scrollLeftBtn);
            navParent.appendChild(scrollRightBtn);
            
            // Update visibility based on scroll position
            container.addEventListener('scroll', () => {
                updateNavigationControlsVisibility(container, scrollLeftBtn, scrollRightBtn);
            });
            
            // Initial visibility check
            updateNavigationControlsVisibility(container, scrollLeftBtn, scrollRightBtn);
        }
    }
}

function updateNavigationControlsVisibility(container, leftBtn, rightBtn) {
    // Show/hide left button based on scroll position
    if (container.scrollLeft > 10) {
        leftBtn.classList.add('visible');
    } else {
        leftBtn.classList.remove('visible');
    }
    
    // Show/hide right button based on if there's more to scroll
    const isAtEnd = container.scrollWidth - container.scrollLeft <= container.clientWidth + 5;
    if (isAtEnd) {
        rightBtn.classList.remove('visible');
    } else {
        rightBtn.classList.add('visible');
    }
}

function checkIfScrollNeeded(container) {
    const genreList = container.querySelector('.genre-list');
    if (genreList) {
        // If all content fits without scrolling, hide the gradients
        if (genreList.scrollWidth <= container.clientWidth) {
            container.classList.add('no-scroll-needed');
        } else {
            container.classList.remove('no-scroll-needed');
        }
        
        // Add portrait mode class for additional styling
        if (window.innerWidth <= 480) {
            container.classList.add('portrait-mode');
            
            // Apply additional optimizations for portrait mode
            document.body.classList.add('portrait-screen');
            
            // Optimize genre pills for very small screens
            if (window.innerWidth < 360) {
                container.classList.add('very-small-screen');
            } else {
                container.classList.remove('very-small-screen');
            }
        } else {
            container.classList.remove('portrait-mode');
            document.body.classList.remove('portrait-screen');
        }
    }
}
