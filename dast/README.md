# DAST ephemeral laboratory — phase 1

## Automated staging in CI

The `zap-staging` job in `.github/workflows/devsecops-pipeline.yml` runs in
`yeisonfblopez/DevSecOps-proyecto-Final-ci`, including reusable CI before simulated
deployment. The final CI gate requires this job to succeed in the mirror. The job
is intentionally skipped in other repositories, whose existing gates remain required.

`python dast/ci.py run --output reports/zap-staging` builds the current checkout's
Identity, Permissions and Audit services in a disposable staging project. The runtime
is selected by `IAM_DAST_RUNTIME`, outside the checkout, normally under RUNNER_TEMP.
The normal `.env`, Compose, database, SMTP and users are not used. No ports are published.

The job executes the existing seven API/role active GET scans through the strict
gateway, validates all 39 operations and five selected rules, and rejects incomplete
scans, unexpected database changes or MEDIUM/HIGH alerts. LOW/informational alerts
remain in the report. It uploads sanitized HTML/JSON reports, coverage, gate,
database comparison and cleanup evidence as `zap-staging-evidence` for 30 days.
Runtime credentials, JWT/JTI, contexts, raw logs and per-cell database digests are omitted.

Cleanup executes on success/failure and has an `always()` fallback step. It only
removes the exact labelled project created by this runner; it never prunes Docker or
uses normal Compose. For a local reproduction, set IAM_DAST_RUNTIME to a fresh
directory outside the checkout before running the command. `python dast/ci.py cleanup`
refuses runtime directories without its ownership marker.

This automates active ZAP against the defined staging scope. It is not complete
application DAST: login/MFA, XLSX, POST/PUT/PATCH/DELETE and frontend discovery remain
outside the GET-only laboratory. The sections below preserve the manual phases and
their historical evidence.

Source: feat/bulk-users-excel-20261005 at 2b0abd4694164ae11b36aab136f2255735c0e598.
Standalone compose.zap.yml; no normal Compose overrides, environment file, secrets,
network or database mounts. No published ports. Phase 2 is described in PHASE2.md.

Runtime secrets and generated OpenAPI live OUTSIDE the checkout in ../dast-runtime.
Never commit that directory. zap.env is mode 0600, runtime directory is mode 0700.
The wrapper sanitizes inherited Compose/application variables.

Fresh creation (prepare refuses an existing runtime directory):

    python3 dast/prepare.py
    python3 dast/dc.py build identity audit-service permissions support
    python3 dast/dc.py up -d --wait postgres
    python3 dast/dc.py run --rm -T support /support/seed.py
    python3 dast/dc.py up -d --wait identity audit-service permissions
    python3 dast/export.py
    python3 dast/probe_host.py
    python3 dast/check.py
    python3 dast/record_seed.py
    python3 -m unittest discover -s dast -p 'test_*.py' -v

Seed refuses a non-empty identity database. It creates six identities with
@example.invalid addresses, two ZAP companies and valid roles/MFA fixtures.
The SQL initialization also creates three academic companies (five total).
No SMTP credentials are supplied; no mail, dispatcher, sync worker or bootstrap runs.

export.py creates short-lived synthetic session fixtures directly in iam_zap and
checks access through the actual API authentication dependencies. It does NOT
validate login, MFA enrolment or TOTP verification. Tokens are not printed or saved.
Authenticated GETs update session activity as normal; this is not a read-only DB.
Every request issued by the validation client is GET. The contracts contain only
15 GET operations, excluding write operations, Excel and POST /eventos.
Audit's contract contains only /health. Contracts are not a server-side firewall;
API write routes still exist, and any future scanner must use the allowlist/context.
Phase 2 was separately authorized and completed; see PHASE2.md.

Reports: ../dast-runtime/{validation,isolation,network-probes,schema-seed}.json
Contracts: ../dast-runtime/openapi/*-readonly.openapi.json

Pause while retaining the ephemeral data:

    python3 dast/dc.py stop

Restart and revalidate (export creates fresh 30-minute session fixtures):

    python3 dast/dc.py up -d --wait postgres identity audit-service permissions
    python3 dast/export.py
    python3 dast/probe_host.py
    python3 dast/check.py

Destroy ONLY this laboratory's containers, network and volume:

    python3 dast/cleanup.py          # read-only inventory
    python3 dast/cleanup.py --execute  # only after evidence approval

The cleanup wrapper uses only this standalone Compose and exact project labels,
then verifies zero project containers, networks and volumes. It removes ephemeral
secret files only after Docker cleanup succeeds. Evidence remains preserved.
Keep runtime configuration until cleanup completes; never use global docker prune.
No active scan has been authorized or executed in phase 1.

## Reproducing the authorized active phase

On a fresh phase-1 laboratory, with explicit authorization to run active scans:

    python3 dast/phase2.py prepare
    python3 dast/preflight2.py
    python3 dast/phase2.py run
    python3 dast/summarize2.py
    python3 dast/postflight2.py

phase2.py run stops the gateway before saving the post-scan snapshot. No normal
login/MFA flow is used. The ZAP image is pinned to its pullable registry digest.
The gateway connects to explicit lab API IPs, avoiding DNS alias ambiguity, and
has only one writable log-file mount. These reproduction refinements were made
after the recorded scan; no additional active scan was executed for the closure.

## Evidence closure

Versioned evidence: docs/evidencias/2026-10-11/dast-active-readonly.
The reduced bundle contains JSON reports; HTML reports remain local. Raw evidence and secrets
remain outside the checkout. Nine offline safety/integrity tests passed.
No git staging, commit or push has been performed. Cleanup status is recorded in the evidence SUMMARY.md.

The nine offline tests use archived contracts and temporary configuration only;
they do not require the laboratory, its runtime directory or its original secrets.
