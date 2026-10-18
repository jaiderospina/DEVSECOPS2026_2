import test from 'node:test'
import assert from 'node:assert/strict'
import { permissionWindowOrigins } from '../../servicios/frontend/src/windowOrigins.mjs'

test('preserve development origins and protected permissions path', () => {
  const urls = permissionWindowOrigins({}, 'http://localhost:5173')
  assert.equal(urls.portalOrigin, 'http://localhost:5173')
  assert.equal(urls.gridUrl.href, 'http://localhost:5176/permissions.html')
})
test('HTTPS laboratory keeps distinct explicit origins', () => {
  const urls = permissionWindowOrigins({ VITE_PORTAL_ORIGIN: 'https://localhost:8443',
    VITE_PERMISSIONS_GRID_ORIGIN: 'https://localhost:8444' }, 'https://localhost:8444')
  assert.equal(urls.portalOrigin, 'https://localhost:8443')
  assert.equal(urls.gridUrl.href, 'https://localhost:8444/permissions.html')
})
for (const value of ['http://localhost:8444', 'https://user:secret@localhost:8444',
  'https://localhost:8444/other', 'https://localhost:8444/?token=x',
  'https://localhost:8444/#token', 'javascript:alert(1)']) {
  test('reject unsafe configured grid origin ' + value, () => {
    assert.throws(() => permissionWindowOrigins({ VITE_PERMISSIONS_GRID_ORIGIN: value }, 'https://localhost:8443'))
  })
}
