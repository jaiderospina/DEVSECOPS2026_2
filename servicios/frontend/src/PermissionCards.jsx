import { useCallback, useEffect, useState } from 'react'
import { permissionsRequest } from './permissions-api'

export default function PermissionCards({ token, onExpired }) {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [view, setView] = useState(null)
  const [opening, setOpening] = useState(false)
  const [refresh, setRefresh] = useState(0)
  const reportError = useCallback((err) => {
    if (err.status === 401) onExpired('La sesión expiró. Inicie sesión nuevamente.')
    else setError(err.message)
  }, [onExpired])

  useEffect(() => {
    let active = true
    setItems([])
    setView(null)
    setError('')
    setLoading(true)
    permissionsRequest(token, '/v1/me/permissions').then((data) => {
      if (active) setItems(data.permisos.filter((item) => item.habilitado))
    }).catch((err) => { if (active) reportError(err) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [token, refresh, reportError])

  const open = async (item) => {
    setOpening(true)
    setView(null)
    setError('')
    try {
      setView(await permissionsRequest(token, '/v1/me/views/' + encodeURIComponent(item.codigo)))
    } catch (err) {
      reportError(err)
      if (err.status === 403) setItems((current) => current.filter((i) => i.codigo !== item.codigo))
    } finally { setOpening(false) }
  }

  return (
    <>
      <button type="button" className="secondary-action-button" disabled={loading || opening}
        onClick={() => setRefresh((n) => n + 1)}>Actualizar mis opciones</button>
      {loading && <p role="status">Consultando opciones habilitadas...</p>}
      {error && <p className="error-message" role="alert">{error}</p>}
      {!loading && !error && !items.length && <p>No tiene opciones habilitadas. Contacte a su administrador de soporte.</p>}
      <div className="leader-accessory-grid">
        {items.map((item) => (
          <article className="leader-accessory-card" key={item.codigo}>
            <div className="leader-accessory-icon">{item.icono}</div>
            <h3>{item.titulo}</h3><p>{item.descripcion}</p>
            <span className="leader-demo-badge">Vista de referencia</span>
            <button type="button" className="secondary-action-button" disabled={opening} onClick={() => open(item)}>Abrir vista</button>
          </article>
        ))}
      </div>
      {view && <section className="leader-account-card" role="status">
        <div><h3>{view.titulo}</h3><p>{view.descripcion}</p><p>Vista académica de referencia.</p></div>
        <button type="button" className="secondary-action-button" onClick={() => setView(null)}>Cerrar vista</button>
      </section>}
    </>
  )
}
