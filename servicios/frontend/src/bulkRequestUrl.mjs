// The API origin comes only from the deployment configuration, never from a job or form.
const configuredApi = import.meta.env?.VITE_API_URL?.trim()
const UUID = '[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
const ROUTE = new RegExp(`^(?:/plantilla|/validar|\\?compania_id=[1-9][0-9]{0,18}|/${UUID}(?:/confirmar|/resultado|/filas/[1-9][0-9]{0,2})?)$`)

export function bulkRequestUrl(path, deploymentApi = configuredApi) {
  const match = typeof path === 'string' && path.match(ROUTE)
  if (!match || match[0] !== path) throw new Error('Ruta de carga inválida.')
  if (path.includes('/filas/')) {
    const row = Number(path.slice(path.lastIndexOf('/') + 1))
    if (row < 2 || row > 501) throw new Error('Fila de carga inválida.')
  }
  const api = new URL(deploymentApi || `${window.location.protocol}//${window.location.hostname}:8003`)
  if (!['http:', 'https:'].includes(api.protocol) || api.username || api.password
      || api.search || api.hash || api.pathname !== '/') {
    throw new Error('La configuración de Identity debe ser un origen HTTP válido.')
  }
  const url = new URL('/usuarios/cargas' + path, api.origin)
  if (url.origin !== api.origin || !url.pathname.startsWith('/usuarios/cargas')) {
    throw new Error('Destino de carga inválido.')
  }
  return url.href
}
