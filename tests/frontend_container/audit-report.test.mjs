import assert from 'node:assert/strict'
import test from 'node:test'
import { auditPeriodValid, auditReportUrl } from '../../servicios/frontend/src/auditReportUrl.mjs'

test('audit download keeps the configured origin and fixed endpoint', () => {
  const url = new URL(auditReportUrl({ desde:'2026-10-01', hasta:'2026-10-07', usuario_id:4 }, 'https://identity.example.org'))
  assert.equal(url.origin, 'https://identity.example.org')
  assert.equal(url.pathname, '/auditoria/informe.xlsx')
  assert.equal(url.searchParams.get('usuario_id'), '4')
})

test('form values cannot redirect requests or add query parameters', () => {
  const url = new URL(auditReportUrl({ evento:'//evil.invalid?a=1&usuario_id=10', servicio:'https://evil.invalid' }, 'https://identity.example.org'))
  assert.equal(url.origin, 'https://identity.example.org')
  assert.equal(url.pathname, '/auditoria/informe.xlsx')
  assert.equal(url.searchParams.get('usuario_id'), null)
  assert.equal(url.searchParams.get('evento'), '//evil.invalid?a=1&usuario_id=10')
  assert.throws(() => auditReportUrl({redirect:'https://evil.invalid'}, 'https://identity.example.org'))
})

test('ambiguous or credential-bearing deployment origins are rejected', () => {
  for (const api of ['https://user:secret@identity.example.org','javascript:alert(1)',
    'https://identity.example.org/path','https://identity.example.org?x=1','https://identity.example.org#fragment']) {
    assert.throws(() => auditReportUrl({}, api))
  }
})

test('audit period uses real inclusive UTC calendar dates, at most 31 days', () => {
  assert.equal(auditPeriodValid('2026-10-01','2026-10-31'),true)
  assert.equal(auditPeriodValid('2026-10-01','2026-11-01'),false)
  assert.equal(auditPeriodValid('2026-10-07','2026-10-07'),true)
  assert.equal(auditPeriodValid('2026-10-07','2026-10-01'),false)
  assert.equal(auditPeriodValid('2026-02-30','2026-03-01'),false)
  assert.equal(auditPeriodValid('','2026-10-01'),false)
})
