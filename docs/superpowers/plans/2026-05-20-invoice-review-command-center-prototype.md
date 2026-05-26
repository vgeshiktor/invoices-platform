# Invoice Review Command Center Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce the repo-backed design package, Figma approval frames, and GitHub tracker structure for the invoice review command center prototype.

**Architecture:** The repo stores the written spec, realistic fixture data, screenshot references, and tracker manifest. Figma is the source of truth for the approval frames. GitHub mirrors the milestone/epic/issue structure defined in the repo so implementation can start from an approved prototype rather than an abstract design brief.

**Tech Stack:** Markdown, JSON, shell automation, Figma plugin tooling, GitHub issue automation

---

### Task 1: Create the local design-source package

**Files:**
- Create: `docs/superpowers/specs/2026-05-20-invoice-review-command-center-design.md`
- Create: `docs/superpowers/plans/2026-05-20-invoice-review-command-center-prototype.md`
- Create: `docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/README.md`

- [ ] Add the approved design spec to the repo.
- [ ] Save the implementation plan to the repo.
- [ ] Add a package README that links fixtures, tracker manifest, screenshots, and the Figma file.

### Task 2: Create realistic prototype fixtures

**Files:**
- Create: `docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/invoice-fixtures.json`

- [ ] Derive the fixture schema from `InvoiceRecord`.
- [ ] Create a curated fixture set covering normal, low-confidence, duplicate, overdue, quarantined, uncategorized, municipal, and mixed-source states.
- [ ] Include list-oriented booleans such as `needsReview`, `isOverdue`, and `isQuarantined` so the prototype is deterministic.

### Task 3: Create tracker manifest and automation helper

**Files:**
- Create: `docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/github-tracker-manifest.json`
- Create: `scripts/create_invoice_review_command_center_tracker.sh`

- [ ] Encode the milestone, umbrella epic, epics, and issue tree in a machine-readable manifest.
- [ ] Add an idempotent shell script that reads the structure and creates the milestone and issues through `gh`.
- [ ] Make the script safe to rerun by checking for existing milestone or issue titles first.

### Task 4: Create the Figma prototype

**Files:**
- Update: `docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/README.md`

- [ ] Create a new Figma design file named for the invoice review command center prototype.
- [ ] Build the shared shell, summary band, list patterns, and drill-down patterns.
- [ ] Create four approval frames:
  - desktop today
  - desktop this month
  - mobile today
  - mobile detail
- [ ] Export or capture screenshot references for those frames.
- [ ] Write the Figma file URL and screenshot references into the artifact README.

### Task 5: Create the GitHub tracker

**Files:**
- Update: `docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/README.md`

- [ ] Create the milestone `Invoice Review Command Center Prototype`.
- [ ] Create the umbrella epic issue.
- [ ] Create issues `FE-801` through `FE-1104` with labels matching repo conventions.
- [ ] Record the resulting GitHub issue numbers in the artifact README.

### Task 6: Verify and capture follow-up work

**Files:**
- Update: `docs/superpowers/artifacts/2026-05-20-invoice-review-command-center/README.md`

- [ ] Verify the four approval frames exist.
- [ ] Verify the fixture set covers all required states.
- [ ] Verify the tracker matches the milestone/epic/issue plan.
- [ ] Record any deferred UX issues explicitly rather than leaving ambiguous debt.
