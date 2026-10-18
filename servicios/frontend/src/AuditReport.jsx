import { useEffect, useRef, useState } from 'react'
import { auditPeriodValid, auditReportUrl } from './auditReportUrl.mjs'
import './audit-report.css'

function initialDates() {
  const until = new Date()
  const from = new Date(until)
  from.setUTCDate(from.getUTCDate() - 6)
  return { desde: from.toISOString().slice(0, 10), hasta: until.toISOString().slice(0, 10) }
}

export default function AuditReport({ token, onExpired }) {
  const [filters, setFilters] = useState(() => ({ ...initialDates(), evento: '', servicio: '',
    resultado: '', usuario_id: '', compania_id: '' }))
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const request = useRef(null)
  const active = useRef(true)
  useEffect(() => {
    active.current = true
    return () => { active.current = false; request.current?.abort() }
  }, [])
  const change = (event) => {
    setFilters((current) => ({ ...current, [event.target.name]: event.target.value }))
    setError(''); setMessage('')
  }
  const download = async (event) => {
    event.preventDefault()
    if (busy) return
    if (!auditPeriodValid(filters.desde, filters.hasta)) {
      setError('Seleccione un período válido de 1 a 31 días.'); return
    }
    const controller = new AbortController()
    request.current = controller
    setBusy(true); setError(''); setMessage('')
    try {
      const url = auditReportUrl({ ...filters, evento: filters.evento.trim().toUpperCase(),
        resultado: filters.resultado.trim().toUpperCase(), servicio: filters.servicio.trim().toLowerCase() })
      const response = await fetch(url, { headers: { Authorization: 'Bearer ' + token },
        signal: controller.signal, credentials: 'omit', redirect: 'error', cache: 'no-store' })
      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        if (response.status === 401) {
          onExpired('La sesión expiró. Inicie sesión para descargar el informe.'); return
        }
        throw new Error(typeof data.detail === 'string' ? data.detail : 'Revise los filtros y vuelva a intentar.')
      }
      const blob = await response.blob()
      if (!active.current) return
      const objectUrl = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = objectUrl
      anchor.download = `auditoria-${filters.desde}-${filters.hasta}.xlsx`
      document.body.appendChild(anchor)
      anchor.click(); anchor.remove()
      window.setTimeout(() => URL.revokeObjectURL(objectUrl), 1000)
      setMessage('Informe generado. Revise su carpeta de descargas; el Excel incluye los filtros y el total de eventos.')
    } catch (err) {
      if (active.current && err.name !== 'AbortError') {
        setError(err instanceof TypeError ? 'No se pudo conectar con Identity. Vuelva a intentar.'
          : err.message || 'No se pudo generar el informe.')
      }
    } finally {
      if (active.current) setBusy(false)
    }
  }
  return (
    <section className="audit-report" aria-labelledby="audit-report-title">
      <span className="eyebrow">ADMIN TI</span>
      <h2 id="audit-report-title">Informe de auditoría</h2>
      <p>Descargue los registros de accesos y acciones de usuarios en Excel. Las fechas corresponden a días completos en UTC.</p>
      <form onSubmit={download}>
        <fieldset disabled={busy}>
          <legend>Filtros del informe</legend>
          <div className="audit-report-filters">
            <label>Desde (UTC)<input required type="date" name="desde" value={filters.desde} onChange={change} /></label>
            <label>Hasta (UTC)<input required type="date" name="hasta" value={filters.hasta} onChange={change} /></label>
            <label>Evento<input name="evento" maxLength={100} value={filters.evento} onChange={change} placeholder="Todos; ej. LOGIN_FALLIDO" /></label>
            <label>Servicio<input name="servicio" maxLength={100} value={filters.servicio} onChange={change} placeholder="Todos; ej. identity" /></label>
            <label>Resultado<input name="resultado" maxLength={50} value={filters.resultado} onChange={change} placeholder="Todos; ej. EXITO" /></label>
            <label>ID usuario (actor u objetivo)<input type="number" name="usuario_id" min="1" max="2147483647" step="1" value={filters.usuario_id} onChange={change} placeholder="Todos" /></label>
            <label>ID compañía<input type="number" name="compania_id" min="1" max="2147483647" step="1" value={filters.compania_id} onChange={change} placeholder="Todas" /></label>
          </div>
          <p className="audit-report-help">Máximo 31 días y 5.000 eventos. Si hay más, reduzca el período o aplique filtros. El detalle se resume a 2.000 caracteres. Los eventos pendientes de entrega todavía no aparecen.</p>
          <button className="primary-button" type="submit">{busy ? 'Generando informe…' : 'Descargar Excel'}</button>
        </fieldset>
      </form>
      {error && <p role="alert" className="audit-report-error">{error}</p>}
      {message && <p role="status" className="audit-report-success">{message}</p>}
    </section>
  )
}
