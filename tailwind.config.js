/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#EAB308', // Yellow-500
        dark: '#0A0A0A',
        card: '#141414',
      },
    },
  },
  plugins: [],
}
