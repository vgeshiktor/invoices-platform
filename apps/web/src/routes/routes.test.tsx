import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AuditPage } from "./AuditPage";
import { CollectionsPage } from "./CollectionsPage";
import { ProvidersPage } from "./ProvidersPage";
import { ReportsPage } from "./ReportsPage";
import { SchedulesPage } from "./SchedulesPage";
import { apiClient } from "../api/client";

afterEach(() => {
  vi.restoreAllMocks();
});

test("providers page loads and creates a provider", async () => {
  const listSpy = vi.spyOn(apiClient, "listProviderConfigs").mockResolvedValue({
    data: {
      items: [
        {
          id: "prov-1",
          tenantId: "tenant-alpha",
          provider: "gmail",
          state: "disconnected",
          connected: false,
          accountEmail: "finance@example.com",
          scopes: [],
          createdAt: "now",
          updatedAt: "now"
        }
      ]
    },
    requestId: "req-list"
  });
  const createSpy = vi.spyOn(apiClient, "createProviderConfig").mockResolvedValue({
    data: {
      id: "prov-2",
      tenantId: "tenant-alpha",
      provider: "gmail",
      state: "disconnected",
      connected: false,
      scopes: [],
      createdAt: "now",
      updatedAt: "now"
    },
    requestId: "req-create"
  });
  const startSpy = vi.spyOn(apiClient, "startProviderOAuth").mockResolvedValue({
    data: {
      authorizationUrl: "https://example.invalid/oauth",
      state: "oauth-1",
      providerConfig: {
        id: "prov-1",
        tenantId: "tenant-alpha",
        provider: "gmail",
        state: "disconnected",
        connected: false,
        scopes: [],
        createdAt: "now",
        updatedAt: "now"
      }
    },
    requestId: "req-start"
  });
  const completeSpy = vi.spyOn(apiClient, "completeProviderOAuth").mockResolvedValue({
    data: {
      id: "prov-1",
      tenantId: "tenant-alpha",
      provider: "gmail",
      state: "connected",
      connected: true,
      scopes: [],
      createdAt: "now",
      updatedAt: "now"
    },
    requestId: "req-complete"
  });
  const refreshSpy = vi.spyOn(apiClient, "refreshProviderOAuth").mockResolvedValue({
    data: {
      id: "prov-1",
      tenantId: "tenant-alpha",
      provider: "gmail",
      state: "connected",
      connected: true,
      scopes: [],
      createdAt: "now",
      updatedAt: "now"
    },
    requestId: "req-refresh"
  });
  const revokeSpy = vi.spyOn(apiClient, "revokeProviderOAuth").mockResolvedValue({
    data: {
      id: "prov-1",
      tenantId: "tenant-alpha",
      provider: "gmail",
      state: "disconnected",
      connected: false,
      scopes: [],
      createdAt: "now",
      updatedAt: "now"
    },
    requestId: "req-revoke"
  });

  render(<ProvidersPage />);

  await waitFor(() => expect(screen.getByRole("heading", { name: /provider settings/i })).toBeInTheDocument());
  await userEvent.click(screen.getByRole("button", { name: /add gmail provider/i }));
  await waitFor(() => expect(createSpy).toHaveBeenCalled());
  await userEvent.click(screen.getAllByRole("button", { name: /begin oauth/i })[0]);
  await userEvent.click(screen.getAllByRole("button", { name: /^connect$/i })[0]);
  await userEvent.click(screen.getAllByRole("button", { name: /refresh/i })[0]);
  await userEvent.click(screen.getAllByRole("button", { name: /revoke/i })[0]);
  await waitFor(() => {
    expect(listSpy).toHaveBeenCalled();
    expect(startSpy).toHaveBeenCalled();
    expect(completeSpy).toHaveBeenCalled();
    expect(refreshSpy).toHaveBeenCalled();
    expect(revokeSpy).toHaveBeenCalled();
  });
});

test("collections page queues a collection run", async () => {
  const listSpy = vi.spyOn(apiClient, "listCollectionJobs").mockResolvedValue({
    data: {
      items: [
        {
          id: "job-1",
          tenantId: "tenant-alpha",
          status: "failed",
          providers: ["gmail", "outlook"],
          month: 1,
          year: 2026,
          startedAt: "2026-01-01T08:00:00Z",
          finishedAt: "2026-01-01T08:10:00Z",
          runSummaryPath: "/tmp/run_summary.json",
          invoicesDir: "/tmp/invoices_01_2026",
          error: "provider timeout",
          createdAt: "now",
          updatedAt: "now"
        }
      ]
    },
    requestId: "req-list"
  });
  const createSpy = vi.spyOn(apiClient, "createCollectionJob").mockResolvedValue({
    data: {
      id: "job-1",
      tenantId: "tenant-alpha",
      status: "queued",
      providers: ["gmail", "outlook"],
      month: 1,
      year: 2026,
      startedAt: "2026-01-01T08:00:00Z",
      createdAt: "now",
      updatedAt: "now"
    },
    requestId: "req-create"
  });
  const retrySpy = vi.spyOn(apiClient, "retryCollectionJob").mockResolvedValue({
    data: {
      id: "job-2",
      tenantId: "tenant-alpha",
      status: "queued",
      providers: ["gmail", "outlook"],
      month: 1,
      year: 2026,
      retryOf: "job-1",
      finishedAt: "2026-01-01T08:20:00Z",
      createdAt: "now",
      updatedAt: "now"
    },
    requestId: "req-retry"
  });
  const originalCreateObjectURL = URL.createObjectURL;
  const originalRevokeObjectURL = URL.revokeObjectURL;
  Object.defineProperty(URL, "createObjectURL", {
    configurable: true,
    writable: true,
    value: vi.fn(() => "blob://bundle")
  });
  Object.defineProperty(URL, "revokeObjectURL", {
    configurable: true,
    writable: true,
    value: vi.fn(() => undefined)
  });
  const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);

  render(<CollectionsPage />);

  await userEvent.click(screen.getByRole("button", { name: /export support bundle/i }));
  await userEvent.click(screen.getByRole("button", { name: /collect current month/i }));
  await waitFor(() => expect(createSpy).toHaveBeenCalled());
  await userEvent.click(screen.getByRole("button", { name: /retry failed run/i }));
  await waitFor(() => {
    expect(URL.createObjectURL).toHaveBeenCalled();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob://bundle");
    expect(clickSpy).toHaveBeenCalled();
    expect(retrySpy).toHaveBeenCalled();
    expect(listSpy).toHaveBeenCalled();
  });
  expect(screen.getByText(/finished with a persisted failure summary/i)).toBeInTheDocument();
  Object.defineProperty(URL, "createObjectURL", {
    configurable: true,
    writable: true,
    value: originalCreateObjectURL
  });
  Object.defineProperty(URL, "revokeObjectURL", {
    configurable: true,
    writable: true,
    value: originalRevokeObjectURL
  });
});

test("reports page queues a report", async () => {
  const listSpy = vi.spyOn(apiClient, "listReports").mockResolvedValue({
    data: {
      items: [
        {
          id: "report-1",
          tenantId: "tenant-alpha",
          status: "ready",
          inputDir: "invoices/invoices_01_2026",
          formats: ["json", "pdf"],
          artifacts: [
            { format: "json", path: "reports/invoice_report.json" },
            { format: "pdf", path: "reports/invoice_report.pdf" }
          ],
          totals: {
            netTotal: 100,
            vatTotal: 17,
            grossTotal: 117
          },
          startedAt: "2026-01-01T09:00:00Z",
          finishedAt: "2026-01-01T09:01:00Z",
          createdAt: "now",
          updatedAt: "now"
        }
      ]
    },
    requestId: "req-list"
  });
  const createSpy = vi.spyOn(apiClient, "createReport").mockResolvedValue({
    data: {
      id: "report-1",
      tenantId: "tenant-alpha",
      status: "queued",
      inputDir: "invoices",
      formats: ["json"],
      artifacts: [],
      startedAt: "2026-01-01T09:00:00Z",
      createdAt: "now",
      updatedAt: "now"
    },
    requestId: "req-report"
  });

  render(<ReportsPage />);

  await userEvent.click(screen.getByLabelText(/^csv$/i));
  await userEvent.click(screen.getByLabelText(/^summary_csv$/i));
  await userEvent.click(screen.getByRole("button", { name: /queue report/i }));
  await waitFor(() => {
    expect(createSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        formats: expect.arrayContaining(["json", "pdf", "csv", "summary_csv"])
      })
    );
    expect(listSpy).toHaveBeenCalled();
  });
  expect(screen.getByRole("link", { name: /json: reports\/invoice_report.json/i })).toBeInTheDocument();
  expect(screen.getByText("100.00")).toBeInTheDocument();
  expect(screen.getByText("17.00")).toBeInTheDocument();
  expect(screen.getByText("117.00")).toBeInTheDocument();
});

test("schedules page creates and pauses a schedule", async () => {
  vi.spyOn(apiClient, "listSchedules").mockResolvedValue({
    data: {
      items: [
        {
          id: "schedule-1",
          tenantId: "tenant-alpha",
          name: "Daily month collection",
          timezone: "Asia/Jerusalem",
          cron: "0 8 * * *",
          providers: ["gmail"],
          status: "active",
          createdAt: "now",
          updatedAt: "now"
        }
      ]
    },
    requestId: "req-schedules"
  });
  vi.spyOn(apiClient, "createSchedule").mockResolvedValue({
    data: {
      id: "schedule-2",
      tenantId: "tenant-alpha",
      name: "Nightly",
      timezone: "UTC",
      cron: "0 0 * * *",
      providers: ["outlook"],
      status: "active",
      createdAt: "now",
      updatedAt: "now"
    },
    requestId: "req-create"
  });
  vi.spyOn(apiClient, "pauseSchedule").mockResolvedValue({
    data: {
      id: "schedule-1",
      tenantId: "tenant-alpha",
      name: "Daily month collection",
      timezone: "Asia/Jerusalem",
      cron: "0 8 * * *",
      providers: ["gmail"],
      status: "paused",
      createdAt: "now",
      updatedAt: "now"
    },
    requestId: "req-pause"
  });

  render(<SchedulesPage />);

  await userEvent.click(screen.getByRole("button", { name: /add schedule/i }));
  await waitFor(() => expect(apiClient.createSchedule).toHaveBeenCalled());
  await userEvent.click(screen.getByRole("button", { name: /pause/i }));
  await waitFor(() => expect(apiClient.pauseSchedule).toHaveBeenCalled());
});

test("audit page renders request timeline entries", async () => {
  vi.spyOn(apiClient, "listAuditEvents").mockResolvedValue({
    data: {
      items: [
        {
          id: "audit-1",
          tenantId: "tenant-alpha",
          action: "report.created",
          entityType: "report",
          entityId: "report-1",
          requestId: "req-audit",
          message: "Queued report generation",
          createdAt: "now"
        }
      ]
    },
    requestId: "req-audit"
  });

  render(<AuditPage />);

  expect(await screen.findByText(/report.created/i)).toBeInTheDocument();
});
