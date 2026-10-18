# Phase 2: authorized GET-only active scan

Completed using local ZAP 2.17.0 image ID
sha256:7aaa659b0d43078febd82e29bad112285c370727e86ab8340444220e17d9f0d2.

Only the three phase-1 filtered OpenAPI files were imported. No full contract,
spider, AJAX spider, login, MFA workflow or password recovery was used.
Seven API/role runs covered 39 combinations of the 15 unique GET operations.

Five active rules at LOW strength: 6, 40018, 90019, 90020, 40003.
One thread per host, 30 ms delay, rule/operation time bounds. Every active scan
specified method GET, recurse false, context ID and in-scope-only true.
Each run exported its context and used exact-host/path allowlist patterns.
Excel routes were explicitly excluded, including static-route collisions with
/usuarios/{usuario_id}.

ZAP used only the new internal scan network, without direct API/database access.
A separate gateway bridged the two internal lab networks. It rejected non-GET,
unapproved hosts/routes and stripped method-override headers, and forced a synthetic
Bearer token per API/role. The scanner did not receive JWT signing secrets or
normal credentials. The gateway is a scope barrier, not an API under test.

Sessions were inserted as lab fixtures before the baseline. GET /auth/me kept
these six sessions alive; this changes only ultima_actividad. No authentication
flow was exercised. Denied role operations (403), gateway-blocked mutations and
unselected rules are outside successful business-logic coverage.

Evidence in ../dast-runtime/phase2/latest-attempt.txt identifies the completed
attempt. It contains SUMMARY.md, summary.json, pre.json, post.json,
post-frozen.json, database-comparison.json and postflight-isolation.json, plus
seven directories with report.json, report.html, coverage.json and scope.context.
Private fixtures/config and preflight network evidence remain in the phase2 root.
Do not commit ../dast-runtime or print its token files.

The initial setup attempt failed on a client option after importing only the
filtered Identity contract and before any active scan. It is preserved separately.

At scan completion, gateway/ZAP containers were stopped and resources preserved
for review. After evidence approval, cleanup.py --execute removed the laboratory
and original secrets. Independent checks confirmed zero DAST containers, networks
and volumes, with unchanged inventories outside DAST. Versioned evidence remains.
No staging, commits or push performed. Reproduction requires a fresh laboratory;
no further scan is scheduled.
