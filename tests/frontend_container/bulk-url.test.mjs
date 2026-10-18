import assert from 'node:assert/strict'
import test from 'node:test'
import { bulkRequestUrl } from '../../servicios/frontend/src/bulkRequestUrl.mjs'

const api = 'https://identity.example.org'
const id = '11111111-1111-4111-8111-111111111111'

test('all existing bulk operations retain their origin and route', () => {
  for (const path of ['/plantilla', '/validar', '?compania_id=1', '/' + id,
    '/' + id + '/confirmar', '/' + id + '/resultado', '/' + id + '/filas/2', '/' + id + '/filas/501']) {
    const url = new URL(bulkRequestUrl(path, api))
    assert.equal(url.origin, api)
    assert.equal(url.pathname + url.search, '/usuarios/cargas' + path)
  }
})

test('job IDs cannot change the origin, endpoint, query, fragment or credentials', () => {
  for (const path of ['//attacker.example', '/../../auth/me', '/' + id + '/../resultado',
    '/' + id + '%2f..%2fauth/me', '/' + id + '\\resultado', '/' + id + '?redirect=evil',
    '/' + id + '#fragment', '/plantilla\n', '?compania_id=1&other=2', '?compania_id=-1',
    '/' + id + '/filas/0', '/' + id + '/filas/502', '/' + id + '/filas/2?other=1', null]) {
    assert.throws(() => bulkRequestUrl(path, api))
  }
})

test('invalid API configuration cannot carry credentials or redirect requests', () => {
  for (const origin of ['javascript:alert(1)', 'file:///tmp/private', 'https://user:pass@example.org',
    api + '/other', api + '?query=1', api + '#fragment']) {
    assert.throws(() => bulkRequestUrl('/plantilla', origin))
  }
  assert.equal(bulkRequestUrl('/plantilla', 'http://localhost:8003/'),
    'http://localhost:8003/usuarios/cargas/plantilla')
})

test('unconfigured development API retains the browser host and port 8003', () => {
  globalThis.window = { location: { protocol: 'http:', hostname: 'localhost' } }
  try {
    assert.equal(bulkRequestUrl('?compania_id=2'), 'http://localhost:8003/usuarios/cargas?compania_id=2')
  } finally { delete globalThis.window }
})
