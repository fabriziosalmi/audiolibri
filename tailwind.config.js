/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./offline.html",
    "./app.js",
    "./mobile-enhancements.js",
    "./tailwind-mobile.css",
    "./tailwind-mobile.js"
  ],
  darkMode: 'media', // Mantiene la modalità dark basata sulle preferenze del sistema
  theme: {
    screens: {
        'xs': '320px',  // Extra small devices (mobiles)
        'sm': '480px',  // Small devices (larger phones, small tablets)
        'md': '768px',  // Medium devices (tablets)
        'lg': '1024px', // Large devices (desktops)
        'xl': '1280px', // Extra large devices (large desktops)
        '2xl': '1536px' // Ultra wide screens
      },
      spacing: {
        'safe-top': 'env(safe-area-inset-top)',
        'safe-bottom': 'env(safe-area-inset-bottom)',
        'safe-left': 'env(safe-area-inset-left)',
        'safe-right': 'env(safe-area-inset-right)',
      },
    extend: {
      colors: {
        // Light theme colors
        'background': '#f5f7fa',
        'text': '#2d3748',
        'card': '#ffffff',
        'border': '#e2e8f0',
        'primary': '#4a6cf7',
        'primary-hover': '#3a56d4',
        'accent': '#10b981',
        'accent-hover': '#059669',
        'danger': '#ef4444',
        'danger-hover': '#dc2626',
        'header': '#1e293b',
        'secondary-text': '#64748b',
        'placeholder': '#f8fafc',
        'tag': '#e2e8f0',
        'tag-text': '#4a5568',
        'progress': '#e2e8f0',
        'progress-fill': '#4a6cf7',
        // Dark theme colors
        'dark-background': '#000000',
        'dark-text': '#e2e8f0',
        'dark-card': '#121212',
        'dark-border': '#2a2a2a',
        'dark-primary': '#ff4343',
        'dark-primary-hover': '#ff0000',
        'dark-accent': '#03dac6',
        'dark-accent-hover': '#00b3a6',
        'dark-danger': '#cf6679',
        'dark-danger-hover': '#b55464',
        'dark-header': '#ffffff',
        'dark-secondary-text': '#a0a0a0',
        'dark-placeholder': '#1e1e1e',
        'dark-tag': '#333333',
        'dark-tag-text': '#e0e0e0',
        'dark-progress': '#333333',
        'dark-progress-fill': '#bb86fc',
      },
      boxShadow: {
        'card': '0 10px 25px rgba(0,0,0,0.05)',
        'card-dark': '0 10px 25px rgba(0,0,0,0.4)',
      },
      fontFamily: {
        'sans': ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Oxygen', 'Ubuntu', 'Cantarell', 'sans-serif'],
      },
      /* Tailwind Utilities Extension */
        /* Touch interaction utilities */
        touchAction: {
          'manipulation': 'manipulation',
          'none': 'none',
        },
        /* CSS scroll snap utilities */
        scrollSnapType: {
          'x': 'x var(--tw-scroll-snap-strictness)',
          'y': 'y var(--tw-scroll-snap-strictness)',
          'mandatory': 'both mandatory',
          'proximity': 'both proximity',
        },
        scrollSnapStrictness: {
          'mandatory': 'mandatory',
          'proximity': 'proximity',
        },
        scrollSnapAlign: {
          'start': 'start',
          'end': 'end',
          'center': 'center',
        },
        scrollSnapStop: {
          'normal': 'normal',
          'always': 'always',
        },
        /* Animation utilities for mobile */
        scale: {
          '95': '0.95',
          '98': '0.98',
        },
      },
    },
  },
  plugins: [
    require('./tailwind-mobile-plugin.js'),
  ],
};