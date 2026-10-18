import { useCallback, useEffect, useState } from 'react'
import PermissionGrid from './PermissionGrid'
import './App.css'
import { permissionWindowOrigins } from './windowOrigins.mjs'

const { portalOrigin } = permissionWindowOrigins(import.meta.env, window.location.origin)

export default function PermissionsWindow() {
  const [session, setSession] = useState(null)
  const [message, setMessage] = useState('Abra esta grilla desde el botón Grilla de permisos del panel de ADMIN_SOPORTE.')
  const [channel, setChannel] = useState('')

  useEffect(() => {
    const owner = window.opener
    if (!owner) return undefined
    const nonce = Array.from(crypto.getRandomValues(new Uint8Array(16)),
      (byte) => byte.toString(16).padStart(2, '0')).join('')
    setChannel(nonce)
    let received = false
    let ended = false
    let lastActivity = 0
    let probeTimeout = null
    let expiresAt = 0
    setMessage('Verificando la sesión del panel...')
    const send = (type) => {
      if (!owner.closed) owner.postMessage({ type, nonce }, portalOrigin)
    }
    const stop = (text) => {
      ended = true
      if (probeTimeout) window.clearTimeout(probeTimeout)
      setSession(null)
      setMessage(text)
    }
    const receive = (event) => {
      const data = event.data
      if (event.source !== owner || event.origin !== portalOrigin || !data ||
          data.nonce !== nonce || ended) return
      if (data.type === 'iam-permissions-session' && !received &&
          typeof data.token === 'string' && data.token &&
          Number.isFinite(data.expiresAt) && data.expiresAt > Date.now() &&
          typeof data.usuario?.nombre === 'string') {
        received = true
        expiresAt = data.expiresAt
        setSession({ token: data.token, usuario: { nombre: data.usuario.nombre } })
        setMessage('')
      } else if (data.type === 'iam-permissions-alive' && received) {
        if (Number.isFinite(data.expiresAt)) expiresAt = data.expiresAt
        if (probeTimeout) window.clearTimeout(probeTimeout)
        probeTimeout = null
      } else if (data.type === 'iam-permissions-ended') {
        stop('La sesión del panel terminó. Cierre esta pestaña y vuelva a iniciar sesión.')
      }
    }
    const checkExpiry = () => {
      if (received && !ended && Date.now() >= expiresAt) {
        stop('La sesión expiró por inactividad. Vuelva a iniciar sesión en el panel.')
        send('iam-permissions-expired')
      }
    }
    const activity = () => {
      checkExpiry()
      if (!received || ended || Date.now() - lastActivity < 1000) return
      lastActivity = Date.now()
      send('iam-permissions-activity')
      send('iam-permissions-probe')
    }
    window.addEventListener('message', receive)
    const events = ['pointerdown', 'keydown', 'touchstart', 'scroll']
    events.forEach((name) => window.addEventListener(name, activity, { passive: true }))
    window.addEventListener('focus', checkExpiry)
    document.addEventListener('visibilitychange', checkExpiry)
    send('iam-permissions-ready')
    const retry = window.setInterval(() => {
      checkExpiry()
      if (owner.closed) stop('El panel se cerró. Abra la grilla desde una sesión activa.')
      else if (!received && !ended) send('iam-permissions-ready')
      else if (received && !ended) {
        // Solo mensajes entre ventanas; no renueva la sesión del backend.
        send('iam-permissions-probe')
        if (!probeTimeout) probeTimeout = window.setTimeout(() => {
          stop('La sesión del panel terminó. Cierre esta pestaña y vuelva a iniciar sesión.')
        }, 4000)
      }
    }, 1000)
    const timeout = window.setTimeout(() => {
      if (!received) stop('No se pudo verificar la sesión. Vuelva al panel y abra nuevamente la grilla.')
    }, 15000)
    return () => {
      window.removeEventListener('message', receive)
      events.forEach((name) => window.removeEventListener(name, activity))
      window.removeEventListener('focus', checkExpiry)
      document.removeEventListener('visibilitychange', checkExpiry)
      window.clearInterval(retry)
      window.clearTimeout(timeout)
      if (probeTimeout) window.clearTimeout(probeTimeout)
    }
  }, [])

  const expired = useCallback((text) => {
    setSession(null)
    setMessage(text)
    if (window.opener && !window.opener.closed) {
      window.opener.postMessage({ type: 'iam-permissions-expired', nonce: channel }, portalOrigin)
    }
  }, [channel])
  const back = () => {
    if (window.opener && !window.opener.closed) window.opener.focus()
    window.close()
  }

  if (!session) return <main className="permissions-page">
    <span className="eyebrow">IAM SECURE · ADMIN SOPORTE</span>
    <h1>Grilla de permisos</h1><p role="status">{message}</p>
    <p>La sesión se recibe del panel y se conserva únicamente en memoria de esta pestaña.</p>
    <button type="button" className="secondary-action-button" onClick={back}>Volver al panel</button>
  </main>
  return <PermissionGrid token={session.token} usuario={session.usuario}
    onExpired={expired} onBack={back} />
}
