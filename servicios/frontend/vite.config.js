import react from '@vitejs/plugin-react'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import { securityHeaders } from './security-policy.js'

// ============================================================
// IAM SECURE - Configuración de Vite
// ============================================================
// El servidor escucha en todas las interfaces para permitir
// demostraciones desde otro equipo de la misma red.
//
// La URL del backend NO se fija aquí. App.jsx utiliza
// VITE_API_URL cuando está definida y, en su ausencia, deriva
// el host del navegador y utiliza el puerto 8003.
// ============================================================

export default defineConfig({
  plugins: [react()],
  build: {
    rolldownOptions: {
      input: {
        panel: fileURLToPath(new URL('./index.html', import.meta.url)),
        permissions: fileURLToPath(new URL('./permissions.html', import.meta.url)),
      },
    },
  },

  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
  },

  preview: {
    headers: securityHeaders(),
    // Acceso desde ZAP en Docker Desktop; mantener lista explicita.
    allowedHosts: ['host.docker.internal'],
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
  },
})