// Generated from integrations/openapi/invoices.yaml by scripts/generate-api-client.mjs.

export const operations = {
  "getHealthz": {
    "method": "GET",
    "path": "/healthz"
  },
  "login": {
    "method": "POST",
    "path": "/auth/login"
  },
  "logout": {
    "method": "POST",
    "path": "/auth/logout"
  },
  "refreshSession": {
    "method": "POST",
    "path": "/auth/refresh"
  },
  "getCurrentUser": {
    "method": "GET",
    "path": "/v1/me"
  },
  "listProviderConfigs": {
    "method": "GET",
    "path": "/v1/provider-configs"
  },
  "createProviderConfig": {
    "method": "POST",
    "path": "/v1/provider-configs"
  },
  "getProviderConfig": {
    "method": "GET",
    "path": "/v1/provider-configs/{providerConfigId}"
  },
  "updateProviderConfig": {
    "method": "PATCH",
    "path": "/v1/provider-configs/{providerConfigId}"
  },
  "startProviderOAuth": {
    "method": "POST",
    "path": "/v1/provider-configs/{providerConfigId}/oauth/start"
  },
  "completeProviderOAuth": {
    "method": "POST",
    "path": "/v1/provider-configs/{providerConfigId}/oauth/callback"
  },
  "refreshProviderOAuth": {
    "method": "POST",
    "path": "/v1/provider-configs/{providerConfigId}/oauth/refresh"
  },
  "revokeProviderOAuth": {
    "method": "POST",
    "path": "/v1/provider-configs/{providerConfigId}/oauth/revoke"
  },
  "listCollectionJobs": {
    "method": "GET",
    "path": "/v1/collection-jobs"
  },
  "createCollectionJob": {
    "method": "POST",
    "path": "/v1/collection-jobs"
  },
  "getCollectionJob": {
    "method": "GET",
    "path": "/v1/collection-jobs/{collectionJobId}"
  },
  "retryCollectionJob": {
    "method": "POST",
    "path": "/v1/collection-jobs/{collectionJobId}/retry"
  },
  "listReports": {
    "method": "GET",
    "path": "/v1/reports"
  },
  "createReport": {
    "method": "POST",
    "path": "/v1/reports"
  },
  "getReport": {
    "method": "GET",
    "path": "/v1/reports/{reportId}"
  },
  "getReportArtifact": {
    "method": "GET",
    "path": "/v1/reports/{reportId}/artifacts/{artifactFormat}"
  },
  "listSchedules": {
    "method": "GET",
    "path": "/v1/schedules"
  },
  "createSchedule": {
    "method": "POST",
    "path": "/v1/schedules"
  },
  "getSchedule": {
    "method": "GET",
    "path": "/v1/schedules/{scheduleId}"
  },
  "updateSchedule": {
    "method": "PATCH",
    "path": "/v1/schedules/{scheduleId}"
  },
  "pauseSchedule": {
    "method": "POST",
    "path": "/v1/schedules/{scheduleId}/pause"
  },
  "resumeSchedule": {
    "method": "POST",
    "path": "/v1/schedules/{scheduleId}/resume"
  },
  "listAuditEvents": {
    "method": "GET",
    "path": "/v1/audit-events"
  }
} as const;

export type OperationName = keyof typeof operations;

export function buildPath(
  operation: OperationName,
  params?: Record<string, string | number>
): string {
  let route = operations[operation].path as string;
  for (const [key, value] of Object.entries(params ?? {})) {
    route = route.replace(`{${key}}`, String(value));
  }
  return route;
}
