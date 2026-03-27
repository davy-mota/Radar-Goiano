/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        darkBg: '#0E1117',
        darkCard: '#1A1C23',
        darkBorder: '#2E323E',
        neonCyan: '#00D4FF',
        neonPurple: '#8A2BE2'
      }
    },
  },
  plugins: [],
}