// postcss.config.js  (ESM syntax because Vite uses ESM)
export default {
  plugins: {
    '@tailwindcss/postcss': {},   // ✅ new plugin name
    autoprefixer: {},
  },
};
