const configuredApi = import.meta.env?.VITE_API_URL?.trim()
const fields = new Set(['desde', 'hasta', 'evento', 'servicio', 'resultado', 'usuario_id', 'compania_id'])

export function auditReportUrl(filters, deploymentApi = configuredApi) {
  if (!filters || Object.keys(filters).some((key) => !fields.has(key))) {
    throw new Error('Filtros de auditoría inválidos.')
  }
  const api = new URL(deploymentApi || `${window.location.protocol}//${window.location.hostname}:8003`)
  if (!['http:', 'https:'].includes(api.protocol) || api.username || api.password
      || api.search || api.hash || api.pathname !== '/') {
    throw new Error('La configuración de Identity debe ser un origen HTTP válido.')
  }
  const url = new URL('/auditoria/informe.xlsx', api.origin)
  for (const [key, value] of Object.entries(filters)) {
    if (value !== '' && value != null) url.searchParams.set(key, String(value))
  }
  return url.href
}

export function auditPeriodValid(from, until) {
  const dates = [from, until].map((value) => {
    if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return NaN
    const parsed = Date.parse(value + 'T00:00:00Z')
    return Number.isFinite(parsed) && new Date(parsed).toISOString().slice(0, 10) === value ? parsed : NaN
  })
  const days = (dates[1] - dates[0]) / 86400000 + 1
  return Number.isFinite(days) && days >= 1 && days <= 31
}
