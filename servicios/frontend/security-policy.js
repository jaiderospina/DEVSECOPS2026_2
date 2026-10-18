// Política compartida por Vite Preview y la imagen estática de Nginx.
// VITE_* contiene configuración pública; nunca credenciales de aplicación.
export function securityHeaders(env = process.env) {
  const apiOrigins = new Set([
    'http://localhost:8003', 'http://127.0.0.1:8003', 'http://host.docker.internal:8003',
    'http://localhost:8005', 'http://127.0.0.1:8005', 'http://host.docker.internal:8005',
  ])
  for (const name of ['VITE_API_URL', 'VITE_PERMISSIONS_API_URL']) {
    if (!env[name]?.trim()) continue
    const url = new URL(env[name].trim())
    if (!['http:', 'https:'].includes(url.protocol) ||
        url.username || url.password || url.search || url.hash) {
      throw new Error(name + ' debe ser una URL pública HTTP o HTTPS')
    }
    // Evita directivas/variables inyectadas en la configuración del servidor.
    if (/["\\\s$]/.test(url.origin)) throw new Error(name + ' contiene un origen no válido')
    apiOrigins.add(url.origin)
  }
  return {
    'Content-Security-Policy': [
      "default-src 'self'", "script-src 'self'", "style-src 'self'",
      "img-src 'self' data: blob:", "font-src 'self'",
      "connect-src 'self' " + [...apiOrigins].join(' '),
      "object-src 'none'", "base-uri 'self'", "form-action 'self'", "frame-ancestors 'none'",
    ].join('; '),
    'X-Frame-Options': 'DENY',
    'X-Content-Type-Options': 'nosniff',
    'Permissions-Policy': 'camera=(), microphone=(), geolocation=()',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
  }
}
