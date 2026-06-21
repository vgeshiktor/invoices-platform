# Invoices Platform

Monorepo for invoice discovery, PDF collection, and invoice reporting across Gmail and Microsoft Graph.

## What Is Implemented

- Gmail invoice discovery and PDF download (`invplatform.cli.gmail_invoice_finder`)
- Microsoft Graph invoice discovery and PDF download (`invplatform.cli.graph_invoice_finder`)
- Monthly orchestration across providers with merge + dedup (`invplatform.cli.monthly_invoices`)
- PDF quarantine utility for non-invoice files (`invplatform.cli.quarantine_invoices`)
- Invoice parsing/report generation to JSON/CSV/Summary CSV/PDF (`invplatform.cli.invoices_report`)
- PDF report enhancements:
  - bilingual-safe rendering (Hebrew + English)
  - vendor grouping and optional vendor subtotal rows
  - configurable subtotal behavior (on/off, skip single-invoice vendors)
- Duplicate removal utility script (`scripts/remove_duplicate_invoices.py`)
- Minimal Go API health surface in `apps/api-go`
- Local dev stack via Docker Compose including `api-go`, `workers-py`, `db`, `mq`, and `n8n`

## Documentation Map

- `README.md` (this file): project overview + quick start + workflow map.
- `docs/USAGE.md`: full command reference and how-to usage for all current functionality.
- `docs/SECURITY-AND-DATA-HANDLING.md`: sensitive-data handling, token storage, logging, retention, and AI-evidence rules.
- `AGENTS.md`: stable repo operating rules for AI-assisted work.
- `PLANS.md`: current repo state, progress notes, and next-step guidance.
- `.ai/README.md`: task-packet and eval contract for substantial AI-assisted work.
- `docs/UX_REVIEW_METHOD.md`: journey-first UX review standard for product screens, prototypes, and design feedback.
- `docs/META_BILLING_GRAPH_API_EXPLORER.md`: ready-to-paste Graph API Explorer URLs for Meta billing diagnostics.
- `docs/FRONTEND_GITHUB_ISSUES.md`: repo-backed copy of the GitHub Weeks 1-10 frontend/control-plane backlog.
- `docs/FRONTEND_TELEMETRY.md`: frontend telemetry taxonomy and request-correlation conventions.
- `docs/FRONTEND_RELEASE_CHECKLIST.md`: release-readiness and rollback baseline for the frontend/control-plane surfaces.
- `integrations/openapi/invoices.yaml`: source-of-truth control-plane OpenAPI contract for the Weeks 1-10 roadmap, including the current `GET /healthz` surface.

## Documentation Approach

The docs structure in this repo follows these principles:

- Quick orientation in `README.md`, detailed how-to/reference in `docs/USAGE.md`.
- Task-first command examples (copy/paste ready).
- Explicitly separate current behavior from future/planned API scope.
- For UI-heavy work, define the user journey and primary decision before critiquing screen content or hierarchy.

References used for this structure:

- Diataxis framework: <https://diataxis.fr/>
- Google developer documentation style guide: <https://developers.google.com/style>
- Write the Docs style/principles:
  - <https://www.writethedocs.org/guide/writing/style-guides.html>
  - <https://www.writethedocs.org/guide/writing/docs-principles.html>

## Quick Start

### Prerequisites

- Python 3.11+
- Go 1.22+ (for `api-go`)
- Docker + Docker Compose (optional, for full local stack)

### Install dependencies (local Python workflow)

```bash
pip install -r requirements.txt
```

### Optional: prepare local stack environment

- Copy `.env.example` to `.env` before using Docker Compose-backed workflows.
- Set `GRAPH_CLIENT_ID` in `.env` if you plan to run Outlook/Graph monthly flows or the n8n bootstrap/daily workflows.

### Run tests

```bash
make test
```

### Run main workflows

```bash
# Gmail finder
make run-gmail START_DATE=2026-01-01 END_DATE=2026-02-01

# Graph finder
make run-graph START_DATE=2026-01-01 END_DATE=2026-02-01 GRAPH_CLIENT_ID=<your-client-id>

# Monthly orchestration (current month by default)
make run-monthly GRAPH_CLIENT_ID=<your-client-id>

# Parse invoices + build reports (JSON/CSV/summary/PDF)
make run-report REPORT_INPUT_DIR=invoices/invoices_01_2026

# Quarantine likely non-invoice PDFs
make quarantine

# Local stack lifecycle
make dev
make up
make down
make run-n8n

# Minimal Go API health surface
make -C apps/api-go run
```

For complete options and examples, use `docs/USAGE.md`.

## Key Outputs

- Provider fetch outputs:
  - `invoices/invoices_gmail_MM_YYYY`
  - `invoices/invoices_outlook_MM_YYYY`
- Consolidated monthly outputs:
  - `invoices/invoices_MM_YYYY`
  - `invoices/invoices_MM_YYYY/run_summary.json`
- Report outputs:
  - `report-*.json`, `report-*.csv`, `report-*.summary.csv`, `report-*.pdf` (or custom output paths)
  - `make run-report` defaults to `reports/invoice_report.json`, `reports/invoice_report.csv`, `reports/invoice_report.summary.csv`, and `reports/invoice_report.pdf`

## API Status (Current)

- Implemented in Go:
  - `GET /healthz`
- Planned and documented for the Weeks 1-10 roadmap:
  - auth/session surfaces
  - provider configuration and OAuth flows
  - collection jobs
  - reports and artifacts
  - schedules
  - audit events
- Current backend/runtime notes:
  - the Go API in `main` is still a minimal health-check baseline
  - `integrations/openapi/invoices.yaml` tracks the target control-plane contract
  - Python worker CLIs remain the source of truth for invoice discovery and report generation workflows

## Repo Layout

```text
invoices-platform/
├─ apps/
│  ├─ api-go/
│  └─ workers-py/
├─ docs/
│  └─ USAGE.md
├─ deploy/
├─ integrations/
├─ scripts/
├─ invoices/
└─ README.md
```

## Notes

- `archive/` contains historical finder scripts kept for comparison/debugging. Current supported entry points are under `apps/workers-py/src/invplatform/cli`.
- `docs/ONBOARDING.md` and `docs/CONTRIBUTING.md` are still placeholders. `docs/ARCHITECTURE.md` and `docs/SECURITY-AND-DATA-HANDLING.md` are repo-specific guidance.
