create table if not exists sessions (
    id text primary key,
    user_id text not null,
    email text not null,
    display_name text not null,
    tenant_id text not null,
    permissions_json jsonb not null,
    created_at timestamptz not null,
    last_seen_at timestamptz not null
);

create table if not exists provider_configs (
    id text primary key,
    tenant_id text not null,
    provider text not null,
    state text not null,
    connected boolean not null default false,
    account_email text,
    health text,
    last_sync_at timestamptz,
    scopes_json jsonb not null,
    created_at timestamptz not null,
    updated_at timestamptz not null
);

create index if not exists provider_configs_tenant_updated_idx
    on provider_configs (tenant_id, updated_at desc);

create table if not exists collection_jobs (
    id text primary key,
    tenant_id text not null,
    status text not null,
    providers_json jsonb not null,
    month integer not null,
    year integer not null,
    graph_client_id text,
    graph_authority text,
    graph_token_cache_path text,
    interactive_auth boolean not null default false,
    request_id text,
    run_summary_path text,
    invoices_dir text,
    retry_of text,
    error_text text,
    started_at timestamptz,
    finished_at timestamptz,
    created_at timestamptz not null,
    updated_at timestamptz not null
);

create index if not exists collection_jobs_tenant_updated_idx
    on collection_jobs (tenant_id, updated_at desc);

create table if not exists reports (
    id text primary key,
    tenant_id text not null,
    status text not null,
    input_dir text not null,
    formats_json jsonb not null,
    artifacts_json jsonb not null,
    totals_json jsonb,
    error_text text,
    started_at timestamptz,
    finished_at timestamptz,
    created_at timestamptz not null,
    updated_at timestamptz not null
);

create index if not exists reports_tenant_updated_idx
    on reports (tenant_id, updated_at desc);

create table if not exists schedules (
    id text primary key,
    tenant_id text not null,
    name text not null,
    timezone text not null,
    cron text not null,
    providers_json jsonb not null,
    status text not null,
    next_run_at timestamptz,
    last_run_at timestamptz,
    last_run_status text,
    created_at timestamptz not null,
    updated_at timestamptz not null
);

create index if not exists schedules_tenant_updated_idx
    on schedules (tenant_id, updated_at desc);

create table if not exists audit_events (
    id text primary key,
    tenant_id text not null,
    action text not null,
    entity_type text not null,
    entity_id text not null,
    request_id text not null,
    message text,
    created_at timestamptz not null
);

create index if not exists audit_events_tenant_entity_created_idx
    on audit_events (tenant_id, entity_type, entity_id, created_at desc);
