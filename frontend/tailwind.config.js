/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Rubik', 'Noto Sans KR', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          DEFAULT: '#1c1410',
          accent: '#c2622a',
          'accent-dark': '#a8511f',
          muted: '#fbeee6',
        },
        surface: '#faf8f5',
      },
    },
  },
  plugins: [],
};
