export type User = {
  id: string;
  email: string;
  displayName: string;
  tenantId: string;
  permissions: string[];
};

export type ProviderConfig = {
  id: string;
  tenantId: string;
  provider: "gmail" | "outlook";
  state: "connected" | "disconnected" | "expiring" | "error";
  connected: boolean;
  accountEmail?: string;
  health?: string;
  lastSyncAt?: string;
  scopes: string[];
  createdAt: string;
  updatedAt: string;
};

export type CollectionJob = {
  id: string;
  tenantId: string;
  status: "queued" | "running" | "succeeded" | "failed";
  providers: Array<"gmail" | "outlook">;
  month: number;
  year: number;
  requestId?: string;
  runSummaryPath?: string;
  invoicesDir?: string;
  retryOf?: string;
  error?: string;
  startedAt?: string;
  finishedAt?: string;
  createdAt: string;
  updatedAt: string;
};

export type ReportArtifact = {
  format: "json" | "csv" | "summary_csv" | "pdf";
  path: string;
};

export type Report = {
  id: string;
  tenantId: string;
  status: "queued" | "running" | "ready" | "failed";
  inputDir: string;
  formats: ReportArtifact["format"][];
  artifacts: ReportArtifact[];
  totals?: {
    netTotal: number;
    vatTotal: number;
    grossTotal: number;
  };
  error?: string;
  startedAt?: string;
  finishedAt?: string;
  createdAt: string;
  updatedAt: string;
};

export type Schedule = {
  id: string;
  tenantId: string;
  name: string;
  timezone: string;
  cron: string;
  providers: Array<"gmail" | "outlook">;
  status: "active" | "paused";
  nextRunAt?: string;
  lastRunAt?: string;
  lastRunStatus?: "queued" | "running" | "succeeded" | "failed";
  createdAt: string;
  updatedAt: string;
};

export type AuditEvent = {
  id: string;
  tenantId: string;
  action: string;
  entityType: string;
  entityId: string;
  requestId: string;
  message?: string;
  createdAt: string;
};

export type ApiList<T> = {
  items: T[];
};

export type ApiResult<T> = {
  data: T;
  requestId?: string;
};
