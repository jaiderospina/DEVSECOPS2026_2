// SPA compilada y contratos simulados. El parser XLSX real se prueba en Pytest.
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { mkdir } from 'node:fs/promises'
const { chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE)
const browser = await chromium.launch({ headless: true })
const context = await browser.newContext()
context.setDefaultTimeout(20000)
const page = await context.newPage()
const company = { id: 1, codigo: 'CARIBE', nombre: 'CARIBE SAS' }
let rows = [
  { fila: 2, datos: { id_externo: '001', nombre: 'Nueva Persona', email: 'nueva@example.org', rol: 'LIDER_FACTURACION' }, estado: 'PENDIENTE', codigo: 'VALIDA', mensaje: 'Lista para importar.', usuario_id: null },
  { fila: 3, datos: { id_externo: '002', nombre: 'Rol inválido', email: 'otra@example.org', rol: 'ADMIN_TI' }, estado: 'INVALIDA', codigo: 'DATOS_INVALIDOS', mensaje: 'Rol no permitido.', usuario_id: null },
]
let confirmed = false, created = 0, validated = false
function job() {
  return { id: '11111111-1111-4111-8111-111111111111', estado: confirmed ? 'CONFIRMADA' : 'VALIDADA',
    compania: company, creada_en: new Date().toISOString(), confirmar_antes: new Date(Date.now() + 1800000).toISOString(),
    resumen: { total: rows.length, pendiente: rows.filter(r => r.estado === 'PENDIENTE').length,
      invalida: rows.filter(r => r.estado === 'INVALIDA').length, creada: rows.filter(r => r.estado === 'CREADA').length, error: 0 },
    filas: rows }
}
await context.addInitScript(() => { sessionStorage.setItem('iam_access_token', 'bulk-test-session') })
await context.route('**/*', async route => {
  const request = route.request(), url = new URL(request.url())
  if (url.port !== '8003') return route.continue()
  const cors = { 'Access-Control-Allow-Origin': 'http://localhost:5173',
    'Access-Control-Allow-Methods': 'GET,POST', 'Access-Control-Allow-Headers': 'Authorization,Content-Type' }
  if (request.method() === 'OPTIONS') return route.fulfill({ status: 204, headers: cors })
  assert.equal(request.headers().authorization, 'Bearer bulk-test-session')
  assert(!request.url().includes('bulk-test-session'))
  let data, status = 200
  if (url.pathname === '/auth/me') data = { id: 1, nombre: 'Soporte Prueba', email: 'soporte@example.org',
    activo: true, roles: ['ADMIN_SOPORTE'], requiere_cambio_password: false, mfa_activo: true }
  else if (url.pathname === '/companias') data = { companias: [company] }
  else if (url.pathname === '/usuarios/cargas/plantilla' || url.pathname.endsWith('/resultado')) {
    return route.fulfill({ status, headers: { ...cors, 'Content-Disposition': 'attachment; filename="fixture.xlsx"' },
      contentType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', body: 'fixture-download' })
  } else if (url.pathname === '/usuarios/cargas/validar') {
    assert.equal(request.method(), 'POST')
    assert(request.headers()['content-type'].startsWith('multipart/form-data; boundary='))
    assert(request.postData().includes('name="compania_id"'))
    assert(request.postData().includes('filename="usuarios.xlsx"'))
    assert.equal(created, 0)
    validated = true; data = job(); status = 201
  } else if (url.pathname === '/usuarios/cargas') {
    assert.equal(url.searchParams.get('compania_id'), '1')
    data = { cargas: validated ? [job()] : [] }
  } else if (url.pathname.endsWith('/confirmar')) {
    assert.deepEqual(request.postDataJSON(), { confirmar: true })
    confirmed = true; data = job()
  } else if (url.pathname.endsWith('/filas/2')) {
    assert(confirmed)
    if (rows[0].estado !== 'CREADA') { created++; rows[0] = { ...rows[0], estado: 'CREADA', codigo: 'CREADA', usuario_id: 20, mensaje: 'Cuenta creada.' } }
    data = { fila: rows[0] }
  } else if (url.pathname.endsWith('/filas/3')) throw new Error('La interfaz intentó crear una fila inválida')
  else if (url.pathname === '/usuarios/cargas/' + job().id) data = job()
  else throw new Error('API inesperada: ' + url.pathname)
  return route.fulfill({ status, headers: cors, contentType: 'application/json', body: JSON.stringify(data) })
})
try {
  await page.goto('http://localhost:5173/')
  await page.getByRole('button', { name: 'Carga masiva', exact: true }).click()
  await page.getByRole('heading', { name: 'Carga masiva desde Excel' }).waitFor()
  assert.equal(await page.locator('.bulk-company').innerText(), 'CARIBE SAS')
  assert((await page.locator('.bulk-notice').innerText()).includes('cada líder recibe las tres opciones de su área habilitadas'))
  let downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Descargar plantilla Excel' }).click()
  assert.equal((await downloadPromise).suggestedFilename(), 'plantilla-usuarios.xlsx')
  await page.locator('input[type=file]').setInputFiles({ name: 'usuarios.xlsx',
    mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', buffer: Buffer.from('mock-upload-no-parser') })
  await page.getByRole('button', { name: 'Validar Excel', exact: true }).click()
  await page.getByRole('heading', { name: 'Vista previa del lote' }).waitFor()
  assert.equal(created, 0)
  assert(await page.getByRole('button', { name: 'Importar filas válidas' }).isDisabled())
  assert.equal(await page.locator('.bulk-table tbody tr').count(), 2)
  await page.getByRole('checkbox', { name: /Revisé las filas válidas/ }).check()
  await page.getByRole('button', { name: 'Importar filas válidas' }).click()
  await page.getByRole('status').filter({ hasText: 'Importación terminada' }).waitFor()
  assert.equal(created, 1)
  assert.equal(await page.locator('.bulk-state.state-creada').count(), 1)
  assert.equal(await page.locator('.bulk-state.state-invalida').count(), 1)
  downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: 'Descargar resultados Excel' }).click()
  assert.equal((await downloadPromise).suggestedFilename(), 'resultado-carga.xlsx')
  await mkdir('reports', { recursive: true })
  await page.screenshot({ path: 'reports/bulk-users-excel.png', fullPage: true })
  console.log('PASS: plantilla, compañía, multipart, vista previa, consentimiento y filas inválidas excluidas')
  await page.reload()
  await page.getByRole('button', { name: 'Carga masiva', exact: true }).click()
  await page.getByText('Lotes recientes de esta compañía', { exact: true }).click()
  await page.getByRole('button', { name: 'Abrir lote', exact: true }).click()
  await page.getByRole('heading', { name: 'Resultados del lote' }).waitFor()
  assert.equal(await page.locator('.bulk-state.state-creada').count(), 1)
  assert.equal(created, 1)
  console.log('PASS: descarga de resultados y reapertura del lote conservan el progreso confirmado')
} finally { await context.close(); await browser.close() }
