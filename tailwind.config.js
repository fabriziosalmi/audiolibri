/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./offline.html",
    "./app.js"
  ],
  darkMode: 'media', // Mantiene la modalità dark basata sulle preferenze del sistema
  theme: {
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
    },
  },
  plugins: [],
};