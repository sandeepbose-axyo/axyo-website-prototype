import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  // THIS is the important part ↓
  base: './',
  plugins: [react()],
})

