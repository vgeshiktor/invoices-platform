# Frontend Telemetry Taxonomy

Version: `v0`
Status: baseline contract for Weeks 9-10 implementation

## Goals

- Keep request correlation visible across the UI and Go API.
- Define stable event names before deeper OpenTelemetry/Sentry wiring expands.
- Make support-bundle exports and audit review use the same identifiers.

## Request Correlation

- Every Go API response should emit `X-Request-ID`.
- Frontend actions should capture the latest `X-Request-ID` for:
  - provider connect/refresh/revoke
  - collection create/retry
  - report create
  - schedule create/pause/resume
  - audit timeline loads when relevant to support work
- Support bundles should embed the request IDs associated with the exported state.

## Event Families

- `auth.*`
  - `auth.session_started`
  - `auth.session_refreshed`
  - `auth.session_ended`
- `providers.*`
  - `providers.config_created`
  - `providers.oauth_started`
  - `providers.oauth_completed`
  - `providers.oauth_refreshed`
  - `providers.oauth_revoked`
- `collections.*`
  - `collections.run_created`
  - `collections.run_retried`
  - `collections.support_bundle_exported`
- `reports.*`
  - `reports.run_created`
  - `reports.artifact_requested`
- `schedules.*`
  - `schedules.created`
  - `schedules.paused`
  - `schedules.resumed`
- `audit.*`
  - `audit.timeline_loaded`

## Required Event Fields

- `event_name`
- `event_version`
- `tenant_id`
- `request_id`
- `route`
- `timestamp`

Optional fields:
- `entity_type`
- `entity_id`
- `provider`
- `status`
- `error_message`

## Baseline Instrumentation Notes

- The current repo baseline exposes the request ID in UI status surfaces and persists it in audit events.
- Deeper OTel span creation and Sentry runtime capture remain follow-on work, but new events should keep the names above stable.
