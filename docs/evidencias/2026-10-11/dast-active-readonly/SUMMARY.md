# Read-only active scan — phase 2

ZAP 2.17.0; 15 unique GET operations, 39 API/role operations, 7 runs.
No spider/AJAX spider. Only filtered local contracts were imported.
Policy: Path Traversal (6), SQL Injection (40018), Server Side Code Injection (90019), Remote OS Command Injection (90020), CRLF Injection (40003), all LOW.

| API / role | GET operations | ZAP recorded requests | Alerts |
|---|---:|---:|---:|
| audit / PUBLIC | 1 | 74 | 0 |
| identity / ADMIN_SOPORTE | 9 | 466 | 0 |
| identity / ADMIN_TI | 9 | 463 | 0 |
| permissions / ADMIN_SOPORTE | 5 | 236 | 0 |
| permissions / LIDER_FACTURACION | 5 | 236 | 0 |
| permissions / LIDER_GESTION_HUMANA | 5 | 236 | 0 |
| permissions / LIDER_LOGISTICA | 5 | 236 | 0 |

## Database comparison

| Table | Before | After | Result |
|---|---:|---:|---|
| auditoria_eventos | 0 | 0 | identical |
| auditoria_outbox | 0 | 0 | identical |
| cargas_usuario_filas | 0 | 0 | identical |
| cargas_usuarios | 0 | 0 | identical |
| companias | 5 | 5 | identical |
| credenciales | 6 | 6 | identical |
| mfa_desafios | 0 | 0 | identical |
| mfa_totp | 6 | 6 | identical |
| permisos_migraciones | 1 | 1 | identical |
| permisos_usuario_compania | 2 | 2 | identical |
| roles_plataforma | 5 | 5 | identical |
| sesiones | 12 | 12 | expected session activity only |
| sync_jobs | 0 | 0 | identical |
| usuario_companias_plataforma | 6 | 6 | identical |
| usuario_roles_plataforma | 6 | 6 | identical |
| usuarios_plataforma | 6 | 6 | identical |

## Coverage limits

- Five selected active rules at LOW strength; not all ZAP rules
- 403 responses do not cover protected business logic
- Synthetic sessions; no login/MFA flow executed
- Gateway rejects out-of-scope mutated URLs; those inputs do not reach the API
- Preflight negative method probes were rejected before the pre-scan snapshot
- First setup attempt imported the filtered Identity contract but failed before any active scan; preserved separately

## Reports

- audit-public: [JSON](audit-public/report.json), [coverage](audit-public/coverage.json); context retained locally
- identity-admin_soporte: [JSON](identity-admin_soporte/report.json), [coverage](identity-admin_soporte/coverage.json); context retained locally
- identity-admin_ti: [JSON](identity-admin_ti/report.json), [coverage](identity-admin_ti/coverage.json); context retained locally
- permissions-admin_soporte: [JSON](permissions-admin_soporte/report.json), [coverage](permissions-admin_soporte/coverage.json); context retained locally
- permissions-lider_facturacion: [JSON](permissions-lider_facturacion/report.json), [coverage](permissions-lider_facturacion/coverage.json); context retained locally
- permissions-lider_gestion_humana: [JSON](permissions-lider_gestion_humana/report.json), [coverage](permissions-lider_gestion_humana/coverage.json); context retained locally
- permissions-lider_logistica: [JSON](permissions-lider_logistica/report.json), [coverage](permissions-lider_logistica/coverage.json); context retained locally

Evidence: database/pre.json, database/post-frozen.json (gateway stopped), database-comparison.json, summary.json.
At scan completion, gateway and scanner containers were stopped and all lab resources were preserved for review.

Archive sanitization: all 14 original JSON/HTML reports were checked against exact ephemeral secret/token values and credential patterns. No matches were found. Raw files remain local. The archive omits per-cell digests, raw network addresses, daemon logs, job files and contexts.

HTML reports are retained exclusively as local evidence.

## Approved cleanup

Executed only `python3 dast/cleanup.py --execute` after the reduced evidence passed validation. Independent verification confirmed **0 DAST containers, 0 DAST networks and 0 DAST volumes**. Fingerprints of non-DAST container/network/volume inventories were unchanged. No normal Compose or global prune was used. Original ephemeral secret files were removed. The nine offline tests passed again after destruction.
