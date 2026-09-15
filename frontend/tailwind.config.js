/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Brand accent used for the primary button, links and highlights.
        brand: {
          50: '#eef2ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#1e1b4b',
        },
        // Deep structural navy for the header / high-contrast surfaces.
        navy: {
          50: '#f0f3fa',
          100: '#dbe2f0',
          400: '#3d4f74',
          500: '#293a5c',
          600: '#1c2b4a',
          700: '#15213a',
          800: '#0f1729',
          900: '#0a0f1d',
          950: '#060911',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'Helvetica Neue',
          'Arial',
          'sans-serif',
        ],
      },
      boxShadow: {
        card: '0 1px 2px 0 rgb(15 23 42 / 0.04), 0 4px 16px -4px rgb(15 23 42 / 0.08)',
        elevated: '0 12px 28px -8px rgb(15 23 42 / 0.20), 0 2px 8px -2px rgb(15 23 42 / 0.08)',
        glow: '0 0 0 1px rgb(79 70 229 / 0.12), 0 10px 24px -6px rgb(79 70 229 / 0.45)',
      },
      keyframes: {
        fadeIn: { '0%': { opacity: 0 }, '100%': { opacity: 1 } },
        slideUp: {
          '0%': { opacity: 0, transform: 'translateY(10px)' },
          '100%': { opacity: 1, transform: 'translateY(0)' },
        },
      },
      animation: {
        'fade-in': 'fadeIn 0.35s ease-out both',
        'slide-up': 'slideUp 0.4s cubic-bezier(0.16,1,0.3,1) both',
      },
    },
  },
  plugins: [],
}
