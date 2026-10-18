const configured = import.meta.env.VITE_PERMISSIONS_API_URL?.trim()
const url = configured ? new URL(configured) : new URL(window.location.origin)
if (!configured) url.port = '8005'
if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
  throw new Error('URL de permisos inválida')
}
const API = url.href.replace(/\/$/, '')

export async function permissionsRequest(token, path, options = {}) {
  const response = await fetch(API + path, {
    ...options, cache: 'no-store', credentials: 'omit', redirect: 'error',
    headers: {
      Authorization: 'Bearer ' + token,
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    },
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    const error = new Error(typeof data.detail === 'string' ? data.detail : 'No se pudo completar la operación de permisos')
    error.status = response.status
    throw error
  }
  return data
}
