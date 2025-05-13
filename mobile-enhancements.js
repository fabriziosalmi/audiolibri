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
