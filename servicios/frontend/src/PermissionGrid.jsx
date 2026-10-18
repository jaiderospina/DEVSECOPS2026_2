import { useCallback, useEffect, useState } from 'react'
import { permissionsRequest } from './permissions-api'
import './permissions.css'

export default function PermissionGrid({ token, usuario, onBack, onExpired }) {
  const [companies, setCompanies] = useState([])
  const [company, setCompany] = useState('')
  const [rows, setRows] = useState([])
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [refresh, setRefresh] = useState(0)

  const reportError = useCallback((err) => {
    if (err.status === 401) onExpired('La sesión expiró. Inicie sesión nuevamente.')
    else setError(err.message)
  }, [onExpired])

  useEffect(() => {
    let active = true
    permissionsRequest(token, '/v1/companies').then((data) => {
      if (!active) return
      setCompanies(data.companias)
      setCompany(String(data.companias[0]?.id || ''))
      if (!data.companias.length) setLoading(false)
    }).catch((err) => {
      if (active) { setLoading(false); reportError(err) }
    })
    return () => { active = false }
  }, [token, reportError])

  useEffect(() => {
    if (!company) return
    let active = true
    setRows([])
    setError('')
    setLoading(true)
    permissionsRequest(token, '/v1/companies/' + company + '/permissions').then((data) => {
      if (active) setRows(data.usuarios.flatMap((user) =>
        user.permisos.map((permission) => ({ user, permission }))))
    }).catch((err) => { if (active) reportError(err) })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [token, company, refresh, reportError])

  const changePermission = async ({ user, permission }) => {
    const enabled = !permission.habilitado
    if (!window.confirm((enabled ? 'Habilitar' : 'Deshabilitar') + ' "' + permission.titulo + '" para ' + user.nombre + '?')) return
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const updated = await permissionsRequest(token,
        '/v1/companies/' + company + '/users/' + user.id + '/permissions/' + encodeURIComponent(permission.codigo), {
          method: 'PUT', body: JSON.stringify({ habilitado: enabled, version: permission.version }),
        })
      setRows((current) => current.map((row) =>
        row.user.id === user.id && row.permission.codigo === permission.codigo
          ? { ...row, permission: { ...row.permission, ...updated } } : row))
      setMessage('Permiso guardado. Se aplicará cuando el usuario vuelva a entrar o actualice sus opciones.')
    } catch (err) {
      reportError(err)
      if (err.status === 409) setRefresh((n) => n + 1)
    } finally { setSaving(false) }
  }

  const visible = rows.filter(({ user, permission }) =>
    [user.nombre, user.email, user.rol, permission.titulo].join(' ').toLowerCase().includes(filter.toLowerCase()))
  const selectedCompany = companies.find((c) => String(c.id) === company)
  return (
    <main className="permissions-page permissions-grid-page">
      <header className="permissions-header">
        <div><span className="eyebrow">IAM SECURE · ADMIN SOPORTE</span>
          <h1>Grilla de permisos</h1>
          <p className="permissions-company" aria-live="polite">{selectedCompany?.nombre || 'Compañías asignadas'}</p>
          {selectedCompany?.codigo && <span className="permissions-company-code">{selectedCompany.codigo}</span>}
          <p>Habilite o deshabilite las opciones de cada usuario dentro de sus compañías asignadas.</p>
        </div>
        <div><strong>{usuario.nombre}</strong>
          <button type="button" className="secondary-action-button" onClick={onBack} disabled={saving}>Volver al panel</button>
        </div>
      </header>
      <section className="permissions-toolbar" aria-label="Filtros de permisos">
        <label>Compañía
          <select value={company} onChange={(e) => { setCompany(e.target.value); setMessage('') }} disabled={saving || !companies.length}>
            {companies.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
          </select>
        </label>
        <label>Buscar usuario u opción
          <input value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Nombre, correo o permiso" />
        </label>
        <button type="button" className="secondary-action-button" disabled={saving || loading || !company}
          onClick={() => { setMessage(''); setRefresh((n) => n + 1) }}>Actualizar grilla</button>
      </section>
      {error && <p className="error-message" role="alert">{error}</p>}
      {message && <p className="permissions-success" role="status">{message}</p>}
      {loading ? <p role="status">Cargando permisos...</p> : (
        <section aria-label={'Permisos de ' + (selectedCompany?.nombre || 'su compañía')}>
          <h2>{selectedCompany?.nombre || 'Compañías asignadas'}</h2>
          {!companies.length ? <p>No tiene compañías activas asignadas.</p> :
            !rows.length ? <p>No hay usuarios líderes con una asignación válida en esta compañía.</p> : (
              <div className="permissions-table-wrapper">
                <table className="permissions-table">
                  <thead><tr><th>Usuario</th><th>Rol</th><th>Área</th><th>Opción</th><th>Estado</th><th>Habilitar</th></tr></thead>
                  <tbody>{visible.map((row) => (
                    <tr key={row.user.id + ':' + row.permission.codigo}>
                      <td><strong>{row.user.nombre}</strong><small>{row.user.email}</small></td>
                      <td>{row.user.rol}</td><td>{row.permission.area}</td><td>{row.permission.titulo}</td>
                      <td><span className={'permission-state ' + (row.permission.habilitado ? 'is-enabled' : 'is-disabled')}>{row.permission.habilitado ? 'Habilitada' : 'Deshabilitada'}</span></td>
                      <td><input type="checkbox" role="switch" checked={row.permission.habilitado}
                        disabled={saving || loading}
                        aria-label={'Habilitar ' + row.permission.titulo + ' para ' + row.user.nombre}
                        onChange={() => changePermission(row)} /></td>
                    </tr>
                  ))}</tbody>
                </table>
                {!visible.length && <p>No hay coincidencias para la búsqueda.</p>}
              </div>
            )}
        </section>
      )}
    </main>
  )
}
