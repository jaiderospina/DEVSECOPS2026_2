import assert from 'node:assert/strict'
import test from 'node:test'
import { mkdir, mkdtemp, readFile, writeFile, copyFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { execFileSync } from 'node:child_process'
import { renderNginxConfig } from '../../servicios/frontend/container/write-nginx-config.mjs'
import { securityHeaders } from '../../servicios/frontend/security-policy.js'

test('CSP mantiene MFA y bloquea scripts/estilos inline', () => {
  const headers = securityHeaders({})
  const csp = headers['Content-Security-Policy']
  assert.match(csp, /img-src 'self' data: blob:/)
  assert.match(csp, /script-src 'self';/)
  assert.match(csp, /style-src 'self';/)
  assert.match(csp, /frame-ancestors 'none'/)
  assert.doesNotMatch(csp, /unsafe-inline|unsafe-eval/)
  assert.equal(headers['X-Frame-Options'], 'DENY')
})
test('CSP incluye ambos orígenes públicos personalizados, sin rutas', () => {
  const csp = securityHeaders({ VITE_API_URL: 'https://iam.example.org/api', VITE_PERMISSIONS_API_URL: 'https://permissions.example.org/v1' })['Content-Security-Policy']
  assert.match(csp, /https:\/\/iam.example.org/)
  assert.match(csp, /https:\/\/permissions.example.org/)
  assert.doesNotMatch(csp, /\/api|\/v1/)
})
test('CSP admite los orígenes IPv6 HTTP/HTTPS', () => {
  assert.match(securityHeaders({ VITE_API_URL: 'http://[::1]:8003' })['Content-Security-Policy'], /http:\/\/\[::1\]:8003/)
})
test('Se rechazan protocolos, credenciales y URLs ambiguas', () => {
  for (const name of ['VITE_API_URL', 'VITE_PERMISSIONS_API_URL']) {
    for (const value of ['javascript:alert(1)', 'file:///etc/passwd', 'https://user:secret@example.org', 'https://example.org?token=secret', 'https://example.org#fragment']) {
      assert.throws(() => securityHeaders({ [name]: value }), /URL pública/)
    }
  }
})
test('Se rechaza la interpolación de variables Nginx en orígenes', () => {
  assert.throws(() => securityHeaders({ VITE_API_URL: 'https://$host.example.org' }), /origen no válido/)
})
test('El generador conserva cabeceras y puerto no privilegiado', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'iam-nginx-test-'))
  try {
    await mkdir(join(dir, 'container'))
    await writeFile(join(dir, 'package.json'), JSON.stringify({ type: 'module' }))
    await copyFile(fileURLToPath(new URL('../../servicios/frontend/security-policy.js', import.meta.url)), join(dir, 'security-policy.js'))
    await copyFile(fileURLToPath(new URL('../../servicios/frontend/container/write-nginx-config.mjs', import.meta.url)), join(dir, 'container/write-nginx-config.mjs'))
    const output = join(dir, 'nginx.conf')
    execFileSync(process.execPath, [join(dir, 'container/write-nginx-config.mjs')], {
      env: { ...process.env, VITE_API_URL: 'https://iam.example.org', VITE_PERMISSIONS_API_URL: '' },
    })
    const config = await readFile(output, 'utf8')
    assert.throws(() => execFileSync(process.execPath, [join(dir, 'container/write-nginx-config.mjs')], { stdio: 'pipe' }), /Command failed/)
    assert.equal(await readFile(output, 'utf8'), config)
    assert.match(config, /listen 5173;/)
    assert.match(config, /pid \/tmp\/nginx.pid;/)
    assert.match(config, /add_header Content-Security-Policy ".*https:\/\/iam.example.org.*" always;/)
    assert.match(config, /location \/assets\/ \{ try_files \$uri =404; \}/)
    assert.match(config, /listen 5173 default_server;/)
    assert.match(config, /server_name localhost \*\.localhost host\.docker\.internal/)
    assert.match(config, /return 403;/)
    assert.doesNotMatch(config, /\$host|\$http_host/)
    assert.doesNotMatch(config, /unsafe-inline|user root/)
  } finally { await rm(dir, { recursive: true, force: true }) }
})

test('Se rechaza cualquier ruta CLI y no se modifica el destino', async () => {
  const dir = await mkdtemp(join(tmpdir(), 'iam-nginx-reject-'))
  try {
    const victim = join(dir, 'victim.conf')
    await writeFile(victim, 'unchanged')
    assert.throws(() => execFileSync(process.execPath, [fileURLToPath(new URL('../../servicios/frontend/container/write-nginx-config.mjs', import.meta.url)), victim], { stdio: 'pipe' }), /Command failed/)
    assert.equal(await readFile(victim, 'utf8'), 'unchanged')
  } finally { await rm(dir, { recursive: true, force: true }) }
})

test('Renderizar no escribe archivos y conserva el escape de expresiones Nginx', () => {
  const config = renderNginxConfig({})
  assert.match(config, /server_tokens off;/)
  assert.ok(config.includes('~^[0-9]+' + String.raw`\\.`))
})
