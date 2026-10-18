# Automated ZAP staging

Commit: 574bb3e8195c3583ebd973f33d7f48a738689f7d
Repository: yeisonfblopez/DevSecOps-proyecto-Final-ci

7 scans; 39 API/role operations; 1947 recorded requests.
Alert gate: PASS (MEDIUM/HIGH).

| API / role | Requests | Alerts |
|---|---:|---:|
| audit / PUBLIC | 74 | 0 |
| identity / ADMIN_SOPORTE | 466 | 0 |
| identity / ADMIN_TI | 463 | 0 |
| permissions / ADMIN_SOPORTE | 236 | 0 |
| permissions / LIDER_FACTURACION | 236 | 0 |
| permissions / LIDER_GESTION_HUMANA | 236 | 0 |
| permissions / LIDER_LOGISTICA | 236 | 0 |

## Scope

- GET-only active scan through scope gateway, five rules at LOW strength
- Synthetic sessions; no login, MFA enrolment, XLSX or write operations
- 403 and gateway-rejected inputs do not cover protected business logic
- No frontend spider or complete application DAST coverage
- Fresh application builds; no use of normal Compose or local database
