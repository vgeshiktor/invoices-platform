# Task Packet Template
Desired outcome:
Convert `.ai/evals/tasks.yaml` toward executable scenarios by adding a runnable `cross-provider-dedup` eval with fixture, make target, expected counts, forbidden conditions, and pass/fail threshold metadata.
Explicit non-goals:
Do not fabricate eval results in `.ai/evals/results.csv` and do not implement the broader P1 hardening backlog in this change.
Relevant docs/files:
- `.ai/evals/tasks.yaml`
- `.ai/evals/results.csv`
- `Makefile`
- `tests/test_monthly_invoices.py`
- `tests/test_domain_invariants.py`
- `docs/SECURITY-AND-DATA-HANDLING.md`
Required validation:
- targeted `pytest` for eval catalog and runner contract
- run `make eval-cross-provider-dedup`
Known decisions:
- keep legacy review-oriented entries preserved separately from executable scenarios if they are not yet runnable
- fixtures must stay synthetic and local to `.ai/evals/fixtures/`
Missing decisions:
- `TBD` whether future eval scenarios should emit a shared JSON schema or integrate with a dedicated eval runner
Reasoning level: `ai:deep`
max initial files: `6`
