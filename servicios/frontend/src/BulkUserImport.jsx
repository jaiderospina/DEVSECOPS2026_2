import { useCallback, useEffect, useRef, useState } from 'react'
import './bulk-users.css'
import { bulkRequestUrl } from './bulkRequestUrl.mjs'

const MAX_FILE = 2 * 1024 * 1024
const labels = { PENDIENTE: 'Lista', INVALIDA: 'Inválida', CREADA: 'Creada', ERROR: 'Error' }

export default function BulkUserImport({ token, companias, onExpired }) {
  const [company, setCompany] = useState(String(companias[0]?.id || ''))
  const [file, setFile] = useState(null)
  const [job, setJob] = useState(null)
  const [recent, setRecent] = useState([])
  const [busy, setBusy] = useState(false)
  const [importing, setImporting] = useState(false)
  const [consent, setConsent] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [filter, setFilter] = useState('')
  const [page, setPage] = useState(0)
  const controller = useRef(null)
  const stop = useRef(false)
  const active = useRef(true)
  const expired = useRef(onExpired)
  expired.current = onExpired

  useEffect(() => {
    active.current = true
    return () => { active.current = false; stop.current = true; controller.current?.abort() }
  }, [])

  const request = useCallback(async (path, options = {}, blob = false) => {
    let response
    try {
      response = await fetch(bulkRequestUrl(path), {
        ...options, credentials: 'omit', redirect: 'error', cache: 'no-store',
        headers: { Authorization: 'Bearer ' + token,
          ...(options.body && !(options.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}) },
      })
    } catch (err) {
      if (err.name === 'AbortError') throw err
      throw new Error('No se pudo conectar con Identity. El progreso confirmado se conserva en el lote.')
    }
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      if (response.status === 401) expired.current('La sesión expiró. Inicie sesión y retome el lote.')
      const err = new Error(typeof data.detail === 'string' ? data.detail : 'No se pudo completar la carga.')
      err.status = response.status
      throw err
    }
    return blob ? response.blob() : response.json()
  }, [token])

  useEffect(() => {
    const ac = new AbortController()
    setRecent([])
    if (company) request('?compania_id=' + encodeURIComponent(company), { signal: ac.signal })
      .then((data) => setRecent(data.cargas))
      .catch((err) => { if (err.name !== 'AbortError') setError(err.message) })
    return () => ac.abort()
  }, [company, request])

  const begin = () => {
    stop.current = false
    controller.current = new AbortController()
    setBusy(true); setError(''); setMessage('')
    return controller.current.signal
  }
  const finish = () => {
    if (active.current) { setBusy(false); setImporting(false) }
  }
  const updateJob = (data) => {
    setJob(data); setPage(0)
    setRecent((items) => [data, ...items.filter((item) => item.id !== data.id)].slice(0, 10))
  }
  const download = async (path, name) => {
    const signal = begin()
    try {
      const data = await request(path, { signal }, true)
      const url = URL.createObjectURL(data)
      const anchor = document.createElement('a')
      anchor.href = url; anchor.download = name
      document.body.appendChild(anchor); anchor.click(); anchor.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (err) { if (active.current && err.name !== 'AbortError') setError(err.message) }
    finally { finish() }
  }
  const validate = async () => {
    if (!company || !file) return
    if (!file.name.toLowerCase().endsWith('.xlsx') || file.size > MAX_FILE) {
      setError('Seleccione un Excel .xlsx de hasta 2 MiB.'); return
    }
    const signal = begin()
    setJob(null); setConsent(false)
    try {
      const data = new FormData()
      data.append('compania_id', company); data.append('archivo', file)
      const result = await request('/validar', { method: 'POST', body: data, signal })
      if (active.current) { updateJob(result); setMessage('Validación completa. Revise las filas antes de importar.') }
    } catch (err) { if (active.current && err.name !== 'AbortError') setError(err.message) }
    finally { finish() }
  }
  const load = async (id) => {
    const signal = begin()
    setConsent(false); setFilter('')
    try {
      const result = await request('/' + id, { signal })
      if (active.current) updateJob(result)
    } catch (err) { if (active.current && err.name !== 'AbortError') setError(err.message) }
    finally { finish() }
  }
  const importRows = async () => {
    if (!job || !consent) return
    const signal = begin()
    setImporting(true)
    try {
      let current = await request('/' + job.id + '/confirmar', {
        method: 'POST', body: JSON.stringify({ confirmar: true }), signal,
      })
      if (active.current) updateJob(current)
      for (const row of current.filas.filter((item) => item.estado === 'PENDIENTE')) {
        if (stop.current || !active.current) break
        const data = await request('/' + job.id + '/filas/' + row.fila, { method: 'POST', signal })
        current = { ...current, filas: current.filas.map((item) => item.fila === row.fila ? data.fila : item) }
        current.resumen = { total: current.filas.length,
          ...Object.fromEntries(['PENDIENTE', 'INVALIDA', 'CREADA', 'ERROR'].map((state) => [
            state.toLowerCase(), current.filas.filter((item) => item.estado === state).length,
          ])) }
        if (active.current) {
          setJob(current)
          setMessage('Procesadas ' + (current.resumen.creada + current.resumen.error) + ' filas; '
            + current.resumen.pendiente + ' pendientes.')
        }
      }
      if (active.current && !stop.current) {
        updateJob(await request('/' + job.id, { signal }))
        setMessage('Importación terminada. Revise los resultados por fila.')
      }
    } catch (err) {
      if (active.current) {
        if (err.name === 'AbortError') setMessage('Carga pausada. Abra o retome el lote para consultar el resultado de la última fila.')
        else setError(err.message)
      }
    } finally { finish() }
  }

  const selected = companias.find((item) => String(item.id) === company)
  const rows = (job?.filas || []).filter((row) => !filter || row.estado === filter)
  const visible = rows.slice(page * 50, (page + 1) * 50)
  const pages = Math.max(1, Math.ceil(rows.length / 50))
  return <section className="bulk-page" aria-label="Importar usuarios desde Excel">
    <header className="bulk-header">
      <span className="eyebrow">IDENTITY MANAGEMENT · ADMIN SOPORTE</span>
      <h2>Carga masiva desde Excel</h2>
      <p className="bulk-company">{selected?.nombre || 'Seleccione una compañía asignada'}</p>
      <p>Descargue la plantilla, valide el archivo y confirme las filas válidas. Hasta 500 usuarios por lote.</p>
    </header>
    <div className="bulk-toolbar">
      <label>Compañía de destino
        <select aria-label="Compañía de destino" value={company} disabled={busy}
          onChange={(event) => { setCompany(event.target.value); setFile(null); setJob(null); setConsent(false); setError(''); setMessage('') }}>
          {!companias.length && <option value="">Sin compañías asignadas</option>}
          {companias.map((item) => <option key={item.id} value={item.id}>{item.nombre}</option>)}
        </select>
      </label>
      <button type="button" className="secondary-action-button" disabled={busy}
        onClick={() => download('/plantilla', 'plantilla-usuarios.xlsx')}>Descargar plantilla Excel</button>
      <label>Archivo Excel (.xlsx)
        <input key={company} type="file" accept=".xlsx" disabled={busy || !company}
          onChange={(event) => { setFile(event.target.files[0] || null); setJob(null); setConsent(false); setError(''); setMessage('') }} />
      </label>
      <button type="button" className="primary-action-button" disabled={busy || !file || !company}
        onClick={validate}>Validar Excel</button>
    </div>
    <p className="bulk-notice">El archivo contiene identificación, nombre, correo y rol. No agregue contraseñas.
      La compañía se asigna desde esta pantalla. Las nuevas cuentas requieren cambio de contraseña y MFA;
      cada líder recibe las tres opciones de su área habilitadas. Ajuste los casos puntuales desde la grilla de permisos.</p>
    {!companias.length && <p>No tiene compañías activas asignadas.</p>}
    {error && <p className="error-message" role="alert">{error}</p>}
    {message && <p className="bulk-status" role="status">{message}</p>}
    {busy && !importing && <p role="status">Procesando solicitud...</p>}
    {!!recent.length && <details className="bulk-recent">
      <summary>Lotes recientes de esta compañía</summary>
      {recent.map((item) => <div key={item.id}>
        <span>{new Date(item.creada_en).toLocaleString()} · {item.resumen.total} filas · {item.resumen.creada} creadas</span>
        <button type="button" className="secondary-action-button" disabled={busy} onClick={() => load(item.id)}>Abrir lote</button>
      </div>)}
    </details>}
    {job && <>
      <h3>{job.estado === 'VALIDADA' ? 'Vista previa del lote' : 'Resultados del lote'}</h3>
      <div className="bulk-stats" aria-label="Resumen de la carga">
        {[['Válidas pendientes', job.resumen.pendiente], ['Inválidas', job.resumen.invalida],
          ['Creadas', job.resumen.creada], ['Errores de creación', job.resumen.error]].map(([label, count]) =>
          <div key={label}><span>{label}</span><strong>{count}</strong></div>)}
      </div>
      {!!job.resumen.pendiente && <div className="bulk-confirm">
        <label><input type="checkbox" checked={consent} disabled={busy} onChange={(event) => setConsent(event.target.checked)} />
          Revisé las filas válidas para {job.compania.nombre} y autorizo su creación con las tres opciones de su área habilitadas y el envío de credenciales al correo de cada usuario.</label>
        <button type="button" className="primary-action-button" disabled={busy || !consent}
          onClick={importRows}>{job.estado === 'CONFIRMADA' ? 'Retomar importación' : 'Importar filas válidas'}</button>
      </div>}
      {importing && <button type="button" className="secondary-action-button"
        onClick={() => { stop.current = true; controller.current?.abort() }}>Pausar carga</button>}
      <div className="bulk-results-toolbar">
        <label>Mostrar filas
          <select aria-label="Mostrar filas" value={filter} disabled={busy} onChange={(event) => { setFilter(event.target.value); setPage(0) }}>
            <option value="">Todas</option>{Object.entries(labels).map(([state, label]) => <option key={state} value={state}>{label}</option>)}
          </select>
        </label>
        <button type="button" className="secondary-action-button" disabled={busy}
          onClick={() => download('/' + job.id + '/resultado', 'resultado-carga.xlsx')}>Descargar resultados Excel</button>
      </div>
      <div className="bulk-table-wrapper"><table className="bulk-table">
        <thead><tr><th>Fila</th><th>Identificación</th><th>Nombre</th><th>Correo</th><th>Rol</th><th>Estado</th><th>Resultado</th></tr></thead>
        <tbody>{visible.map((row) => <tr key={row.fila}>
          <td>{row.fila}</td><td>{row.datos.id_externo}</td><td>{row.datos.nombre}</td>
          <td>{row.datos.email}</td><td>{row.datos.rol}</td>
          <td><span className={'bulk-state state-' + row.estado.toLowerCase()}>{labels[row.estado]}</span></td>
          <td>{row.mensaje}</td>
        </tr>)}</tbody>
      </table></div>
      <div className="bulk-pagination">
        <button type="button" disabled={busy || page === 0} onClick={() => setPage((n) => n - 1)}>Anterior</button>
        <span>Página {page + 1} de {pages}</span>
        <button type="button" disabled={busy || page + 1 >= pages} onClick={() => setPage((n) => n + 1)}>Siguiente</button>
      </div>
    </>}
  </section>
}
