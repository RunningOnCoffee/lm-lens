/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        surface: {
          900: '#0d0f14',
          800: '#141720',
          700: '#1c2030',
          600: '#252a3a',
        },
        accent: {
          DEFAULT: '#00d4ff',
          dim: '#00a3c7',
          bright: '#40e0ff',
        },
        warn: '#f59e0b',
        danger: '#ef4444',
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'monospace'],
        heading: ['Outfit', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
