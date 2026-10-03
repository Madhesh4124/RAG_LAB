/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'monospace'],
      },
      colors: {
        zinc: {
          950: '#09090b',
          900: '#121215',
          850: '#18181b',
          800: '#27272a',
          750: '#323238',
          700: '#3f3f46',
          600: '#52525b',
          500: '#71717a',
          400: '#a1a1aa',
          300: '#d4d4d8',
          200: '#e4e4e7',
          100: '#f4f4f5',
          50:  '#fafafa',
        },
        surface: {
          0: '#09090b',
          1: '#121215',
          2: '#18181b',
          3: '#222227',
          4: '#2a2a30',
        },
        accent: {
          amber:   '#f59e0b',
          'amber-hover': '#d97706',
          emerald: '#10b981',
          blue:    '#3b82f6',
          red:     '#ef4444',
          violet:  '#f59e0b',
          'violet-light': '#fbbf24',
        },
      },
      boxShadow: {
        'subtle': '0 1px 2px 0 rgba(0, 0, 0, 0.4)',
        'card': '0 1px 3px 0 rgba(0, 0, 0, 0.4), 0 1px 2px -1px rgba(0, 0, 0, 0.4)',
        'dropdown': '0 10px 25px -5px rgba(0, 0, 0, 0.7), 0 8px 10px -6px rgba(0, 0, 0, 0.7)',
      },
      letterSpacing: {
        tightest: '-0.035em',
        tighter:  '-0.025em',
        tight:    '-0.015em',
      },
    },
  },
  plugins: [],
}
