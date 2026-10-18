// Compiled public origins. Keep exact origin/window/nonce checks in the callers.
export function permissionWindowOrigins(env, currentOrigin) {
  const current = new URL(currentOrigin)
  const resolve = (name, defaultPort) => {
    const configured = env[name]?.trim()
    const url = new URL(configured || current.origin)
    if (!configured) url.port = defaultPort
    if (!['http:', 'https:'].includes(url.protocol) || url.username || url.password ||
        url.pathname !== '/' || url.search || url.hash ||
        (current.protocol === 'https:' && url.protocol !== 'https:')) {
      throw new Error(name + ' debe ser un origen válido y compatible con HTTPS')
    }
    return url.origin
  }
  return {
    portalOrigin: resolve('VITE_PORTAL_ORIGIN', '5173'),
    gridUrl: new URL('/permissions.html', resolve('VITE_PERMISSIONS_GRID_ORIGIN', '5176')),
  }
}
