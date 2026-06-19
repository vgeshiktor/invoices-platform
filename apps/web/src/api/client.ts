import { buildPath } from "./generated";
import type {
  ApiList,
  ApiResult,
  AuditEvent,
  CollectionJob,
  ProviderConfig,
  Report,
  ReportArtifact,
  Schedule,
  User,
} from "./types";

export class ApiError extends Error {
  status: number;
  requestId?: string;

  constructor(message: string, status: number, requestId?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.requestId = requestId;
  }
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  query?: Record<string, string | undefined>;
  params?: Record<string, string | number>;
};

export class ApiClient {
  constructor(private readonly baseUrl: string) {}

  private async request<T>(operation: Parameters<typeof buildPath>[0], options: RequestOptions = {}): Promise<ApiResult<T>> {
    const url = new URL(buildPath(operation, options.params), this.baseUrl);
    for (const [key, value] of Object.entries(options.query ?? {})) {
      if (value) {
        url.searchParams.set(key, value);
      }
    }

    const response = await fetch(url, {
      method: options.method ?? "GET",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
      },
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    const requestId = response.headers.get("X-Request-ID") ?? undefined;
    if (!response.ok) {
      let message = response.statusText;
      try {
        const payload = (await response.json()) as { error?: string };
        message = payload.error ?? message;
      } catch {
        // ignore
      }
      throw new ApiError(message, response.status, requestId);
    }

    const data = (await response.json()) as T;
    return { data, requestId };
  }

  login(payload: { email: string; tenantId: string; displayName?: string; permissions?: string[] }) {
    return this.request<{ user: User }>("login", { method: "POST", body: payload });
  }

  logout() {
    return this.request<{ message: string }>("logout", { method: "POST" });
  }

  refreshSession() {
    return this.request<{ user: User }>("refreshSession", { method: "POST" });
  }

  getCurrentUser() {
    return this.request<User>("getCurrentUser");
  }

  listProviderConfigs() {
    return this.request<ApiList<ProviderConfig>>("listProviderConfigs");
  }

  createProviderConfig(payload: { provider: "gmail" | "outlook"; accountEmail?: string; scopes?: string[] }) {
    return this.request<ProviderConfig>("createProviderConfig", { method: "POST", body: payload });
  }

  startProviderOAuth(providerConfigId: string) {
    return this.request<{ authorizationUrl: string; state: string; providerConfig: ProviderConfig }>("startProviderOAuth", {
      method: "POST",
      params: { providerConfigId },
    });
  }

  completeProviderOAuth(providerConfigId: string, code = "demo-code") {
    return this.request<ProviderConfig>("completeProviderOAuth", {
      method: "POST",
      params: { providerConfigId },
      body: { code },
    });
  }

  refreshProviderOAuth(providerConfigId: string) {
    return this.request<ProviderConfig>("refreshProviderOAuth", {
      method: "POST",
      params: { providerConfigId },
    });
  }

  revokeProviderOAuth(providerConfigId: string) {
    return this.request<ProviderConfig>("revokeProviderOAuth", {
      method: "POST",
      params: { providerConfigId },
    });
  }

  listCollectionJobs() {
    return this.request<ApiList<CollectionJob>>("listCollectionJobs");
  }

  createCollectionJob(payload: { providers: Array<"gmail" | "outlook">; month: number; year: number }) {
    return this.request<CollectionJob>("createCollectionJob", { method: "POST", body: payload });
  }

  retryCollectionJob(collectionJobId: string) {
    return this.request<CollectionJob>("retryCollectionJob", {
      method: "POST",
      params: { collectionJobId },
    });
  }

  listReports() {
    return this.request<ApiList<Report>>("listReports");
  }

  createReport(payload: { inputDir: string; formats: ReportArtifact["format"][] }) {
    return this.request<Report>("createReport", { method: "POST", body: payload });
  }

  listSchedules() {
    return this.request<ApiList<Schedule>>("listSchedules");
  }

  createSchedule(payload: { name: string; timezone: string; cron: string; providers: Array<"gmail" | "outlook"> }) {
    return this.request<Schedule>("createSchedule", { method: "POST", body: payload });
  }

  pauseSchedule(scheduleId: string) {
    return this.request<Schedule>("pauseSchedule", {
      method: "POST",
      params: { scheduleId },
    });
  }

  resumeSchedule(scheduleId: string) {
    return this.request<Schedule>("resumeSchedule", {
      method: "POST",
      params: { scheduleId },
    });
  }

  listAuditEvents(filters: { entityType?: string; entityId?: string } = {}) {
    return this.request<ApiList<AuditEvent>>("listAuditEvents", { query: filters });
  }
}

export const apiClient = new ApiClient(import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8080");
