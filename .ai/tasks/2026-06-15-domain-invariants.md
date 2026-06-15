# Task Packet Template
Desired outcome:
Define executable domain invariants for duplicate suppression, monthly idempotence, visible partial failure, explicit money rounding, multilingual preservation, quarantine visibility, report redaction, and explicit date/time semantics.
Explicit non-goals:
Do not redesign the full ingestion/report architecture or introduce a database/queue model.
Relevant docs/files:
- `docs/ARCHITECTURE.md`
- `docs/SECURITY-AND-DATA-HANDLING.md`
- `apps/workers-py/src/invplatform/cli/monthly_invoices.py`
- `apps/workers-py/src/invplatform/cli/invoices_report.py`
- `tests/test_monthly_invoices.py`
- `tests/test_graph_invoice_finder_e2e.py`
Required validation:
- targeted `pytest` for invariant coverage
- rerun the affected monthly/report test slices
Known decisions:
- invariants should be executable as tests, not prose-only guidance
- keep changes proportional to the current CLI-first, file-based system
Missing decisions:
- `TBD` if stronger cross-provider semantic dedupe than current hash/stem/text behavior is needed later
Reasoning level: `ai:deep`
max initial files: `6`
