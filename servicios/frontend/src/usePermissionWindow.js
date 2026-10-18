import { useEffect, useRef } from 'react'
import { permissionWindowOrigins } from './windowOrigins.mjs'

const { gridUrl } = permissionWindowOrigins(import.meta.env, window.location.origin)
const gridOrigin = gridUrl.origin

// El canal solo acepta la ventana abierta por este panel y su origen exacto.
export default function usePermissionWindow({ token, usuario, idleDeadline, onExpired, onError }) {
  const popup = useRef(null)
  const nonce = useRef('')
  const session = useRef(null)
  session.current = { token, usuario, idleDeadline, onExpired, onError }

  useEffect(() => {
    const receive = (event) => {
      const child = popup.current
      const data = event.data
      if (!child || event.source !== child || event.origin !== gridOrigin ||
          !data || typeof data !== 'object') return
      const current = session.current
      if (!current.token || !current.idleDeadline.current || Date.now() >= current.idleDeadline.current) {
        child.postMessage({ type: 'iam-permissions-ended', nonce: data.nonce }, gridOrigin)
        window.dispatchEvent(new Event('iam-session-check'))
        return
      }
      if (data.type === 'iam-permissions-ready') {
        if (!/^[a-f0-9]{32}$/.test(data.nonce || '') || !current.token ||
            !current.usuario?.roles?.includes('ADMIN_SOPORTE') ||
            current.usuario.requiere_cambio_password) return
        nonce.current = data.nonce
        child.postMessage({ type: 'iam-permissions-session', nonce: data.nonce,
          token: current.token, expiresAt: current.idleDeadline.current,
          usuario: { nombre: current.usuario.nombre } }, gridOrigin)
      } else if (data.nonce === nonce.current && nonce.current) {
        if (data.type === 'iam-permissions-probe' && current.token &&
            current.usuario?.roles?.includes('ADMIN_SOPORTE') &&
            !current.usuario.requiere_cambio_password) {
          child.postMessage({ type: 'iam-permissions-alive', nonce: data.nonce,
            expiresAt: current.idleDeadline.current }, gridOrigin)
        } else if (data.type === 'iam-permissions-activity') {
          window.dispatchEvent(new Event('iam-permissions-activity'))
        } else if (data.type === 'iam-permissions-expired') {
          current.onExpired('La sesión expiró. Inicie sesión nuevamente.')
        }
      }
    }
    window.addEventListener('message', receive)
    return () => window.removeEventListener('message', receive)
  }, [])

  useEffect(() => {
    const end = () => {
      if (popup.current && !popup.current.closed) {
        popup.current.postMessage({ type: 'iam-permissions-ended', nonce: nonce.current }, gridOrigin)
      }
      nonce.current = ''
      popup.current = null
    }
    window.addEventListener('pagehide', end)
    return () => { window.removeEventListener('pagehide', end); end() }
  }, [token, usuario?.id])

  return () => {
    if (popup.current && !popup.current.closed) { popup.current.focus(); return }
    nonce.current = ''
    popup.current = window.open(gridUrl.href, '_blank')
    if (!popup.current) session.current.onError('Permita abrir la pestaña de permisos en este navegador.')
  }
}
