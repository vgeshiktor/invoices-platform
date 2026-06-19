package storage

import (
	"context"
	"errors"
	"os"
	"strings"
	"testing"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/vgeshiktor/invoices-platform/apps/api-go/internal/api"
)

func TestMigrateBootstrapsSchema(t *testing.T) {
	databaseURL := os.Getenv("DATABASE_URL")
	if databaseURL == "" {
		t.Skip("DATABASE_URL is required for postgres integration tests")
	}

	testDatabaseURL := createTestDatabase(t, databaseURL)
	ctx := context.Background()
	store, err := Open(ctx, testDatabaseURL)
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	defer store.Close()

	if err := store.Migrate(ctx); err != nil {
		t.Fatalf("migrate store: %v", err)
	}

	var count int
	if err := store.pool.QueryRow(ctx, `select count(*) from schema_migrations`).Scan(&count); err != nil {
		t.Fatalf("query schema_migrations: %v", err)
	}
	if count == 0 {
		t.Fatal("expected at least one applied migration")
	}
}

func TestPostgresStorePersistsTenantScopedResources(t *testing.T) {
	databaseURL := os.Getenv("DATABASE_URL")
	if databaseURL == "" {
		t.Skip("DATABASE_URL is required for postgres integration tests")
	}

	testDatabaseURL := createTestDatabase(t, databaseURL)
	ctx := context.Background()
	store, err := Open(ctx, testDatabaseURL)
	if err != nil {
		t.Fatalf("open store: %v", err)
	}
	defer store.Close()
	if err := store.Migrate(ctx); err != nil {
		t.Fatalf("migrate store: %v", err)
	}

	session := api.Session{
		ID:          "sess-1",
		UserID:      "user-1",
		Email:       "owner@example.com",
		DisplayName: "owner",
		TenantID:    "tenant-a",
		Permissions: []string{"reports:read"},
		CreatedAt:   nowRFC3339(),
		LastSeenAt:  nowRFC3339(),
	}
	if err := store.CreateSession(ctx, session); err != nil {
		t.Fatalf("create session: %v", err)
	}
	gotSession, err := store.GetSession(ctx, session.ID)
	if err != nil {
		t.Fatalf("get session: %v", err)
	}
	if gotSession.Email != session.Email {
		t.Fatalf("unexpected session email: %s", gotSession.Email)
	}
	gotSession.LastSeenAt = nowRFC3339()
	if err := store.UpdateSession(ctx, gotSession); err != nil {
		t.Fatalf("update session: %v", err)
	}

	providerA := api.ProviderConfig{
		ID:           "prov-1",
		TenantID:     "tenant-a",
		Provider:     "gmail",
		State:        "connected",
		Connected:    true,
		AccountEmail: "finance@example.com",
		Health:       "healthy",
		Scopes:       []string{"gmail.readonly"},
		CreatedAt:    nowRFC3339(),
		UpdatedAt:    nowRFC3339(),
	}
	providerB := api.ProviderConfig{
		ID:        "prov-2",
		TenantID:  "tenant-b",
		Provider:  "outlook",
		State:     "disconnected",
		Connected: false,
		Scopes:    []string{"mail.read"},
		CreatedAt: nowRFC3339(),
		UpdatedAt: nowRFC3339(),
	}
	if err := store.CreateProviderConfig(ctx, providerA); err != nil {
		t.Fatalf("create provider A: %v", err)
	}
	if err := store.CreateProviderConfig(ctx, providerB); err != nil {
		t.Fatalf("create provider B: %v", err)
	}
	providers, err := store.ListProviderConfigs(ctx, "tenant-a")
	if err != nil {
		t.Fatalf("list providers: %v", err)
	}
	if len(providers) != 1 || providers[0].ID != providerA.ID {
		t.Fatalf("unexpected tenant-scoped providers: %#v", providers)
	}

	job := api.CollectionJob{
		ID:              "job-1",
		TenantID:        "tenant-a",
		Status:          "queued",
		Providers:       []string{"gmail", "outlook"},
		Month:           6,
		Year:            2026,
		GraphClientID:   "graph-client",
		GraphAuthority:  "consumers",
		GraphTokenCache: ".cache/msal.bin",
		InteractiveAuth: true,
		RequestID:       "req-1",
		CreatedAt:       nowRFC3339(),
		UpdatedAt:       nowRFC3339(),
	}
	if err := store.CreateCollectionJob(ctx, job); err != nil {
		t.Fatalf("create collection job: %v", err)
	}
	job.Status = "running"
	job.StartedAt = nowRFC3339()
	job.UpdatedAt = nowRFC3339()
	if err := store.UpdateCollectionJob(ctx, job); err != nil {
		t.Fatalf("update collection job: %v", err)
	}
	gotJob, err := store.GetCollectionJob(ctx, "tenant-a", job.ID)
	if err != nil {
		t.Fatalf("get collection job: %v", err)
	}
	if gotJob.Status != "running" || gotJob.StartedAt == "" || gotJob.GraphClientID != "graph-client" || !gotJob.InteractiveAuth {
		t.Fatalf("unexpected collection job: %#v", gotJob)
	}

	report := api.Report{
		ID:        "report-1",
		TenantID:  "tenant-a",
		Status:    "queued",
		InputDir:  "invoices/invoices_06_2026",
		Formats:   []string{"json", "pdf"},
		Artifacts: []api.ReportArtifact{{Format: "json", Path: "reports/invoice_report.json"}},
		CreatedAt: nowRFC3339(),
		UpdatedAt: nowRFC3339(),
	}
	if err := store.CreateReport(ctx, report); err != nil {
		t.Fatalf("create report: %v", err)
	}
	report.Status = "ready"
	report.Totals = &api.ReportTotals{NetTotal: 100, VATTotal: 17, GrossTotal: 117}
	report.FinishedAt = nowRFC3339()
	report.UpdatedAt = nowRFC3339()
	if err := store.UpdateReport(ctx, report); err != nil {
		t.Fatalf("update report: %v", err)
	}
	gotReport, err := store.GetReport(ctx, "tenant-a", report.ID)
	if err != nil {
		t.Fatalf("get report: %v", err)
	}
	if gotReport.Totals == nil || gotReport.Totals.GrossTotal != 117 {
		t.Fatalf("unexpected report totals: %#v", gotReport.Totals)
	}

	schedule := api.Schedule{
		ID:        "sched-1",
		TenantID:  "tenant-a",
		Name:      "monthly",
		Timezone:  "UTC",
		Cron:      "0 8 * * *",
		Providers: []string{"gmail"},
		Status:    "active",
		CreatedAt: nowRFC3339(),
		UpdatedAt: nowRFC3339(),
	}
	if err := store.CreateSchedule(ctx, schedule); err != nil {
		t.Fatalf("create schedule: %v", err)
	}
	schedule.NextRunAt = nowRFC3339()
	schedule.UpdatedAt = nowRFC3339()
	if err := store.UpdateSchedule(ctx, schedule); err != nil {
		t.Fatalf("update schedule: %v", err)
	}
	gotSchedule, err := store.GetSchedule(ctx, "tenant-a", schedule.ID)
	if err != nil {
		t.Fatalf("get schedule: %v", err)
	}
	if gotSchedule.NextRunAt == "" {
		t.Fatalf("expected next run on schedule: %#v", gotSchedule)
	}

	event := api.AuditEvent{
		ID:         "audit-1",
		TenantID:   "tenant-a",
		Action:     "report.created",
		EntityType: "report",
		EntityID:   report.ID,
		RequestID:  "req-2",
		Message:    "Queued report generation",
		CreatedAt:  nowRFC3339(),
	}
	if err := store.CreateAuditEvent(ctx, event); err != nil {
		t.Fatalf("create audit event: %v", err)
	}
	events, err := store.ListAuditEvents(ctx, "tenant-a", "report", report.ID)
	if err != nil {
		t.Fatalf("list audit events: %v", err)
	}
	if len(events) != 1 || events[0].ID != event.ID {
		t.Fatalf("unexpected audit events: %#v", events)
	}

	if err := store.DeleteSession(ctx, session.ID); err != nil {
		t.Fatalf("delete session: %v", err)
	}
	if _, err := store.GetSession(ctx, session.ID); err == nil || !errors.Is(err, api.ErrNotFound) {
		t.Fatalf("expected deleted session to be missing, got %v", err)
	}
}

func createTestDatabase(t *testing.T, databaseURL string) string {
	t.Helper()

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	cfg, err := pgx.ParseConfig(databaseURL)
	if err != nil {
		t.Fatalf("parse DATABASE_URL: %v", err)
	}
	adminCfg := *cfg
	adminCfg.Database = "postgres"
	adminConn, err := pgx.ConnectConfig(ctx, &adminCfg)
	if err != nil {
		t.Fatalf("connect admin database: %v", err)
	}

	dbName := "invoices_api_test_" + strings.ReplaceAll(nowRFC3339(), ":", "_")
	if _, err := adminConn.Exec(ctx, `create database "`+dbName+`"`); err != nil {
		t.Fatalf("create test database: %v", err)
	}

	testCfg := *cfg
	testCfg.Database = dbName
	testURL := testCfg.ConnString()

	t.Cleanup(func() {
		dropCtx, dropCancel := context.WithTimeout(context.Background(), 30*time.Second)
		defer dropCancel()

		testConn, err := pgx.ConnectConfig(dropCtx, &testCfg)
		if err == nil {
			testConn.Close(dropCtx)
		}

		_, _ = adminConn.Exec(dropCtx, `
			select pg_terminate_backend(pid)
			from pg_stat_activity
			where datname = $1 and pid <> pg_backend_pid()
		`, dbName)
		_, err = adminConn.Exec(dropCtx, `drop database if exists "`+dbName+`"`)
		if err != nil {
			t.Fatalf("drop test database: %v", err)
		}
		adminConn.Close(dropCtx)
	})

	return testURL
}

func nowRFC3339() string {
	return time.Now().UTC().Format(time.RFC3339)
}
