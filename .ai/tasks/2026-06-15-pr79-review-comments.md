# PR 79 Review Comments
Desired outcome:
- Address all actionable unresolved review comments on PR 79 without regressing invoice parsing behavior.

Explicit non-goals:
- Resolve GitHub threads or post review replies.
- Refactor unrelated invoice parsing paths.

Relevant docs/files:
- `apps/workers-py/src/invplatform/cli/invoices_report.py`
- `tests/test_invoices_report_utils.py`
- `AGENTS.md`
- `PLANS.md`

Required validation:
- `pytest tests/test_invoices_report_utils.py -k 'prefers_positive_summary_rate or skips_iso_date_tokens'`

Known decisions:
- Work in the current checkout to preserve existing in-progress local changes.
- Limit fixes to the two unresolved Codex review threads on PR 79.

Missing decisions:
- None.

Reasoning level: `ai:review`
max initial files: `6`
