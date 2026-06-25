# Security and Data Handling

## Purpose

This repository handles invoice PDFs, mailbox metadata, and report artifacts. Those materials often contain financial, personal, and operational data. This document defines the minimum handling rules for local runs, automation, tests, AI-assisted work, and evidence captured in the repo.

Use this document together with:

- [README.md](../README.md) for the supported runtime surfaces
- [USAGE.md](./USAGE.md) for current command behavior
- [ARCHITECTURE.md](./ARCHITECTURE.md) for where sensitive data flows through the system
- [AGENTS.md](../AGENTS.md) and [.ai/README.md](../.ai/README.md) for AI-assisted workflow rules

## Data Classification

Treat the following as sensitive by default:

- invoice PDFs downloaded by `gmail_invoice_finder.py`, `graph_invoice_finder.py`, and `monthly_invoices.py`
- email content used during discovery, including:
  - subject lines
  - sender addresses
  - preview text
  - message body text or HTML
  - attachment names when they can reveal vendor, invoice number, or person-specific details
- generated report outputs under `reports/` and `report-*`
- candidate and rejection dumps produced by `--save-candidates`, `--save-nonmatches`, `--save-json`, `--save-csv`, or `--download-report`
- OAuth and token material such as `credentials.json`, `token.json`, and MSAL token cache files

Unless a file is clearly synthetic and intentionally sanitized for tests or docs, assume it contains production or production-adjacent data.

## OAuth and MSAL Token Caches

The repo’s implemented auth surfaces currently include:

- Gmail OAuth files:
  - `credentials.json`
  - `token.json`
- Microsoft Graph/MSAL cache files:
  - `--token-cache-path`
  - `GRAPH_TOKEN_CACHE_PATH`
  - the default `~/.msal_graph_invoice_cache.bin` or repo-local `./.msal_token_cache.bin` patterns used by current workflows

Handling rules:

- Never commit OAuth client secrets, refresh tokens, access tokens, or serialized token caches.
- Keep token files outside shared screenshots, logs, task packets, or evidence bundles.
- Prefer persistent token-cache paths only on trusted local machines or controlled automation environments.
- Do not paste serialized cache blobs, bearer tokens, OAuth codes, or browser bootstrap responses into issues, docs, PRs, or Codex transcripts.
- If a token cache is suspected to be exposed, rotate or revoke it and replace the file instead of reusing it.

## Prohibited Logging

The current CLIs support debug and audit outputs. Those modes are useful for local troubleshooting, but they can expose sensitive content.

Do not log or preserve the following in committed files, PR descriptions, or shared evidence:

- raw email body text or HTML
- full subject lines from production mailboxes when they include names, amounts, invoice ids, or addresses
- full sender email addresses from production data
- attachment bytes, PDF text previews, or extracted invoice field dumps from real invoices
- OAuth tokens, device codes, bearer headers, session cookies, or serialized token caches
- full candidate/non-match dumps from real mailbox traffic
- full report rows generated from real production PDFs

Extra caution for current debug paths:

- `gmail_invoice_finder.py` and `graph_invoice_finder.py` emit message-level progress and optional candidate/non-match artifacts.
- `invoices_report.py --debug` prints text previews and parsing summaries that may expose invoice contents.

Policy:

- Use debug output only for sanitized fixtures or local operator troubleshooting.
- Do not commit debug logs or copy them into repo docs when they come from real mailboxes or real PDFs.
- When evidence is required, redact first and prefer summaries over raw dumps.

## Sanitized Fixture Requirements

Test and demo fixtures must be sanitized or synthetic.

Acceptable fixture patterns in this repo:

- synthetic PDF-like bytes, such as `tests/fixtures/graph_september_2025.py`
- invented IDs, links, and message bodies under fixture-only domains like `fixtures.example`
- synthetic invoice/report artifacts created only to exercise parser or workflow behavior

Fixture requirements:

- Do not add real OAuth files, real token caches, or real mailbox exports to `tests/`, `docs/`, `.ai/`, or `fixtures/`.
- Do not add real invoice PDFs or real report outputs as committed fixtures.
- Replace or mask real names, addresses, account numbers, invoice ids, payment references, and URLs unless the value is obviously fake.
- If a production sample is needed to reproduce a parser bug, convert it into a minimized sanitized fixture before committing it.
- Keep the minimum structure required to preserve the failing behavior; strip everything else.

## File Permissions and Local Storage

This repo is file-oriented today, so local filesystem hygiene matters.

Minimum handling rules:

- Keep invoice directories, report outputs, and token files readable only by the local user or the minimal automation account that needs them.
- Do not place token files in broadly shared directories, public desktop folders, or synced evidence folders.
- Treat `invoices/`, `reports/`, `report-*`, and mailbox-derived JSON/CSV outputs as sensitive local working data.
- When using Docker or n8n mounts, ensure the mounted workspace and token-cache paths are not broadly readable by unrelated users on the host.
- Do not rely on `.gitignore` as the only protection for sensitive files; local permissions still matter.

## Retention and Deletion

The repo currently creates several classes of derived artifacts:

- downloaded PDFs under provider and monthly folders
- quarantine directories
- duplicate-review folders
- JSON/CSV/report outputs
- candidate/non-match and download-report audit files

Retention rules:

- Keep sensitive local artifacts only as long as needed for the immediate operational or debugging task.
- Delete local candidate dumps, debug outputs, quarantined files, and report artifacts once the investigation or reporting run is complete.
- Remove obsolete token caches when an automation path changes or when a local machine is no longer trusted for access.
- Prefer regenerating derived files from source workflows instead of keeping old sensitive snapshots indefinitely.

When deleting data:

- Delete both the primary artifact and nearby copies made for debugging, screenshots, manual exports, or ad hoc analysis.
- If a sensitive file was accidentally committed, remove it from the current tree immediately and follow the team’s history-rewrite or rotation process as needed.

## Permitted External Network Access

Only network access required by implemented repo workflows is permitted.

Allowed categories in the current codebase:

- Gmail OAuth and Gmail API access used by `gmail_invoice_finder.py`
- Microsoft identity and Microsoft Graph access used by `graph_invoice_finder.py`
- invoice-document hosts reached from mailbox-discovered links during invoice retrieval, including direct PDF hosts and provider-specific flows such as Bezeq/YES-style retrieval paths
- Meta Graph endpoints used by `meta_billing_export.py`
- package/dependency registries only during explicit install/build/test setup steps

Not allowed:

- sending invoice PDFs, email bodies, report rows, or token material to unrelated third-party services
- ad hoc uploads of production files to external AI tools, pastebins, screenshots-as-a-service tools, or personal cloud drives
- introducing new external network dependencies for data handling without documenting the purpose and reviewing the exposure

If a workflow needs a new outbound destination, document it before use and treat it as a security review point.

## Skill Adoption and Data Exposure

Treat third-party or public skills like executable dependencies.

- third-party/public skills are treated like executable dependencies and must be reviewed before use
- pinning and audit expectations apply before shared adoption
- real or production data should not flow through public-prototype-only skills
- if a skill will touch sensitive, side-effectful, or external-tool work, apply the repo's existing trust-level, HITL, and read-only rules before adoption
- do not assume marketplace popularity is a security signal; prefer official, internal, or otherwise vetted sources and review what the skill can execute in your context

## Production Data Prohibition for Agent Evaluations

Agent-evaluation and benchmark material must not use production data.

This applies to:

- `.ai/evals/tasks.yaml`
- `.ai/evals/results.csv`
- task packets under `.ai/tasks/`
- agent prompts, transcripts, or attached evidence used to compare tools or workflows

Rules:

- Do not use real invoice PDFs, real mailbox exports, or real report outputs as evaluation fixtures.
- Do not paste production message bodies, invoice text, or report tables into benchmark tasks.
- Do not record benchmark results that depend on undisclosed production inputs.
- When an evaluation needs realistic structure, derive a sanitized fixture first and describe it as synthetic.

## Redaction Requirements for Codex Evidence

Codex evidence includes any artifact shared to explain, validate, or review work, including:

- screenshots
- pasted logs
- terminal transcripts
- task packets
- markdown reports
- JSON/CSV snippets
- PR descriptions and review comments

Before including evidence derived from sensitive runs:

- redact names, email addresses, invoice ids, payment references, account numbers, and street-address-like content
- remove or mask bearer tokens, OAuth codes, token-cache blobs, cookies, and auth headers
- replace direct invoice/report file paths when the path itself reveals customer or vendor details
- crop screenshots to the minimum necessary area
- prefer aggregate counts, statuses, or summaries over raw rows or raw message previews

Allowed evidence style:

- “10 PDFs downloaded, 2 quarantined, 1 duplicate skipped”
- “MSAL cache bootstrap required; non-interactive run returned `AUTH_REQUIRED` until cache was seeded”
- “Parser failed on a sanitized municipal fixture and passed after the normalization fix”

Disallowed evidence style:

- full screenshot of a real inbox or invoice PDF
- pasted raw report rows from production outputs
- copied debug preview text from `invoices_report.py --debug` against real documents
- candidate/non-match JSON copied from a real mailbox run

## Commit and Review Guardrails

Before committing or opening a PR:

- confirm no token files, caches, local reports, or invoice PDFs are staged
- confirm new fixtures are sanitized
- confirm docs and evidence do not include raw production content
- confirm screenshots and transcripts are redacted

If unsure whether something is sensitive, treat it as sensitive and redact or exclude it.
