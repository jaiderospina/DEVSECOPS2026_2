// Comprueba la SPA compilada con contratos API simulados; no usa cuentas reales.
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { mkdir } from 'node:fs/promises'
const { chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE)
const browser = await chromium.launch({ headless: true })
const context = await browser.newContext()
context.setDefaultTimeout(20000)
context.setDefaultNavigationTimeout(20000)
const page = await context.newPage()
let leader = false
let unavailable = false
const company = { id: 1, codigo: 'CARIBE', nombre: 'CARIBE SAS' }
const permissions = [
  { codigo: 'facturacion.aprobaciones.consultar', titulo: 'Facturas pendientes por aprobación', descripcion: 'Documentos en proceso de revisión', icono: '▤' },
  { codigo: 'facturacion.pagos.consultar', titulo: 'Facturas pendientes por pagar', descripcion: 'Compromisos de pago del período', icono: '$' },
  { codigo: 'facturacion.impuestos.consultar', titulo: 'Declaración de impuestos', descripcion: 'Calendario y obligaciones tributarias', icono: '%' },
].map((p) => ({ ...p, area: 'Facturación', rol: 'LIDER_FACTURACION', habilitado: true, version: 1 }))
await context.addInitScript(() => {
  if (window.location.port === '5173') sessionStorage.setItem('iam_access_token', 'test-session')
})
await context.route('**/*', async (route) => {
  const url = new URL(route.request().url())
  if (!['8003', '8005'].includes(url.port)) return route.continue()
  const origin = route.request().headers().origin
  assert(['http://localhost:5173', 'http://localhost:5176'].includes(origin))
  const cors = { 'Access-Control-Allow-Origin': origin,
    'Access-Control-Allow-Methods': 'GET,PUT', 'Access-Control-Allow-Headers': 'Authorization,Content-Type' }
  if (route.request().method() === 'OPTIONS') {
    return route.fulfill({ status: 204, headers: cors })
  }
  assert.equal(url.search, '')
  assert.equal(route.request().headers().authorization, 'Bearer test-session')
  let data
  let status = 200
  if (url.port === '8003' && url.pathname === '/auth/me') {
    data = { id: leader ? 2 : 1, nombre: leader ? 'Facturador' : 'Soporte de prueba',
      email: leader ? 'facturacion@example.org' : 'soporte@example.org', activo: true,
      roles: [leader ? 'LIDER_FACTURACION' : 'ADMIN_SOPORTE'],
      requiere_cambio_password: false, mfa_activo: true,
      ...(leader ? { compania: company } : {}) }
  } else if (url.port === '8003' && url.pathname === '/companias') {
    data = { companias: [company, { id: 3, codigo: 'ANDINA', nombre: 'ANDINA SAS' }] }
  } else if (url.pathname === '/v1/companies') {
    data = { companias: [company, { id: 3, codigo: 'ANDINA', nombre: 'ANDINA SAS' }] }
  } else if (url.pathname === '/v1/companies/3/permissions') {
    data = { compania: { id: 3, codigo: 'ANDINA', nombre: 'ANDINA SAS' }, usuarios: [] }
  } else if (url.pathname === '/v1/companies/1/permissions') {
    data = { compania: company, usuarios: [{ id: 2, nombre: 'Facturador',
      email: 'facturacion@example.org', rol: 'LIDER_FACTURACION', permisos: permissions }] }
  } else if (route.request().method() === 'PUT') {
    const change = route.request().postDataJSON()
    const permission = permissions.find((p) => url.pathname.endsWith(p.codigo))
    assert(permission)
    assert.equal(change.version, permission.version)
    permission.habilitado = change.habilitado
    permission.version++
    data = permission
  } else if (url.pathname === '/v1/me/permissions') {
    data = unavailable ? { detail: 'Servicio de permisos no disponible' } : { compania_id: 1, permisos: permissions }
    if (unavailable) status = 503
  } else if (url.pathname.startsWith('/v1/me/views/')) {
    const permission = permissions.find((p) => url.pathname.endsWith(p.codigo) && p.habilitado)
    data = permission || { detail: 'Permiso no habilitado' }
    if (!permission) status = 403
  } else {
    throw new Error('Petición API no prevista: ' + url.pathname)
  }
  await route.fulfill({ status, headers: cors, contentType: 'application/json', body: JSON.stringify(data) })
})
try {
  await page.goto('http://localhost:5173/')
  const popupPromise = page.waitForEvent('popup')
  await page.getByRole('button', { name: 'Grilla de permisos', exact: true }).click()
  const grid = await popupPromise
  await grid.waitForURL('http://localhost:5176/permissions.html')
  await grid.getByRole('heading', { name: 'Grilla de permisos', exact: true }).waitFor()
  await grid.locator('.permissions-header .permissions-company').filter({ hasText: 'CARIBE SAS' }).waitFor()
  assert.equal(await grid.evaluate(() => sessionStorage.getItem('iam_access_token')), null)
  assert.equal(await grid.evaluate(() => localStorage.getItem('iam_access_token')), null)
  assert.equal(new URL(grid.url()).search, '')
  assert.equal(new URL(grid.url()).hash, '')
  assert.equal(await page.getByRole('heading', { name: 'Panel principal', exact: true }).count(), 1)
  assert.deepEqual(await grid.getByRole('combobox', { name: /Compañía/ }).locator('option').evaluateAll((options) => options.map((option) => option.value)), ['1', '3'])
  await grid.getByRole('combobox', { name: /Compañía/ }).selectOption('3')
  await grid.locator('.permissions-header .permissions-company').filter({ hasText: 'ANDINA SAS' }).waitFor()
  await grid.getByRole('combobox', { name: /Compañía/ }).selectOption('1')
  const toggle = grid.getByRole('switch', { name: 'Habilitar Facturas pendientes por pagar para Facturador', exact: true })
  await toggle.waitFor()
  assert(await toggle.isChecked())
  grid.once('dialog', (dialog) => dialog.accept())
  await toggle.click()
  await grid.getByRole('status').filter({ hasText: 'Permiso guardado' }).waitFor()
  assert.equal(await toggle.isChecked(), false)
  await mkdir('reports', { recursive: true })
  await grid.screenshot({ path: 'reports/permissions-grid.png', fullPage: true })
  leader = true
  await page.reload()
  await grid.getByRole('status').filter({ hasText: 'La sesión del panel terminó' }).waitFor()
  assert.equal(await grid.getByRole('switch').count(), 0)
  console.log('PASS: pestaña 5176, compañía en encabezado, sesión solo en memoria y cierre desde panel')
  await page.getByRole('heading', { name: 'Facturas pendientes por aprobación', exact: true }).waitFor()
  assert.equal(await page.getByRole('heading', { name: 'Facturas pendientes por pagar', exact: true }).count(), 0)
  assert.equal(await page.getByRole('heading', { name: 'Declaración de impuestos', exact: true }).count(), 1)
  await page.screenshot({ path: 'reports/permissions-leader.png', fullPage: true })
  console.log('PASS: grilla modifica permiso y una nueva sesión de interfaz oculta la opción')
  unavailable = true
  await page.reload()
  await page.getByRole('alert').filter({ hasText: 'Servicio de permisos no disponible' }).waitFor()
  assert.equal(await page.getByRole('heading', { name: 'Facturas pendientes por aprobación', exact: true }).count(), 0)
  console.log('PASS: API no disponible no muestra tarjetas sin verificar permisos')
  const direct = await context.newPage()
  await direct.goto('http://localhost:5176/permissions.html')
  await direct.getByRole('status').filter({ hasText: 'Abra esta grilla desde el botón' }).waitFor()
  assert.equal(await direct.getByRole('switch').count(), 0)
  console.log('PASS: abrir la grilla directamente no concede sesión ni acceso a permisos')
} finally {
  await context.close()
  await browser.close()
}
