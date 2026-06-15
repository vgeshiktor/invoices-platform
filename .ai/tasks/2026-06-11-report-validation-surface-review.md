# Report Validation Surface Review

Issue:
First real governance task packet for report-generation documentation and validation coverage.

Desired outcome:
Verified, repo-backed guidance for JSON, CSV, summary CSV, and PDF report outputs across `README.md`, `docs/USAGE.md`, `Makefile`, and the current report tests.

Explicit non-goals:
- Parser or report behavior changes unless the current docs cannot be made accurate without them
- Changes to Gmail, Graph, monthly orchestration, or local-stack workflows outside report-generation references
- Expanding placeholder governance docs

Relevant docs/files:
- `README.md`
- `docs/USAGE.md`
- `Makefile`
- `apps/workers-py/src/invplatform/cli/invoices_report.py`
- `tests/test_invoices_report.py`
- `tests/test_invoices_report_utils.py`

Required validation:
- `pytest -q tests/test_invoices_report.py tests/test_invoices_report_utils.py`
- Manual doc-to-code consistency check for `make run-report`, `--summary-csv-output`, default PDF output behavior, `--pdf-vendor-subtotals`, `--no-pdf-vendor-subtotals`, and `--pdf-skip-single-vendor-subtotals`

Known decisions:
- Reasoning level is `ai:standard`
- Maximum initial files is `6`
- This is a docs-and-validation review first; product code changes stay out of scope unless the current docs are provably inaccurate

Missing decisions:
None after comparing docs, Makefile defaults, CLI flags, and tests.

Reasoning level: `ai:standard`

Maximum initial files: `6`
