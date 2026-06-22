package storage

import (
	"context"
	"database/sql"
	"encoding/json"
	"errors"
	"fmt"
	"time"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgconn"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/vgeshiktor/invoices-platform/apps/api-go/internal/api"
)

type PostgresStore struct {
	pool *pgxpool.Pool
}

func Open(ctx context.Context, databaseURL string) (*PostgresStore, error) {
	cfg, err := pgxpool.ParseConfig(databaseURL)
	if err != nil {
		return nil, fmt.Errorf("parse DATABASE_URL: %w", err)
	}
	pool, err := pgxpool.NewWithConfig(ctx, cfg)
	if err != nil {
		return nil, fmt.Errorf("open postgres pool: %w", err)
	}
	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return nil, fmt.Errorf("ping postgres: %w", err)
	}
	return &PostgresStore{pool: pool}, nil
}

func (s *PostgresStore) Close() {
	if s.pool != nil {
		s.pool.Close()
	}
}

func (s *PostgresStore) CreateSession(ctx context.Context, session api.Session) error {
	permissionsJSON, err := json.Marshal(session.Permissions)
	if err != nil {
		return fmt.Errorf("marshal session permissions: %w", err)
	}
	_, err = s.pool.Exec(ctx, `
		insert into sessions (
			id, user_id, email, display_name, tenant_id, permissions_json, created_at, last_seen_at
		) values ($1, $2, $3, $4, $5, $6::jsonb, $7, $8)
	`, session.ID, session.UserID, session.Email, session.DisplayName, session.TenantID, permissionsJSON, parseTime(session.CreatedAt), parseTime(session.LastSeenAt))
	return err
}

func (s *PostgresStore) GetSession(ctx context.Context, id string) (api.Session, error) {
	row := s.pool.QueryRow(ctx, `
		select id, user_id, email, display_name, tenant_id, permissions_json, created_at, last_seen_at
		from sessions where id = $1
	`, id)
	return scanSession(row)
}

func (s *PostgresStore) UpdateSession(ctx context.Context, session api.Session) error {
	permissionsJSON, err := json.Marshal(session.Permissions)
	if err != nil {
		return fmt.Errorf("marshal session permissions: %w", err)
	}
	tag, err := s.pool.Exec(ctx, `
		update sessions
		set user_id = $2,
			email = $3,
			display_name = $4,
			tenant_id = $5,
			permissions_json = $6::jsonb,
			created_at = $7,
			last_seen_at = $8
		where id = $1
	`, session.ID, session.UserID, session.Email, session.DisplayName, session.TenantID, permissionsJSON, parseTime(session.CreatedAt), parseTime(session.LastSeenAt))
	return rowsAffectedOrNotFound(tag, err)
}

func (s *PostgresStore) DeleteSession(ctx context.Context, id string) error {
	_, err := s.pool.Exec(ctx, `delete from sessions where id = $1`, id)
	return err
}

func (s *PostgresStore) ListProviderConfigs(ctx context.Context, tenantID string) ([]api.ProviderConfig, error) {
	rows, err := s.pool.Query(ctx, `
		select id, tenant_id, provider, state, connected, account_email, health, last_sync_at, scopes_json, created_at, updated_at
		from provider_configs
		where tenant_id = $1
		order by updated_at desc
	`, tenantID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return collectProviderConfigs(rows)
}

func (s *PostgresStore) GetProviderConfig(ctx context.Context, tenantID, id string) (api.ProviderConfig, error) {
	row := s.pool.QueryRow(ctx, `
		select id, tenant_id, provider, state, connected, account_email, health, last_sync_at, scopes_json, created_at, updated_at
		from provider_configs
		where tenant_id = $1 and id = $2
	`, tenantID, id)
	return scanProviderConfig(row)
}

func (s *PostgresStore) CreateProviderConfig(ctx context.Context, item api.ProviderConfig) error {
	scopesJSON, err := json.Marshal(item.Scopes)
	if err != nil {
		return fmt.Errorf("marshal provider scopes: %w", err)
	}
	_, err = s.pool.Exec(ctx, `
		insert into provider_configs (
			id, tenant_id, provider, state, connected, account_email, health, last_sync_at, scopes_json, created_at, updated_at
		) values ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10, $11)
	`, item.ID, item.TenantID, item.Provider, item.State, item.Connected, nullString(item.AccountEmail), nullString(item.Health), nullTime(item.LastSyncAt), scopesJSON, parseTime(item.CreatedAt), parseTime(item.UpdatedAt))
	return err
}

func (s *PostgresStore) UpdateProviderConfig(ctx context.Context, item api.ProviderConfig) error {
	scopesJSON, err := json.Marshal(item.Scopes)
	if err != nil {
		return fmt.Errorf("marshal provider scopes: %w", err)
	}
	tag, err := s.pool.Exec(ctx, `
		update provider_configs
		set provider = $3,
			state = $4,
			connected = $5,
			account_email = $6,
			health = $7,
			last_sync_at = $8,
			scopes_json = $9::jsonb,
			created_at = $10,
			updated_at = $11
		where id = $1 and tenant_id = $2
	`, item.ID, item.TenantID, item.Provider, item.State, item.Connected, nullString(item.AccountEmail), nullString(item.Health), nullTime(item.LastSyncAt), scopesJSON, parseTime(item.CreatedAt), parseTime(item.UpdatedAt))
	return rowsAffectedOrNotFound(tag, err)
}

func (s *PostgresStore) ListCollectionJobs(ctx context.Context, tenantID string) ([]api.CollectionJob, error) {
	rows, err := s.pool.Query(ctx, `
		select id, tenant_id, status, providers_json, month, year, graph_client_id, graph_authority, graph_token_cache_path, interactive_auth,
		       request_id, run_summary_path, invoices_dir, retry_of, error_text,
		       started_at, finished_at, created_at, updated_at
		from collection_jobs
		where tenant_id = $1
		order by updated_at desc
	`, tenantID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return collectCollectionJobs(rows)
}

func (s *PostgresStore) GetCollectionJob(ctx context.Context, tenantID, id string) (api.CollectionJob, error) {
	row := s.pool.QueryRow(ctx, `
		select id, tenant_id, status, providers_json, month, year, graph_client_id, graph_authority, graph_token_cache_path, interactive_auth,
		       request_id, run_summary_path, invoices_dir, retry_of, error_text,
		       started_at, finished_at, created_at, updated_at
		from collection_jobs
		where tenant_id = $1 and id = $2
	`, tenantID, id)
	return scanCollectionJob(row)
}

func (s *PostgresStore) CreateCollectionJob(ctx context.Context, item api.CollectionJob) error {
	providersJSON, err := json.Marshal(item.Providers)
	if err != nil {
		return fmt.Errorf("marshal collection providers: %w", err)
	}
	_, err = s.pool.Exec(ctx, `
		insert into collection_jobs (
			id, tenant_id, status, providers_json, month, year, graph_client_id, graph_authority, graph_token_cache_path, interactive_auth,
			request_id, run_summary_path, invoices_dir, retry_of, error_text, started_at, finished_at, created_at, updated_at
		) values ($1, $2, $3, $4::jsonb, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)
	`, item.ID, item.TenantID, item.Status, providersJSON, item.Month, item.Year, nullString(item.GraphClientID), nullString(item.GraphAuthority), nullString(item.GraphTokenCache), item.InteractiveAuth, nullString(item.RequestID), nullString(item.RunSummaryPath), nullString(item.InvoicesDir), nullString(item.RetryOf), nullString(item.Error), nullTime(item.StartedAt), nullTime(item.FinishedAt), parseTime(item.CreatedAt), parseTime(item.UpdatedAt))
	return err
}

func (s *PostgresStore) UpdateCollectionJob(ctx context.Context, item api.CollectionJob) error {
	providersJSON, err := json.Marshal(item.Providers)
	if err != nil {
		return fmt.Errorf("marshal collection providers: %w", err)
	}
	tag, err := s.pool.Exec(ctx, `
		update collection_jobs
		set status = $3,
			providers_json = $4::jsonb,
			month = $5,
			year = $6,
			graph_client_id = $7,
			graph_authority = $8,
			graph_token_cache_path = $9,
			interactive_auth = $10,
			request_id = $11,
			run_summary_path = $12,
			invoices_dir = $13,
			retry_of = $14,
			error_text = $15,
			started_at = $16,
			finished_at = $17,
			created_at = $18,
			updated_at = $19
		where id = $1 and tenant_id = $2
	`, item.ID, item.TenantID, item.Status, providersJSON, item.Month, item.Year, nullString(item.GraphClientID), nullString(item.GraphAuthority), nullString(item.GraphTokenCache), item.InteractiveAuth, nullString(item.RequestID), nullString(item.RunSummaryPath), nullString(item.InvoicesDir), nullString(item.RetryOf), nullString(item.Error), nullTime(item.StartedAt), nullTime(item.FinishedAt), parseTime(item.CreatedAt), parseTime(item.UpdatedAt))
	return rowsAffectedOrNotFound(tag, err)
}

func (s *PostgresStore) ListReports(ctx context.Context, tenantID string) ([]api.Report, error) {
	rows, err := s.pool.Query(ctx, `
		select id, tenant_id, status, input_dir, formats_json, artifacts_json, totals_json, error_text,
		       started_at, finished_at, created_at, updated_at
		from reports
		where tenant_id = $1
		order by updated_at desc
	`, tenantID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return collectReports(rows)
}

func (s *PostgresStore) GetReport(ctx context.Context, tenantID, id string) (api.Report, error) {
	row := s.pool.QueryRow(ctx, `
		select id, tenant_id, status, input_dir, formats_json, artifacts_json, totals_json, error_text,
		       started_at, finished_at, created_at, updated_at
		from reports
		where tenant_id = $1 and id = $2
	`, tenantID, id)
	return scanReport(row)
}

func (s *PostgresStore) CreateReport(ctx context.Context, item api.Report) error {
	formatsJSON, err := json.Marshal(item.Formats)
	if err != nil {
		return fmt.Errorf("marshal report formats: %w", err)
	}
	artifactsJSON, err := json.Marshal(item.Artifacts)
	if err != nil {
		return fmt.Errorf("marshal report artifacts: %w", err)
	}
	totalsJSON, err := marshalNullable(item.Totals)
	if err != nil {
		return fmt.Errorf("marshal report totals: %w", err)
	}
	_, err = s.pool.Exec(ctx, `
		insert into reports (
			id, tenant_id, status, input_dir, formats_json, artifacts_json, totals_json, error_text,
			started_at, finished_at, created_at, updated_at
		) values ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7::jsonb, $8, $9, $10, $11, $12)
	`, item.ID, item.TenantID, item.Status, item.InputDir, formatsJSON, artifactsJSON, totalsJSON, nullString(item.Error), nullTime(item.StartedAt), nullTime(item.FinishedAt), parseTime(item.CreatedAt), parseTime(item.UpdatedAt))
	return err
}

func (s *PostgresStore) UpdateReport(ctx context.Context, item api.Report) error {
	formatsJSON, err := json.Marshal(item.Formats)
	if err != nil {
		return fmt.Errorf("marshal report formats: %w", err)
	}
	artifactsJSON, err := json.Marshal(item.Artifacts)
	if err != nil {
		return fmt.Errorf("marshal report artifacts: %w", err)
	}
	totalsJSON, err := marshalNullable(item.Totals)
	if err != nil {
		return fmt.Errorf("marshal report totals: %w", err)
	}
	tag, err := s.pool.Exec(ctx, `
		update reports
		set status = $3,
			input_dir = $4,
			formats_json = $5::jsonb,
			artifacts_json = $6::jsonb,
			totals_json = $7::jsonb,
			error_text = $8,
			started_at = $9,
			finished_at = $10,
			created_at = $11,
			updated_at = $12
		where id = $1 and tenant_id = $2
	`, item.ID, item.TenantID, item.Status, item.InputDir, formatsJSON, artifactsJSON, totalsJSON, nullString(item.Error), nullTime(item.StartedAt), nullTime(item.FinishedAt), parseTime(item.CreatedAt), parseTime(item.UpdatedAt))
	return rowsAffectedOrNotFound(tag, err)
}

func (s *PostgresStore) ListSchedules(ctx context.Context, tenantID string) ([]api.Schedule, error) {
	rows, err := s.pool.Query(ctx, `
		select id, tenant_id, name, timezone, cron, providers_json, status, next_run_at, last_run_at, last_run_status, created_at, updated_at
		from schedules
		where tenant_id = $1
		order by updated_at desc
	`, tenantID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return collectSchedules(rows)
}

func (s *PostgresStore) GetSchedule(ctx context.Context, tenantID, id string) (api.Schedule, error) {
	row := s.pool.QueryRow(ctx, `
		select id, tenant_id, name, timezone, cron, providers_json, status, next_run_at, last_run_at, last_run_status, created_at, updated_at
		from schedules
		where tenant_id = $1 and id = $2
	`, tenantID, id)
	return scanSchedule(row)
}

func (s *PostgresStore) CreateSchedule(ctx context.Context, item api.Schedule) error {
	providersJSON, err := json.Marshal(item.Providers)
	if err != nil {
		return fmt.Errorf("marshal schedule providers: %w", err)
	}
	_, err = s.pool.Exec(ctx, `
		insert into schedules (
			id, tenant_id, name, timezone, cron, providers_json, status, next_run_at, last_run_at, last_run_status, created_at, updated_at
		) values ($1, $2, $3, $4, $5, $6::jsonb, $7, $8, $9, $10, $11, $12)
	`, item.ID, item.TenantID, item.Name, item.Timezone, item.Cron, providersJSON, item.Status, nullTime(item.NextRunAt), nullTime(item.LastRunAt), nullString(item.LastRunStatus), parseTime(item.CreatedAt), parseTime(item.UpdatedAt))
	return err
}

func (s *PostgresStore) UpdateSchedule(ctx context.Context, item api.Schedule) error {
	providersJSON, err := json.Marshal(item.Providers)
	if err != nil {
		return fmt.Errorf("marshal schedule providers: %w", err)
	}
	tag, err := s.pool.Exec(ctx, `
		update schedules
		set name = $3,
			timezone = $4,
			cron = $5,
			providers_json = $6::jsonb,
			status = $7,
			next_run_at = $8,
			last_run_at = $9,
			last_run_status = $10,
			created_at = $11,
			updated_at = $12
		where id = $1 and tenant_id = $2
	`, item.ID, item.TenantID, item.Name, item.Timezone, item.Cron, providersJSON, item.Status, nullTime(item.NextRunAt), nullTime(item.LastRunAt), nullString(item.LastRunStatus), parseTime(item.CreatedAt), parseTime(item.UpdatedAt))
	return rowsAffectedOrNotFound(tag, err)
}

func (s *PostgresStore) ListAuditEvents(ctx context.Context, tenantID, entityType, entityID string) ([]api.AuditEvent, error) {
	rows, err := s.pool.Query(ctx, `
		select id, tenant_id, action, entity_type, entity_id, request_id, message, created_at
		from audit_events
		where tenant_id = $1
		  and ($2 = '' or entity_type = $2)
		  and ($3 = '' or entity_id = $3)
		order by created_at desc
	`, tenantID, entityType, entityID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return collectAuditEvents(rows)
}

func (s *PostgresStore) CreateAuditEvent(ctx context.Context, item api.AuditEvent) error {
	_, err := s.pool.Exec(ctx, `
		insert into audit_events (
			id, tenant_id, action, entity_type, entity_id, request_id, message, created_at
		) values ($1, $2, $3, $4, $5, $6, $7, $8)
	`, item.ID, item.TenantID, item.Action, item.EntityType, item.EntityID, item.RequestID, nullString(item.Message), parseTime(item.CreatedAt))
	return err
}

type sessionScanner interface {
	Scan(dest ...any) error
}

func scanSession(row sessionScanner) (api.Session, error) {
	var item api.Session
	var permissionsJSON []byte
	var createdAt time.Time
	var lastSeenAt time.Time
	err := row.Scan(&item.ID, &item.UserID, &item.Email, &item.DisplayName, &item.TenantID, &permissionsJSON, &createdAt, &lastSeenAt)
	if err != nil {
		return api.Session{}, mapScanError(err)
	}
	if err := json.Unmarshal(permissionsJSON, &item.Permissions); err != nil {
		return api.Session{}, fmt.Errorf("unmarshal session permissions: %w", err)
	}
	item.CreatedAt = createdAt.UTC().Format(time.RFC3339)
	item.LastSeenAt = lastSeenAt.UTC().Format(time.RFC3339)
	return item, nil
}

type providerConfigScanner interface {
	Scan(dest ...any) error
}

func scanProviderConfig(row providerConfigScanner) (api.ProviderConfig, error) {
	var item api.ProviderConfig
	var scopesJSON []byte
	var accountEmail sql.NullString
	var health sql.NullString
	var lastSyncAt sql.NullTime
	var createdAt time.Time
	var updatedAt time.Time
	err := row.Scan(&item.ID, &item.TenantID, &item.Provider, &item.State, &item.Connected, &accountEmail, &health, &lastSyncAt, &scopesJSON, &createdAt, &updatedAt)
	if err != nil {
		return api.ProviderConfig{}, mapScanError(err)
	}
	if err := json.Unmarshal(scopesJSON, &item.Scopes); err != nil {
		return api.ProviderConfig{}, fmt.Errorf("unmarshal provider scopes: %w", err)
	}
	item.AccountEmail = accountEmail.String
	item.Health = health.String
	item.LastSyncAt = nullableTimeString(lastSyncAt)
	item.CreatedAt = createdAt.UTC().Format(time.RFC3339)
	item.UpdatedAt = updatedAt.UTC().Format(time.RFC3339)
	return item, nil
}

func collectProviderConfigs(rows pgx.Rows) ([]api.ProviderConfig, error) {
	items := []api.ProviderConfig{}
	for rows.Next() {
		item, err := scanProviderConfig(rows)
		if err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, rows.Err()
}

type collectionJobScanner interface {
	Scan(dest ...any) error
}

func scanCollectionJob(row collectionJobScanner) (api.CollectionJob, error) {
	var item api.CollectionJob
	var providersJSON []byte
	var graphClientID sql.NullString
	var graphAuthority sql.NullString
	var graphTokenCache sql.NullString
	var interactiveAuth bool
	var requestID sql.NullString
	var runSummaryPath sql.NullString
	var invoicesDir sql.NullString
	var retryOf sql.NullString
	var errorText sql.NullString
	var startedAt sql.NullTime
	var finishedAt sql.NullTime
	var createdAt time.Time
	var updatedAt time.Time
	err := row.Scan(&item.ID, &item.TenantID, &item.Status, &providersJSON, &item.Month, &item.Year, &graphClientID, &graphAuthority, &graphTokenCache, &interactiveAuth, &requestID, &runSummaryPath, &invoicesDir, &retryOf, &errorText, &startedAt, &finishedAt, &createdAt, &updatedAt)
	if err != nil {
		return api.CollectionJob{}, mapScanError(err)
	}
	if err := json.Unmarshal(providersJSON, &item.Providers); err != nil {
		return api.CollectionJob{}, fmt.Errorf("unmarshal collection providers: %w", err)
	}
	item.RequestID = requestID.String
	item.RunSummaryPath = runSummaryPath.String
	item.InvoicesDir = invoicesDir.String
	item.RetryOf = retryOf.String
	item.Error = errorText.String
	item.GraphClientID = graphClientID.String
	item.GraphAuthority = graphAuthority.String
	item.GraphTokenCache = graphTokenCache.String
	item.InteractiveAuth = interactiveAuth
	item.StartedAt = nullableTimeString(startedAt)
	item.FinishedAt = nullableTimeString(finishedAt)
	item.CreatedAt = createdAt.UTC().Format(time.RFC3339)
	item.UpdatedAt = updatedAt.UTC().Format(time.RFC3339)
	return item, nil
}

func collectCollectionJobs(rows pgx.Rows) ([]api.CollectionJob, error) {
	items := []api.CollectionJob{}
	for rows.Next() {
		item, err := scanCollectionJob(rows)
		if err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, rows.Err()
}

type reportScanner interface {
	Scan(dest ...any) error
}

func scanReport(row reportScanner) (api.Report, error) {
	var item api.Report
	var formatsJSON []byte
	var artifactsJSON []byte
	var totalsJSON []byte
	var errorText sql.NullString
	var startedAt sql.NullTime
	var finishedAt sql.NullTime
	var createdAt time.Time
	var updatedAt time.Time
	err := row.Scan(&item.ID, &item.TenantID, &item.Status, &item.InputDir, &formatsJSON, &artifactsJSON, &totalsJSON, &errorText, &startedAt, &finishedAt, &createdAt, &updatedAt)
	if err != nil {
		return api.Report{}, mapScanError(err)
	}
	if err := json.Unmarshal(formatsJSON, &item.Formats); err != nil {
		return api.Report{}, fmt.Errorf("unmarshal report formats: %w", err)
	}
	if err := json.Unmarshal(artifactsJSON, &item.Artifacts); err != nil {
		return api.Report{}, fmt.Errorf("unmarshal report artifacts: %w", err)
	}
	if len(totalsJSON) > 0 && string(totalsJSON) != "null" {
		item.Totals = &api.ReportTotals{}
		if err := json.Unmarshal(totalsJSON, item.Totals); err != nil {
			return api.Report{}, fmt.Errorf("unmarshal report totals: %w", err)
		}
	}
	item.Error = errorText.String
	item.StartedAt = nullableTimeString(startedAt)
	item.FinishedAt = nullableTimeString(finishedAt)
	item.CreatedAt = createdAt.UTC().Format(time.RFC3339)
	item.UpdatedAt = updatedAt.UTC().Format(time.RFC3339)
	return item, nil
}

func collectReports(rows pgx.Rows) ([]api.Report, error) {
	items := []api.Report{}
	for rows.Next() {
		item, err := scanReport(rows)
		if err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, rows.Err()
}

type scheduleScanner interface {
	Scan(dest ...any) error
}

func scanSchedule(row scheduleScanner) (api.Schedule, error) {
	var item api.Schedule
	var providersJSON []byte
	var nextRunAt sql.NullTime
	var lastRunAt sql.NullTime
	var lastRunStatus sql.NullString
	var createdAt time.Time
	var updatedAt time.Time
	err := row.Scan(&item.ID, &item.TenantID, &item.Name, &item.Timezone, &item.Cron, &providersJSON, &item.Status, &nextRunAt, &lastRunAt, &lastRunStatus, &createdAt, &updatedAt)
	if err != nil {
		return api.Schedule{}, mapScanError(err)
	}
	if err := json.Unmarshal(providersJSON, &item.Providers); err != nil {
		return api.Schedule{}, fmt.Errorf("unmarshal schedule providers: %w", err)
	}
	item.NextRunAt = nullableTimeString(nextRunAt)
	item.LastRunAt = nullableTimeString(lastRunAt)
	item.LastRunStatus = lastRunStatus.String
	item.CreatedAt = createdAt.UTC().Format(time.RFC3339)
	item.UpdatedAt = updatedAt.UTC().Format(time.RFC3339)
	return item, nil
}

func collectSchedules(rows pgx.Rows) ([]api.Schedule, error) {
	items := []api.Schedule{}
	for rows.Next() {
		item, err := scanSchedule(rows)
		if err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, rows.Err()
}

type auditEventScanner interface {
	Scan(dest ...any) error
}

func scanAuditEvent(row auditEventScanner) (api.AuditEvent, error) {
	var item api.AuditEvent
	var message sql.NullString
	var createdAt time.Time
	err := row.Scan(&item.ID, &item.TenantID, &item.Action, &item.EntityType, &item.EntityID, &item.RequestID, &message, &createdAt)
	if err != nil {
		return api.AuditEvent{}, mapScanError(err)
	}
	item.Message = message.String
	item.CreatedAt = createdAt.UTC().Format(time.RFC3339)
	return item, nil
}

func collectAuditEvents(rows pgx.Rows) ([]api.AuditEvent, error) {
	items := []api.AuditEvent{}
	for rows.Next() {
		item, err := scanAuditEvent(rows)
		if err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, rows.Err()
}

func rowsAffectedOrNotFound(tag pgconn.CommandTag, err error) error {
	if err != nil {
		return err
	}
	if tag.RowsAffected() == 0 {
		return api.ErrNotFound
	}
	return nil
}

func parseTime(value string) time.Time {
	ts, err := time.Parse(time.RFC3339, value)
	if err != nil {
		return time.Time{}
	}
	return ts.UTC()
}

func nullTime(value string) any {
	if value == "" {
		return nil
	}
	return parseTime(value)
}

func nullString(value string) any {
	if value == "" {
		return nil
	}
	return value
}

func nullableTimeString(value sql.NullTime) string {
	if !value.Valid {
		return ""
	}
	return value.Time.UTC().Format(time.RFC3339)
}

func marshalNullable(value any) ([]byte, error) {
	if value == nil {
		return []byte("null"), nil
	}
	return json.Marshal(value)
}

func mapScanError(err error) error {
	if errors.Is(err, pgx.ErrNoRows) {
		return api.ErrNotFound
	}
	return err
}
