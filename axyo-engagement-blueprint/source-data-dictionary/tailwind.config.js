/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      /* example brand colour — delete or add more */
      colors: {
        'brand-iris': '#0D0DB7',
      },
    },
  },
  plugins: [],
};
