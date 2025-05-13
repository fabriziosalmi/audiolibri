// Plugin Tailwind per ottimizzazioni mobile avanzate
const plugin = require('tailwindcss/plugin')

module.exports = plugin(function({ addComponents, addUtilities, theme, e }) {
  // Aggiunta di componenti specifici per mobile
  addComponents({
    // Container ottimizzato per mobile
    '.mobile-container': {
      width: '100%',
      maxWidth: '100%',
      padding: '0 0.5rem',
      margin: '0 auto',
      overflowX: 'hidden',
      '@screen sm': {
        padding: '0 0.75rem',
      },
      '@screen md': {
        padding: '0 1rem',
      }
    },
    
    // Card ottimizzate per mobile
    '.mobile-card': {
      display: 'flex',
      flexDirection: 'column',
      borderRadius: theme('borderRadius.lg', '0.5rem'),
      overflow: 'hidden',
      backgroundColor: 'var(--card-background, #ffffff)',
      boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)',
      border: '1px solid var(--border-color, #e2e8f0)',
      transition: 'transform 0.2s ease, box-shadow 0.2s ease',
      WebkitTapHighlightColor: 'transparent',
      '@media (hover: hover)': {
        '&:hover': {
          transform: 'translateY(-2px)',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
        }
      },
      '@media (hover: none)': {
        '&:active': {
          transform: 'scale(0.98)',
        }
      }
    },
    
    // Contenitore scrollabile orizzontale
    '.mobile-scroll': {
      display: 'flex',
      overflowX: 'auto',
      overflowY: 'hidden',
      WebkitOverflowScrolling: 'touch',
      scrollbarWidth: 'none',
      scrollSnapType: 'x mandatory',
      scrollBehavior: 'smooth',
      padding: '0.5rem 0',
      margin: '0 -0.5rem',
      '&::-webkit-scrollbar': {
        display: 'none'
      },
      '> *': {
        flex: '0 0 auto',
        scrollSnapAlign: 'start',
        marginRight: '0.75rem'
      }
    },
    
    // Bottoni touch-friendly
    '.mobile-button': {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '0.5rem 1rem',
      borderRadius: '0.375rem',
      fontWeight: '500',
      backgroundColor: 'var(--primary-color, #4a6cf7)',
      color: 'white',
      transition: 'transform 0.1s ease, background-color 0.2s ease',
      userSelect: 'none',
      touchAction: 'manipulation',
      '&:active': {
        transform: 'scale(0.96)',
      }
    },
    
    // Bottom navigation
    '.mobile-bottom-nav': {
      position: 'fixed',
      bottom: '0',
      left: '0',
      right: '0',
      display: 'flex',
      justifyContent: 'space-around',
      alignItems: 'center',
      padding: '0.5rem 0',
      backgroundColor: 'var(--card-background, #ffffff)',
      borderTop: '1px solid var(--border-color, #e2e8f0)',
      zIndex: '50',
      boxShadow: '0 -1px 3px rgba(0, 0, 0, 0.1)',
      paddingBottom: 'env(safe-area-inset-bottom, 0.5rem)'
    },
    
    // Nav item
    '.mobile-nav-item': {
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '0.25rem 0.5rem',
      fontSize: '0.75rem',
      color: 'var(--secondary-text, #64748b)',
      '&.active': {
        color: 'var(--primary-color, #4a6cf7)'
      }
    }
  })
  
  // Aggiunta di utility per mobile
  addUtilities({
    // Touch action utilities
    '.touch-none': { touchAction: 'none' },
    '.touch-manipulation': { touchAction: 'manipulation' },
    '.touch-pan-x': { touchAction: 'pan-x' },
    '.touch-pan-y': { touchAction: 'pan-y' },
    
    // Tap highlight utilities
    '.tap-highlight-none': { WebkitTapHighlightColor: 'transparent' },
    '.tap-highlight-light': { WebkitTapHighlightColor: 'rgba(0, 0, 0, 0.1)' },
    
    // Scrolling utilities
    '.scroll-snap-x': { scrollSnapType: 'x mandatory' },
    '.scroll-snap-y': { scrollSnapType: 'y mandatory' },
    '.scroll-snap-none': { scrollSnapType: 'none' },
    '.scroll-snap-start': { scrollSnapAlign: 'start' },
    '.scroll-snap-center': { scrollSnapAlign: 'center' },
    '.scroll-snap-end': { scrollSnapAlign: 'end' },
    
    // Text utilities for mobile
    '.text-truncate': {
      overflow: 'hidden',
      textOverflow: 'ellipsis',
      whiteSpace: 'nowrap'
    },
    
    // Miglioramento iOS
    '.ios-momentum-scroll': { WebkitOverflowScrolling: 'touch' },
    '.ios-safe-area-top': { paddingTop: 'env(safe-area-inset-top, 0)' },
    '.ios-safe-area-bottom': { paddingBottom: 'env(safe-area-inset-bottom, 0)' },
    '.ios-safe-area-left': { paddingLeft: 'env(safe-area-inset-left, 0)' },
    '.ios-safe-area-right': { paddingRight: 'env(safe-area-inset-right, 0)' }
  })
})