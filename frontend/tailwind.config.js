/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: '#0f172a',
          accent: '#2563eb',
        },
      },
    },
  },
  plugins: [],
};
