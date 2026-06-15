# Command Surface Governance Pass

Issue:
Execute the `command-surface-governance-pass` benchmark task against the current repo-owned docs, validation guidance, and source-of-truth ordering.

Desired outcome:
`AGENTS.md`, `PLANS.md`, `README.md`, `docs/USAGE.md`, `Makefile`, `pytest.ini`, and `requirements.txt` agree on authoritative surfaces and practical validation entrypoints.

Explicit non-goals:
- New governance subsystems
- Expanding placeholder docs without repo-backed content
- Product-code changes unless governance truth depends on them

Relevant docs/files:
- `AGENTS.md`
- `PLANS.md`
- `README.md`
- `docs/USAGE.md`
- `Makefile`
- `pytest.ini`
- `requirements.txt`

Required validation:
- Confirm source-of-truth order matches actual repo usage.
- Confirm validation guidance references real commands only.
- Run `pytest -q tests/test_graph_invoice_auth.py tests/test_invoices_report.py tests/test_invoices_report_utils.py tests/test_monthly_invoices.py`.
- Run `make test` at the end if the environment supports a full-root proof.

Known decisions:
- Review-oriented benchmark tasks stay on-demand and are not part of this closure path.
- Placeholder docs remain placeholders unless another source-of-truth file requires concrete content.
- Reasoning level is `ai:deep`.

Missing decisions:
None after comparing the current repo-owned guidance files.

Reasoning level: `ai:deep`

Maximum initial files: `6`
