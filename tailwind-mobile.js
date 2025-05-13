// Tailwind Dynamic Integration for Mobile
document.addEventListener('DOMContentLoaded', () => {
    // Identifica dispositivo e browser
    const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
    const isSafari = /^((?!chrome|android).)*safari/i.test(navigator.userAgent);
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    
    // Aggiungi classi al body per selettori CSS specifici
    if (isIOS) document.body.classList.add('ios-device');
    if (isSafari) document.body.classList.add('safari-browser');
    if (isMobile) document.body.classList.add('mobile-device');
    
    // Applica classi Tailwind in modo dinamico
    applyTailwindClasses();
    
    // Aggiungi supporto per safe area insets di iOS
    applySafeAreaInsets();
    
    // Converti elementi esistenti in componenti Tailwind
    convertToTailwindComponents();
    
    // Aggiorna le classi quando cambia l'orientamento
    window.addEventListener('resize', debounce(() => {
        applyTailwindClasses();
    }, 250));
});

// Applica classi Tailwind in base al contesto
function applyTailwindClasses() {
    const isSmallMobile = window.innerWidth <= 480;
    const isMobilePortrait = window.innerWidth < window.innerHeight;
    
    // Converti i container principali
    document.querySelectorAll('.main-container, .content-container').forEach(container => {
        if (isSmallMobile) {
            container.classList.add('tw-mobile-container');
            container.classList.add('ios-safe-container');
        }
    });
    
    // Ottimizza griglia per visualizzazione portrait/landscape
    document.querySelectorAll('.audiobook-grid').forEach(grid => {
        if (isSmallMobile) {
            if (isMobilePortrait) {
                grid.classList.add('tw-mobile-card-grid');
            } else {
                grid.classList.add('tw-grid-autofit-sm');
            }
        }
    });
    
    // Aggiungi classi per la navigazione mobile
    document.querySelectorAll('.genre-list').forEach(list => {
        list.classList.add('tw-mobile-pills');
        list.classList.add('ios-momentum-scroll');
    });
    
    // Migliora button e pills
    document.querySelectorAll('.genre-pill').forEach(pill => {
        pill.classList.add('ios-tap-effect');
        pill.classList.add('touch-manipulation');
    });
}

// Applica insets per notch e UI di sistema
function applySafeAreaInsets() {
    const header = document.querySelector('.site-header');
    if (header) {
        header.style.paddingTop = 'env(safe-area-inset-top, 10px)';
    }
    
    const footer = document.querySelector('.site-footer');
    if (footer) {
        footer.style.paddingBottom = 'env(safe-area-inset-bottom, 10px)';
    }
}

// Converti elementi esistenti in componenti Tailwind
function convertToTailwindComponents() {
    // Converti bottoni in stile iOS
    document.querySelectorAll('.primary-button').forEach(button => {
        button.classList.add('tw-ios-button');
    });
    
    // Converti card in stile iOS
    document.querySelectorAll('.audiobook-card').forEach(card => {
        card.classList.add('tw-ios-card');
    });
    
    // Converti badge/pills
    document.querySelectorAll('.badge, .tag, .pill').forEach(badge => {
        badge.classList.add('tw-ios-badge');
    });
    
    // Migliora liste
    document.querySelectorAll('.list-container').forEach(list => {
        list.classList.add('tw-ios-list');
        
        // Aggiunge classi ai figli
        list.querySelectorAll('li, .list-item').forEach(item => {
            item.classList.add('tw-ios-list-item');
        });
    });
}

// Funzione per debouncing (prevenire troppe chiamate)
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
