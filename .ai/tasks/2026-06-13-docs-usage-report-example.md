# Docs Usage Report Example

Issue:
Execute the `docs-usage-report-example` benchmark task against the current report-generation docs and Make target behavior.

Desired outcome:
Report-generation examples and output-path language stay aligned with the current `make run-report` surface without inventing behavior.

Explicit non-goals:
- Parser or report code changes unless doc truth requires them
- Monthly, Graph, Gmail, or local-stack workflow changes outside report-generation references

Relevant docs/files:
- `README.md`
- `docs/USAGE.md`
- `Makefile`

Required validation:
- Confirm command examples match current `make run-report` behavior.
- Confirm output-path language stays accurate for JSON, CSV, summary CSV, and PDF outputs.
- Run `pytest -q tests/test_invoices_report.py tests/test_invoices_report_utils.py` if report-facing wording changes materially.

Known decisions:
- Existing report docs were already close to implementation and may only need wording tightening.
- Reasoning level is `ai:light`.

Missing decisions:
None after comparing the docs with `Makefile`.

Reasoning level: `ai:light`

Maximum initial files: `6`
