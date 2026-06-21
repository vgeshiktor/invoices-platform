# Frontend GitHub Issues

Repo-backed snapshot of the live GitHub milestone backlog for Weeks 1-10.

Source:
- GitHub issues `#2` through `#45`
- GitHub milestones `Week 1` through `Week 10`
- Snapshot date: `2026-06-19`

This document is the checked-in companion to the live GitHub tracker. Update both when roadmap scope changes.

## Week 1

- `FE-001` `#2`: Scaffold `apps/web` workspace with Vite + TypeScript
  - Depends on: none
  - Acceptance: `apps/web` exists and `dev/build/test` scripts run in CI
- `FE-002` `#3`: Add frontend quality gates
  - Depends on: `FE-001`
  - Acceptance: lint and type checks are required and fail CI on violations
- `FE-003` `#4`: Implement app shell and protected route skeleton
  - Depends on: `FE-001`
  - Acceptance: app layout and protected routes exist
- `FE-004` `#5`: Generate typed API client from OpenAPI contract
  - Depends on: `FE-001`
  - Acceptance: generated client compiles and is used by at least one page
- `FE-005` `#6`: Add global error boundary and fallback UX
  - Depends on: `FE-003`
  - Acceptance: uncaught UI errors render a safe fallback with retry
- `FE-006` `#7`: Add design tokens and baseline component styles
  - Depends on: `FE-003`
  - Acceptance: tokenized color, spacing, and type scale are used in base components
- `FE-007` `#8`: Add frontend build/test steps to CI pipeline
  - Depends on: `FE-002`
  - Acceptance: CI runs frontend lint/type/test/build and blocks failures

## Week 2

- `BE-001` `#9`: Implement user/session auth endpoints for tenant login
  - Depends on: none
  - Acceptance: `/auth/*` and `/v1/me` exist with tenant-safe session handling
- `FE-101` `#10`: Build login/logout UI and protected-route flow
  - Depends on: `BE-001`
  - Acceptance: users can login/logout and protected screens require a session
- `FE-102` `#11`: Implement role-aware navigation and action-level RBAC UX
  - Depends on: `FE-101`
  - Acceptance: restricted actions are hidden or disabled according to permissions
- `FE-103` `#12`: Implement secure session storage and renew flow
  - Depends on: `FE-101`
  - Acceptance: session survives refresh and handles expiry gracefully
- `FE-104` `#13`: Add auth unit/integration/e2e coverage
  - Depends on: `FE-101`
  - Acceptance: login journey passes in CI with stable e2e coverage

## Week 3

- `BE-101` `#14`: Add provider configuration domain and tenant-scoped CRUD APIs
  - Depends on: `BE-001`
  - Acceptance: provider configs persist per tenant and are queryable safely
- `BE-102` `#15`: Implement provider OAuth lifecycle endpoints
  - Depends on: `BE-101`
  - Acceptance: OAuth start/callback/refresh/revoke supported for Gmail and Outlook
- `FE-201` `#16`: Build provider settings screen
  - Depends on: `BE-102`
  - Acceptance: users can connect and manage provider state from UI
- `FE-202` `#17`: Show provider health and sync metadata
  - Depends on: `BE-102`
  - Acceptance: token health and last sync status are visible
- `FE-203` `#18`: Add provider flow tests for Gmail and Outlook
  - Depends on: `FE-201`
  - Acceptance: connect/disconnect/re-auth flows are covered end to end

## Week 4

- `BE-201` `#19`: Add `collection_jobs` model and APIs
  - Depends on: `BE-102`
  - Acceptance: collection lifecycle `queued/running/succeeded/failed` is persisted and queryable
- `FE-301` `#21`: Build "Collect current month" wizard with provider selector
  - Depends on: `BE-201`
  - Acceptance: a run can be started in three clicks or fewer and returns a run ID/status
- `FE-302` `#22`: Build collection run detail/progress page
  - Depends on: `FE-301`
  - Acceptance: live status, file counts, and errors stay visible through completion

## Week 5

- `BE-202` `#20`: Wire collection jobs to provider executors and parse pipeline
  - Depends on: `BE-201`
  - Acceptance: collection runs produce files and parse job links with failure details
- `FE-303` `#23`: Add retry UX for failed collection runs
  - Depends on: `BE-202`
  - Acceptance: retry action works safely with clear status feedback
- `FE-304` `#24`: Add collection journey e2e coverage
  - Depends on: `FE-301`
  - Acceptance: CI validates happy-path and representative failure flows

## Week 6

- `FE-401` `#25`: Build report creation flow with output format selection
  - Depends on: existing report APIs
  - Acceptance: users can request reports with selected formats and filters
- `FE-402` `#26`: Build report list/detail views with status tracking
  - Depends on: `FE-401`
  - Acceptance: list/detail views show accurate report status transitions
- `FE-403` `#27`: Add report artifact download actions
  - Depends on: `FE-402`
  - Acceptance: JSON/CSV/SUMMARY/PDF downloads work when artifacts are available
- `FE-404` `#28`: Render totals/VAT summary cards in report UX
  - Depends on: `FE-402`
  - Acceptance: totals and VAT shown in the UI match backend report data
- `FE-405` `#29`: Add report journey integration and e2e tests
  - Depends on: `FE-401`
  - Acceptance: report create -> status -> download is green in CI

## Week 7

- `BE-301` `#30`: Add schedule model and tenant-scoped schedule CRUD APIs
  - Depends on: `BE-201`
  - Acceptance: schedules persist with timezone and pause/resume support
- `FE-501` `#32`: Build schedule create/edit/pause/resume UI
  - Depends on: `BE-301`
  - Acceptance: users can fully manage daily schedules from the UI
- `FE-502` `#33`: Build schedule history and next-run visibility UX
  - Depends on: `FE-501`
  - Acceptance: last run, next run, and recent statuses are visible

## Week 8

- `BE-302` `#31`: Implement scheduler runtime and schedule-triggered run linkage
  - Depends on: `BE-301`
  - Acceptance: scheduled execution creates traceable collection runs at the configured time
- `FE-503` `#34`: Add scheduling e2e coverage
  - Depends on: `FE-501`
  - Acceptance: schedule create/update and run visibility passes in CI

## Week 9

- `BE-401` `#35`: Add tenant-scoped audit event query API
  - Depends on: existing audit writes
  - Acceptance: audit events can be listed and filtered per tenant for timeline UX
- `FE-601` `#36`: Define and document frontend telemetry event taxonomy
  - Depends on: `FE-001`
  - Acceptance: a versioned event dictionary is approved and referenced in implementation
- `FE-602` `#37`: Add frontend OTel + Sentry instrumentation
  - Depends on: `FE-601`
  - Acceptance: key interactions produce traces and runtime errors capture useful context
- `FE-603` `#38`: Propagate and display request correlation IDs
  - Depends on: `FE-301`
  - Acceptance: `X-Request-ID` is surfaced in key flows and copyable for support
- `FE-604` `#39`: Build tenant activity timeline UI from audit events
  - Depends on: `BE-401`
  - Acceptance: users can filter and inspect chronological audit events
- `FE-605` `#40`: Add support bundle export for failed run diagnostics
  - Depends on: `FE-603`
  - Acceptance: support bundle export includes relevant request IDs and status context

## Week 10

- `FE-701` `#41`: Enforce frontend testing pyramid in CI
  - Depends on: `FE-001`
  - Acceptance: unit, integration, and e2e suites all run as required checks
- `FE-702` `#42`: Enforce `>=80%` frontend coverage gate
  - Depends on: `FE-701`
  - Acceptance: CI blocks merges below the frontend coverage threshold
- `FE-703` `#43`: Add accessibility quality gate
  - Depends on: `FE-003`
  - Acceptance: no P1/P2 accessibility violations on critical journeys
- `FE-704` `#44`: Add Lighthouse mobile performance budgets
  - Depends on: `FE-003`
  - Acceptance: performance budgets are defined and enforced on key routes
- `FE-705` `#45`: Create release readiness checklist and rollback runbook
  - Depends on: `FE-701`
  - Acceptance: release checklist and rollback procedure exist and are reviewed

## Notes

- This backlog is dependency-ordered product scope, not a literal time commitment.
- When repo behavior diverges from GitHub issue text, update this file and the matching issue together.
