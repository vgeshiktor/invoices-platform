# Frontend Release Checklist

Baseline release-readiness and rollback guide for the control-plane surfaces introduced by the Weeks 1-10 roadmap.

## Pre-Release Checks

- `make verify` passes from the repo root.
- `cd apps/web && npm run e2e -- --reporter=line` passes.
- Control-plane auth flow still works:
  - login
  - refresh
  - logout
- Critical routes load with an authenticated session:
  - Overview
  - Providers
  - Collections
  - Reports
  - Schedules
  - Audit
- `X-Request-ID` appears in UI status surfaces after mutating actions.
- New OpenAPI changes are reflected in `apps/web/src/api/generated.ts`.

## Release Notes Inputs

- Notable API contract changes in `integrations/openapi/invoices.yaml`
- New UI routes or permission-gated surfaces
- Any in-memory limitations that still apply to the control-plane baseline

## Rollback Procedure

1. Revert the frontend/control-plane change set in git.
2. Re-run `make verify`.
3. Restart `apps/api-go` and the frontend dev/build artifact.
4. Validate:
   - `/healthz`
   - login flow
   - one read-only route such as `/audit`
5. If the issue is isolated to generated client drift, regenerate `apps/web/src/api/generated.ts` from the reverted OpenAPI contract before rebuilding.

## Known Baseline Limits

- Control-plane resources currently use in-memory backend storage.
- Collection/report runtime orchestration is still a baseline control surface, not a production scheduler/executor stack.
