/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        bg: '#050e0e',
        surface: '#0e2a1e',
        'surface-2': '#122e22',
        'surface-elevated': '#112b1e',
        gold: '#c9a84c',
        'gold-light': '#e0bc6a',
        cream: '#f0ede0',
        'cream-dim': 'rgba(240,237,224,0.55)',
        'cream-muted': 'rgba(240,237,224,0.3)',
        muted: '#7a9a82',
      },
      fontFamily: {
        display: ['Cinzel Decorative', 'serif'],
        body: ['DM Sans', 'sans-serif'],
        arabic: ['Noto Naskh Arabic', 'serif'],
      },
      boxShadow: {
        gold: '0 0 20px rgba(201,168,76,0.2)',
        'gold-sm': '0 0 16px rgba(201,168,76,0.2)',
      },
    },
  },
  plugins: [],
};
