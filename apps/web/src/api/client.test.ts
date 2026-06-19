import { ApiClient, ApiError } from "./client";

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  fetchMock.mockReset();
});

function ok(payload: unknown) {
  return new Response(JSON.stringify(payload), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
      "X-Request-ID": "req-123"
    }
  });
}

test("invokes the generated routes through the typed client surface", async () => {
  fetchMock.mockImplementation(async () =>
    ok({ user: { id: "u1", email: "a@b.com", displayName: "A", tenantId: "t1", permissions: [] } })
  );
  const client = new ApiClient("http://127.0.0.1:8080");

  await expect(client.login({ email: "a@b.com", tenantId: "t1" })).resolves.toMatchObject({ requestId: "req-123" });
  await expect(client.getCurrentUser()).resolves.toMatchObject({ requestId: "req-123" });
  await expect(client.logout()).resolves.toMatchObject({ requestId: "req-123" });
  await expect(client.refreshSession()).resolves.toMatchObject({ requestId: "req-123" });

  fetchMock.mockImplementation(async () => ok({ items: [] }));
  await client.listProviderConfigs();
  await client.listCollectionJobs();
  await client.listReports();
  await client.listSchedules();
  await client.listAuditEvents({ entityType: "report" });

  fetchMock.mockImplementation(async () =>
    ok({ id: "prov-1", tenantId: "t1", provider: "gmail", state: "connected", connected: true, scopes: [], createdAt: "now", updatedAt: "now" })
  );
  await client.createProviderConfig({ provider: "gmail" });
  await client.completeProviderOAuth("prov-1");
  await client.refreshProviderOAuth("prov-1");
  await client.revokeProviderOAuth("prov-1");

  fetchMock.mockImplementation(async () =>
    ok({ authorizationUrl: "https://example.invalid", state: "oauth", providerConfig: { id: "prov-1", tenantId: "t1", provider: "gmail", state: "disconnected", connected: false, scopes: [], createdAt: "now", updatedAt: "now" } })
  );
  await client.startProviderOAuth("prov-1");

  fetchMock.mockImplementation(async () =>
    ok({ id: "job-1", tenantId: "t1", status: "queued", providers: ["gmail"], month: 1, year: 2026, createdAt: "now", updatedAt: "now" })
  );
  await client.createCollectionJob({ providers: ["gmail"], month: 1, year: 2026 });
  await client.retryCollectionJob("job-1");

  fetchMock.mockImplementation(async () =>
    ok({ id: "report-1", tenantId: "t1", status: "queued", inputDir: "invoices", formats: ["json"], artifacts: [], createdAt: "now", updatedAt: "now" })
  );
  await client.createReport({ inputDir: "invoices", formats: ["json"] });

  fetchMock.mockImplementation(async () =>
    ok({ id: "schedule-1", tenantId: "t1", name: "Daily", timezone: "UTC", cron: "* * * * *", providers: ["gmail"], status: "active", createdAt: "now", updatedAt: "now" })
  );
  await client.createSchedule({ name: "Daily", timezone: "UTC", cron: "* * * * *", providers: ["gmail"] });
  await client.pauseSchedule("schedule-1");
  await client.resumeSchedule("schedule-1");
});

test("surfaces API failures with status and request id", async () => {
  fetchMock.mockResolvedValue(
    new Response(JSON.stringify({ error: "unauthorized" }), {
      status: 401,
      headers: {
        "Content-Type": "application/json",
        "X-Request-ID": "req-401"
      }
    })
  );

  const client = new ApiClient("http://127.0.0.1:8080");

  await expect(client.getCurrentUser()).rejects.toEqual(
    expect.objectContaining<ApiError>({
      name: "ApiError",
      message: "unauthorized",
      status: 401,
      requestId: "req-401"
    })
  );
});
