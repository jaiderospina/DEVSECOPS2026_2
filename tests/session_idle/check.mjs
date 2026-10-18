// SPA compilada, reloj controlado y API simulada: ninguna cuenta o correo real.
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { readFile } from 'node:fs/promises'
import { resolve, sep } from 'node:path'
const { chromium } = createRequire(import.meta.url)(process.env.PLAYWRIGHT_MODULE)
const browser = await chromium.launch({ headless: true,
  ...(process.env.BROWSER_CHANNEL ? { channel: process.env.BROWSER_CHANNEL } : {}) })
const company = { id: 1, codigo: 'PRUEBA', nombre: 'Compañía de prueba' }
const baseTime = Date.now()

async function setup() {
  const context = await browser.newContext()
  context.setDefaultTimeout(10000)
  await context.addInitScript(() => {
    if (location.port === '5173') sessionStorage.setItem('iam_access_token', 'idle-test-session')
    // Reproduce una revocación que nunca responde.
    const original = window.fetch
    window.fetch = (input, options) => String(input).endsWith('/auth/logout')
      ? new Promise(() => {}) : original(input, options)
  })
  let apiCalls = 0
  await context.route('**/*', async route => {
    const url = new URL(route.request().url())
    if (!['8003', '8005'].includes(url.port)) {
      if (!process.env.STATIC_DIST_DIR || !['5173', '5176'].includes(url.port)) return route.continue()
      const root = resolve(process.env.STATIC_DIST_DIR)
      const file = resolve(root, '.' + decodeURIComponent(url.pathname === '/' ? '/index.html' : url.pathname))
      assert(file.startsWith(root + sep))
      const contentType = file.endsWith('.js') ? 'application/javascript' :
        file.endsWith('.css') ? 'text/css' : file.endsWith('.html') ? 'text/html' : 'application/octet-stream'
      return route.fulfill({ contentType, body: await readFile(file) })
    }
    if (route.request().method() === 'OPTIONS') return route.fulfill({ status: 204,
      headers: { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*' } })
    apiCalls++
    let data
    if (url.pathname === '/auth/me') data = { id: 1, nombre: 'Soporte de prueba',
      roles: ['ADMIN_SOPORTE'], requiere_cambio_password: false, mfa_activo: true }
    else if (['/companias', '/v1/companies'].includes(url.pathname)) data = { companias: [company] }
    else if (url.pathname === '/v1/companies/1/permissions') data = { compania: company,
      usuarios: [{ id: 2, nombre: 'Líder de prueba', rol: 'LIDER_FACTURACION',
        permisos: [{ codigo: 'facturacion.pagos.consultar', titulo: 'Pagos', habilitado: true, version: 1 }] }] }
    else if (url.pathname === '/usuarios/cargas') data = { cargas: [] }
    else throw new Error('API no prevista: ' + url.pathname)
    return route.fulfill({ contentType: 'application/json',
      headers: { 'Access-Control-Allow-Origin': '*' }, body: JSON.stringify(data) })
  })
  const page = await context.newPage()
  await page.clock.install({ time: baseTime })
  await page.goto('http://localhost:5173/')
  await page.getByRole('heading', { name: 'Panel principal', exact: true }).waitFor()
  return { context, page, calls: () => apiCalls }
}

try {
  {
    const { context, page } = await setup()
    await page.getByRole('button', { name: 'Carga masiva', exact: true }).click()
    await page.getByRole('heading', { name: 'Carga masiva desde Excel' }).waitFor()
    await page.clock.fastForward(299000)
    assert.equal(await page.locator('.bulk-page').count(), 1)
    await page.clock.fastForward(2000)
    await page.getByText(/La sesión expiró por 5 minutos de inactividad/).waitFor()
    assert.equal(await page.locator('.bulk-page').count(), 0)
    assert.equal(await page.evaluate(() => sessionStorage.getItem('iam_access_token')), null)
    console.log('PASS: carga masiva desaparece al vencer 5 minutos aunque logout no responde')
    await context.close()
  }
  {
    const { context, page, calls } = await setup()
    const popup = page.waitForEvent('popup')
    await page.getByRole('button', { name: 'Grilla de permisos', exact: true }).click()
    const grid = await popup
    await grid.getByRole('switch').waitFor()
    await grid.clock.install({ time: baseTime })
    const initialCalls = calls()
    // La interacción real en la grilla reinicia el temporizador del panel.
    await page.clock.fastForward(240000)
    await grid.clock.setFixedTime(baseTime + 240000)
    await grid.getByPlaceholder('Nombre, correo o permiso').fill('Líder')
    await grid.getByPlaceholder('Nombre, correo o permiso').press('End')
    await page.waitForTimeout(100)
    await page.clock.fastForward(61000)
    assert.equal(await page.getByRole('heading', { name: 'Panel principal', exact: true }).count(), 1)
    assert.equal(calls(), initialCalls, 'Los probes no deben consultar ni renovar la API')
    await page.clock.fastForward(240000)
    await grid.getByRole('status').filter({ hasText: /sesión.*terminó|sesión expiró/ }).waitFor()
    assert.equal(await grid.getByRole('switch').count(), 0)
    assert.equal(await page.evaluate(() => sessionStorage.getItem('iam_access_token')), null)
    console.log('PASS: actividad de grilla reinicia plazo; probes no renuevan y al vencer retira permisos')
    await context.close()
  }
  {
    const { context, page } = await setup()
    const popup = page.waitForEvent('popup')
    await page.getByRole('button', { name: 'Grilla de permisos', exact: true }).click()
    const grid = await popup
    await grid.getByRole('switch').waitFor()
    await grid.clock.install({ time: baseTime })
    await grid.clock.setFixedTime(baseTime + 600000)
    await grid.evaluate(() => window.dispatchEvent(new Event('focus')))
    await grid.getByRole('status').filter({ hasText: 'La sesión expiró por inactividad' }).waitFor()
    assert.equal(await grid.getByRole('switch').count(), 0)
    await page.getByText(/La sesión expiró/).waitFor()
    assert.equal(await page.evaluate(() => sessionStorage.getItem('iam_access_token')), null)
    console.log('PASS: grilla verifica su vencimiento aunque el temporizador del panel no se ejecuta')
    await context.close()
  }
  {
    const { context, page } = await setup()
    await page.getByRole('button', { name: 'Cerrar sesión', exact: true }).click()
    await page.getByRole('button', { name: 'Carga masiva', exact: true }).waitFor({ state: 'detached' })
    assert.equal(await page.evaluate(() => sessionStorage.getItem('iam_access_token')), null)
    console.log('PASS: cierre manual también elimina sesión sin esperar la red')
    await context.close()
  }
  {
    const { context, page } = await setup()
    await page.getByRole('button', { name: 'Carga masiva', exact: true }).click()
    await page.clock.setFixedTime(baseTime + 600000)
    // Simula suspensión: avanzó la hora, pero no se ejecutó el temporizador.
    await page.evaluate(() => window.dispatchEvent(new Event('keydown')))
    await page.getByText(/La sesión expiró por 5 minutos de inactividad/).waitFor()
    assert.equal(await page.locator('.bulk-page').count(), 0)
    console.log('PASS: interacción tras suspensión no revive una sesión vencida')
    await context.close()
  }
} finally { await browser.close() }
