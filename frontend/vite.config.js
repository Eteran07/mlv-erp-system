import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/cuentas': 'http://127.0.0.1:8000',
      '/api': 'http://127.0.0.1:8000',
      '/verificar-tokens': 'http://127.0.0.1:8000',
      '/estado-progreso': 'http://127.0.0.1:8000',
      '/previsualizar': 'http://127.0.0.1:8000',
      '/publicar-lote': 'http://127.0.0.1:8000'
    }
  }
})
