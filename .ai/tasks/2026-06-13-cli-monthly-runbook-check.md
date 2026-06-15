# CLI Monthly Runbook Check

Issue:
Execute the `cli-monthly-runbook-check` benchmark task against the current monthly orchestration docs, auth guidance, and test-backed behavior.

Desired outcome:
Monthly-orchestration docs stay internally consistent across `README.md`, `docs/USAGE.md`, `Makefile`, and the current auth/monthly tests.

Explicit non-goals:
- Product changes outside minimal truth-preserving fixes
- New scheduling features or undocumented auth flows
- Expanding beyond monthly orchestration and its Graph token guidance

Relevant docs/files:
- `README.md`
- `docs/USAGE.md`
- `Makefile`
- `tests/test_monthly_invoices.py`
- `tests/test_graph_invoice_auth.py`

Required validation:
- Compare `run-monthly` examples against current Makefile variables.
- Verify scheduler notes do not conflict with the documented auth flow.
- Run `pytest -q tests/test_monthly_invoices.py tests/test_graph_invoice_auth.py`.

Known decisions:
- `GRAPH_CLIENT_ID` is the implemented environment variable for monthly Graph flows.
- Reasoning level is `ai:standard`.

Missing decisions:
None after comparing docs, Makefile, and tests.

Reasoning level: `ai:standard`

Maximum initial files: `6`
