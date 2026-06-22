package api

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"net/http"
	"strings"
	"sync/atomic"
	"time"
)

const sessionCookieName = "invplatform_session"

type Server struct {
	idCounter        uint64
	store            Store
	collectionRunner CollectionRunner
}

type Session struct {
	ID          string   `json:"id"`
	UserID      string   `json:"userId"`
	Email       string   `json:"email"`
	DisplayName string   `json:"displayName"`
	TenantID    string   `json:"tenantId"`
	Permissions []string `json:"permissions"`
	CreatedAt   string   `json:"createdAt"`
	LastSeenAt  string   `json:"lastSeenAt"`
}

type User struct {
	ID          string   `json:"id"`
	Email       string   `json:"email"`
	DisplayName string   `json:"displayName"`
	TenantID    string   `json:"tenantId"`
	Permissions []string `json:"permissions"`
}

type LoginRequest struct {
	Email       string   `json:"email"`
	DisplayName string   `json:"displayName"`
	TenantID    string   `json:"tenantId"`
	Permissions []string `json:"permissions"`
}

type AuthResponse struct {
	User User `json:"user"`
}

type MessageResponse struct {
	Message string `json:"message"`
}

type ErrorResponse struct {
	Error string `json:"error"`
}

type HealthResponse struct {
	Status string `json:"status"`
}

type ProviderConfig struct {
	ID           string   `json:"id"`
	TenantID     string   `json:"tenantId"`
	Provider     string   `json:"provider"`
	State        string   `json:"state"`
	Connected    bool     `json:"connected"`
	AccountEmail string   `json:"accountEmail,omitempty"`
	Health       string   `json:"health,omitempty"`
	LastSyncAt   string   `json:"lastSyncAt,omitempty"`
	Scopes       []string `json:"scopes"`
	CreatedAt    string   `json:"createdAt"`
	UpdatedAt    string   `json:"updatedAt"`
}

type ProviderConfigCreateRequest struct {
	Provider     string   `json:"provider"`
	AccountEmail string   `json:"accountEmail"`
	Scopes       []string `json:"scopes"`
}

type ProviderConfigUpdateRequest struct {
	AccountEmail string `json:"accountEmail"`
	Health       string `json:"health"`
	State        string `json:"state"`
	LastSyncAt   string `json:"lastSyncAt"`
}

type ProviderConfigList struct {
	Items []ProviderConfig `json:"items"`
}

type OAuthFlowResponse struct {
	AuthorizationURL string         `json:"authorizationUrl"`
	State            string         `json:"state"`
	ProviderConfig   ProviderConfig `json:"providerConfig"`
}

type OAuthCallbackRequest struct {
	Code  string `json:"code"`
	State string `json:"state"`
}

type CollectionJob struct {
	ID              string   `json:"id"`
	TenantID        string   `json:"tenantId"`
	Status          string   `json:"status"`
	Providers       []string `json:"providers"`
	Month           int      `json:"month"`
	Year            int      `json:"year"`
	GraphClientID   string   `json:"-"`
	GraphAuthority  string   `json:"-"`
	GraphTokenCache string   `json:"-"`
	InteractiveAuth bool     `json:"-"`
	RequestID       string   `json:"requestId,omitempty"`
	RunSummaryPath  string   `json:"runSummaryPath,omitempty"`
	InvoicesDir     string   `json:"invoicesDir,omitempty"`
	RetryOf         string   `json:"retryOf,omitempty"`
	Error           string   `json:"error,omitempty"`
	StartedAt       string   `json:"startedAt,omitempty"`
	FinishedAt      string   `json:"finishedAt,omitempty"`
	CreatedAt       string   `json:"createdAt"`
	UpdatedAt       string   `json:"updatedAt"`
}

type CollectionJobCreateRequest struct {
	Providers       []string `json:"providers"`
	Month           int      `json:"month"`
	Year            int      `json:"year"`
	GraphClientID   string   `json:"graphClientId"`
	GraphAuthority  string   `json:"graphAuthority"`
	GraphTokenCache string   `json:"graphTokenCachePath"`
	InteractiveAuth bool     `json:"interactiveAuth"`
}

type CollectionJobList struct {
	Items []CollectionJob `json:"items"`
}

type Report struct {
	ID         string           `json:"id"`
	TenantID   string           `json:"tenantId"`
	Status     string           `json:"status"`
	InputDir   string           `json:"inputDir"`
	Formats    []string         `json:"formats"`
	Artifacts  []ReportArtifact `json:"artifacts"`
	Totals     *ReportTotals    `json:"totals,omitempty"`
	Error      string           `json:"error,omitempty"`
	StartedAt  string           `json:"startedAt,omitempty"`
	FinishedAt string           `json:"finishedAt,omitempty"`
	CreatedAt  string           `json:"createdAt"`
	UpdatedAt  string           `json:"updatedAt"`
}

type ReportArtifact struct {
	Format string `json:"format"`
	Path   string `json:"path"`
}

type ReportTotals struct {
	NetTotal   float64 `json:"netTotal"`
	VATTotal   float64 `json:"vatTotal"`
	GrossTotal float64 `json:"grossTotal"`
}

type ReportCreateRequest struct {
	InputDir         string   `json:"inputDir"`
	Formats          []string `json:"formats"`
	JSONOutput       string   `json:"jsonOutput"`
	CSVOutput        string   `json:"csvOutput"`
	SummaryCSVOutput string   `json:"summaryCsvOutput"`
	PDFOutput        string   `json:"pdfOutput"`
}

type ReportList struct {
	Items []Report `json:"items"`
}

type Schedule struct {
	ID            string   `json:"id"`
	TenantID      string   `json:"tenantId"`
	Name          string   `json:"name"`
	Timezone      string   `json:"timezone"`
	Cron          string   `json:"cron"`
	Providers     []string `json:"providers"`
	Status        string   `json:"status"`
	NextRunAt     string   `json:"nextRunAt,omitempty"`
	LastRunAt     string   `json:"lastRunAt,omitempty"`
	LastRunStatus string   `json:"lastRunStatus,omitempty"`
	CreatedAt     string   `json:"createdAt"`
	UpdatedAt     string   `json:"updatedAt"`
}

type ScheduleCreateRequest struct {
	Name      string   `json:"name"`
	Timezone  string   `json:"timezone"`
	Cron      string   `json:"cron"`
	Providers []string `json:"providers"`
}

type ScheduleUpdateRequest struct {
	Name      string   `json:"name"`
	Timezone  string   `json:"timezone"`
	Cron      string   `json:"cron"`
	Providers []string `json:"providers"`
	NextRunAt string   `json:"nextRunAt"`
}

type ScheduleList struct {
	Items []Schedule `json:"items"`
}

type AuditEvent struct {
	ID         string `json:"id"`
	TenantID   string `json:"tenantId"`
	Action     string `json:"action"`
	EntityType string `json:"entityType"`
	EntityID   string `json:"entityId"`
	RequestID  string `json:"requestId"`
	Message    string `json:"message,omitempty"`
	CreatedAt  string `json:"createdAt"`
}

type AuditEventList struct {
	Items []AuditEvent `json:"items"`
}

type routeContext struct {
	RequestID string
	Session   *Session
}

type contextKey string

var routeContextKey = contextKey("route-context")

func NewServer(opts ...Option) *Server {
	server := &Server{
		store:            NewMemoryStore(),
		collectionRunner: noopCollectionRunner{},
	}
	for _, opt := range opts {
		if opt != nil {
			opt(server)
		}
	}
	return server
}

func (s *Server) Handler() http.Handler {
	return s.withMiddleware(http.HandlerFunc(s.route))
}

func (s *Server) withMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestID := r.Header.Get("X-Request-ID")
		if requestID == "" {
			requestID = s.newID("req")
		}
		w.Header().Set("X-Request-ID", requestID)
		s.applyCORS(w, r)
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, withRouteContext(r, routeContext{RequestID: requestID}))
	})
}

func (s *Server) applyCORS(w http.ResponseWriter, r *http.Request) {
	origin := r.Header.Get("Origin")
	allowed := map[string]bool{
		"http://localhost:5173": true,
		"http://127.0.0.1:5173": true,
		"http://localhost:4173": true,
		"http://127.0.0.1:4173": true,
	}
	if allowed[origin] {
		w.Header().Set("Access-Control-Allow-Origin", origin)
		w.Header().Set("Access-Control-Allow-Credentials", "true")
		w.Header().Set("Vary", "Origin")
	}
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type, X-Request-ID")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
}

func (s *Server) route(w http.ResponseWriter, r *http.Request) {
	switch {
	case r.URL.Path == "/healthz" && r.Method == http.MethodGet:
		writeJSON(w, http.StatusOK, HealthResponse{Status: "ok"})
	case r.URL.Path == "/auth/login" && r.Method == http.MethodPost:
		s.handleLogin(w, r)
	case r.URL.Path == "/auth/logout" && r.Method == http.MethodPost:
		s.requireSession(w, r, s.handleLogout)
	case r.URL.Path == "/auth/refresh" && r.Method == http.MethodPost:
		s.requireSession(w, r, s.handleRefresh)
	case r.URL.Path == "/v1/me" && r.Method == http.MethodGet:
		s.requireSession(w, r, s.handleMe)
	case r.URL.Path == "/v1/provider-configs":
		s.requireSession(w, r, s.handleProviderConfigs)
	case strings.HasPrefix(r.URL.Path, "/v1/provider-configs/"):
		s.requireSession(w, r, s.handleProviderConfigDetail)
	case r.URL.Path == "/v1/collection-jobs":
		s.requireSession(w, r, s.handleCollectionJobs)
	case strings.HasPrefix(r.URL.Path, "/v1/collection-jobs/"):
		s.requireSession(w, r, s.handleCollectionJobDetail)
	case r.URL.Path == "/v1/reports":
		s.requireSession(w, r, s.handleReports)
	case strings.HasPrefix(r.URL.Path, "/v1/reports/"):
		s.requireSession(w, r, s.handleReportDetail)
	case r.URL.Path == "/v1/schedules":
		s.requireSession(w, r, s.handleSchedules)
	case strings.HasPrefix(r.URL.Path, "/v1/schedules/"):
		s.requireSession(w, r, s.handleScheduleDetail)
	case r.URL.Path == "/v1/audit-events" && r.Method == http.MethodGet:
		s.requireSession(w, r, s.handleAuditEvents)
	default:
		writeJSON(w, http.StatusNotFound, ErrorResponse{Error: "not found"})
	}
}

func (s *Server) handleLogin(w http.ResponseWriter, r *http.Request) {
	var req LoginRequest
	if err := decodeJSON(r, &req); err != nil {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: err.Error()})
		return
	}
	if req.Email == "" || req.TenantID == "" {
		writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "email and tenantId are required"})
		return
	}

	now := utcNow()
	displayName := req.DisplayName
	if displayName == "" {
		displayName = strings.Split(req.Email, "@")[0]
	}
	permissions := req.Permissions
	if len(permissions) == 0 {
		permissions = []string{
			"providers:read", "providers:write",
			"collections:read", "collections:write",
			"reports:read", "reports:write",
			"schedules:read", "schedules:write",
			"audit:read",
		}
	}

	session := Session{
		ID:          s.newID("sess"),
		UserID:      s.newID("user"),
		Email:       req.Email,
		DisplayName: displayName,
		TenantID:    req.TenantID,
		Permissions: permissions,
		CreatedAt:   now,
		LastSeenAt:  now,
	}
	if err := s.store.CreateSession(r.Context(), session); err != nil {
		s.writeInternalError(w, err)
		return
	}

	http.SetCookie(w, &http.Cookie{
		Name:     sessionCookieName,
		Value:    session.ID,
		Path:     "/",
		HttpOnly: true,
		SameSite: http.SameSiteLaxMode,
		MaxAge:   60 * 60 * 12,
	})
	writeJSON(w, http.StatusOK, AuthResponse{User: session.toUser()})
}

func (s *Server) handleLogout(w http.ResponseWriter, r *http.Request, session Session) {
	if err := s.store.DeleteSession(r.Context(), session.ID); err != nil {
		s.writeInternalError(w, err)
		return
	}
	http.SetCookie(w, &http.Cookie{
		Name:     sessionCookieName,
		Value:    "",
		Path:     "/",
		HttpOnly: true,
		SameSite: http.SameSiteLaxMode,
		MaxAge:   -1,
	})
	writeJSON(w, http.StatusOK, MessageResponse{Message: "logged out"})
}

func (s *Server) handleRefresh(w http.ResponseWriter, r *http.Request, session Session) {
	refreshed := session
	refreshed.LastSeenAt = utcNow()
	if err := s.store.UpdateSession(r.Context(), refreshed); err != nil {
		s.writeInternalError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, AuthResponse{User: refreshed.toUser()})
}

func (s *Server) handleMe(w http.ResponseWriter, _ *http.Request, session Session) {
	writeJSON(w, http.StatusOK, session.toUser())
}

func (s *Server) handleProviderConfigs(w http.ResponseWriter, r *http.Request, session Session) {
	switch r.Method {
	case http.MethodGet:
		items, err := s.store.ListProviderConfigs(r.Context(), session.TenantID)
		if err != nil {
			s.writeInternalError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, ProviderConfigList{Items: items})
	case http.MethodPost:
		var req ProviderConfigCreateRequest
		if err := decodeJSON(r, &req); err != nil {
			writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: err.Error()})
			return
		}
		if req.Provider == "" {
			writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "provider is required"})
			return
		}
		now := utcNow()
		item := ProviderConfig{
			ID:           s.newID("prov"),
			TenantID:     session.TenantID,
			Provider:     req.Provider,
			State:        "disconnected",
			Connected:    false,
			AccountEmail: req.AccountEmail,
			Health:       "not_connected",
			Scopes:       req.Scopes,
			CreatedAt:    now,
			UpdatedAt:    now,
		}
		if err := s.store.CreateProviderConfig(r.Context(), item); err != nil {
			s.writeInternalError(w, err)
			return
		}
		if err := s.recordAudit(r.Context(), session.TenantID, routeCtx(r).RequestID, "provider.created", "provider_config", item.ID, fmt.Sprintf("Created %s provider config", item.Provider)); err != nil {
			s.writeInternalError(w, err)
			return
		}
		writeJSON(w, http.StatusCreated, item)
	default:
		writeJSON(w, http.StatusMethodNotAllowed, ErrorResponse{Error: "method not allowed"})
	}
}

func (s *Server) handleProviderConfigDetail(w http.ResponseWriter, r *http.Request, session Session) {
	id, action := trimPrefixID(r.URL.Path, "/v1/provider-configs/")
	item, err := s.store.GetProviderConfig(r.Context(), session.TenantID, id)
	if err != nil {
		s.writeLookupError(w, err, "provider config not found")
		return
	}

	if action == "" {
		switch r.Method {
		case http.MethodGet:
			writeJSON(w, http.StatusOK, item)
		case http.MethodPatch:
			var req ProviderConfigUpdateRequest
			if err := decodeJSON(r, &req); err != nil {
				writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: err.Error()})
				return
			}
			if req.AccountEmail != "" {
				item.AccountEmail = req.AccountEmail
			}
			if req.Health != "" {
				item.Health = req.Health
			}
			if req.State != "" {
				item.State = req.State
				item.Connected = req.State == "connected"
			}
			if req.LastSyncAt != "" {
				item.LastSyncAt = req.LastSyncAt
			}
			item.UpdatedAt = utcNow()
			if err := s.store.UpdateProviderConfig(r.Context(), item); err != nil {
				s.writeLookupError(w, err, "provider config not found")
				return
			}
			if err := s.recordAudit(r.Context(), session.TenantID, routeCtx(r).RequestID, "provider.updated", "provider_config", item.ID, "Updated provider config"); err != nil {
				s.writeInternalError(w, err)
				return
			}
			writeJSON(w, http.StatusOK, item)
		default:
			writeJSON(w, http.StatusMethodNotAllowed, ErrorResponse{Error: "method not allowed"})
		}
		return
	}

	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, ErrorResponse{Error: "method not allowed"})
		return
	}

	switch action {
	case "oauth/start":
		state := s.newID("oauth")
		writeJSON(w, http.StatusOK, OAuthFlowResponse{
			AuthorizationURL: fmt.Sprintf("https://example.invalid/oauth/%s?state=%s", item.Provider, state),
			State:            state,
			ProviderConfig:   item,
		})
	case "oauth/callback":
		var req OAuthCallbackRequest
		if err := decodeJSON(r, &req); err != nil {
			writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: err.Error()})
			return
		}
		if req.Code == "" {
			writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "code is required"})
			return
		}
		item.State = "connected"
		item.Connected = true
		item.Health = "healthy"
		item.LastSyncAt = utcNow()
		item.UpdatedAt = item.LastSyncAt
		if err := s.store.UpdateProviderConfig(r.Context(), item); err != nil {
			s.writeLookupError(w, err, "provider config not found")
			return
		}
		if err := s.recordAudit(r.Context(), session.TenantID, routeCtx(r).RequestID, "provider.oauth.callback", "provider_config", item.ID, "Completed provider OAuth flow"); err != nil {
			s.writeInternalError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, item)
	case "oauth/refresh":
		item.Health = "healthy"
		item.State = "connected"
		item.Connected = true
		item.LastSyncAt = utcNow()
		item.UpdatedAt = item.LastSyncAt
		if err := s.store.UpdateProviderConfig(r.Context(), item); err != nil {
			s.writeLookupError(w, err, "provider config not found")
			return
		}
		if err := s.recordAudit(r.Context(), session.TenantID, routeCtx(r).RequestID, "provider.oauth.refresh", "provider_config", item.ID, "Refreshed provider connection"); err != nil {
			s.writeInternalError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, item)
	case "oauth/revoke":
		item.State = "disconnected"
		item.Connected = false
		item.Health = "revoked"
		item.UpdatedAt = utcNow()
		if err := s.store.UpdateProviderConfig(r.Context(), item); err != nil {
			s.writeLookupError(w, err, "provider config not found")
			return
		}
		if err := s.recordAudit(r.Context(), session.TenantID, routeCtx(r).RequestID, "provider.oauth.revoke", "provider_config", item.ID, "Revoked provider connection"); err != nil {
			s.writeInternalError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, item)
	default:
		writeJSON(w, http.StatusNotFound, ErrorResponse{Error: "not found"})
	}
}

func (s *Server) handleCollectionJobs(w http.ResponseWriter, r *http.Request, session Session) {
	switch r.Method {
	case http.MethodGet:
		items, err := s.store.ListCollectionJobs(r.Context(), session.TenantID)
		if err != nil {
			s.writeInternalError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, CollectionJobList{Items: items})
	case http.MethodPost:
		var req CollectionJobCreateRequest
		if err := decodeJSON(r, &req); err != nil {
			writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: err.Error()})
			return
		}
		if len(req.Providers) == 0 || req.Month == 0 || req.Year == 0 {
			writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "providers, month, and year are required"})
			return
		}
		now := utcNow()
		item := CollectionJob{
			ID:              s.newID("job"),
			TenantID:        session.TenantID,
			Status:          "queued",
			Providers:       req.Providers,
			Month:           req.Month,
			Year:            req.Year,
			GraphClientID:   req.GraphClientID,
			GraphAuthority:  req.GraphAuthority,
			GraphTokenCache: req.GraphTokenCache,
			InteractiveAuth: req.InteractiveAuth,
			RequestID:       routeCtx(r).RequestID,
			CreatedAt:       now,
			UpdatedAt:       now,
		}
		if err := s.store.CreateCollectionJob(r.Context(), item); err != nil {
			s.writeInternalError(w, err)
			return
		}
		if err := s.recordAudit(r.Context(), session.TenantID, routeCtx(r).RequestID, "collection.created", "collection_job", item.ID, "Queued collection job"); err != nil {
			s.writeInternalError(w, err)
			return
		}
		item = s.runCollectionJob(r.Context(), session, routeCtx(r).RequestID, item, req)
		writeJSON(w, http.StatusCreated, item)
	default:
		writeJSON(w, http.StatusMethodNotAllowed, ErrorResponse{Error: "method not allowed"})
	}
}

func (s *Server) handleCollectionJobDetail(w http.ResponseWriter, r *http.Request, session Session) {
	id, action := trimPrefixID(r.URL.Path, "/v1/collection-jobs/")
	item, err := s.store.GetCollectionJob(r.Context(), session.TenantID, id)
	if err != nil {
		s.writeLookupError(w, err, "collection job not found")
		return
	}
	if action == "" && r.Method == http.MethodGet {
		writeJSON(w, http.StatusOK, item)
		return
	}
	if action == "retry" && r.Method == http.MethodPost {
		now := utcNow()
		retry := item
		retry.ID = s.newID("job")
		retry.Status = "queued"
		retry.RetryOf = item.ID
		retry.RequestID = routeCtx(r).RequestID
		retry.RunSummaryPath = ""
		retry.InvoicesDir = ""
		retry.Error = ""
		retry.StartedAt = ""
		retry.FinishedAt = ""
		retry.CreatedAt = now
		retry.UpdatedAt = now
		if err := s.store.CreateCollectionJob(r.Context(), retry); err != nil {
			s.writeInternalError(w, err)
			return
		}
		if err := s.recordAudit(r.Context(), session.TenantID, routeCtx(r).RequestID, "collection.retried", "collection_job", retry.ID, fmt.Sprintf("Retried collection job %s", item.ID)); err != nil {
			s.writeInternalError(w, err)
			return
		}
		retry = s.runCollectionJob(r.Context(), session, routeCtx(r).RequestID, retry, CollectionJobCreateRequest{
			Providers:       retry.Providers,
			Month:           retry.Month,
			Year:            retry.Year,
			GraphClientID:   retry.GraphClientID,
			GraphAuthority:  retry.GraphAuthority,
			GraphTokenCache: retry.GraphTokenCache,
			InteractiveAuth: retry.InteractiveAuth,
		})
		writeJSON(w, http.StatusCreated, retry)
		return
	}
	writeJSON(w, http.StatusMethodNotAllowed, ErrorResponse{Error: "method not allowed"})
}

func (s *Server) handleReports(w http.ResponseWriter, r *http.Request, session Session) {
	switch r.Method {
	case http.MethodGet:
		items, err := s.store.ListReports(r.Context(), session.TenantID)
		if err != nil {
			s.writeInternalError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, ReportList{Items: items})
	case http.MethodPost:
		var req ReportCreateRequest
		if err := decodeJSON(r, &req); err != nil {
			writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: err.Error()})
			return
		}
		if req.InputDir == "" || len(req.Formats) == 0 {
			writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "inputDir and formats are required"})
			return
		}
		now := utcNow()
		item := Report{
			ID:        s.newID("report"),
			TenantID:  session.TenantID,
			Status:    "queued",
			InputDir:  req.InputDir,
			Formats:   req.Formats,
			Artifacts: buildArtifacts(req),
			CreatedAt: now,
			UpdatedAt: now,
		}
		if err := s.store.CreateReport(r.Context(), item); err != nil {
			s.writeInternalError(w, err)
			return
		}
		if err := s.recordAudit(r.Context(), session.TenantID, routeCtx(r).RequestID, "report.created", "report", item.ID, "Queued report generation"); err != nil {
			s.writeInternalError(w, err)
			return
		}
		writeJSON(w, http.StatusCreated, item)
	default:
		writeJSON(w, http.StatusMethodNotAllowed, ErrorResponse{Error: "method not allowed"})
	}
}

func (s *Server) handleReportDetail(w http.ResponseWriter, r *http.Request, session Session) {
	id, action := trimPrefixID(r.URL.Path, "/v1/reports/")
	item, err := s.store.GetReport(r.Context(), session.TenantID, id)
	if err != nil {
		s.writeLookupError(w, err, "report not found")
		return
	}
	if action == "" && r.Method == http.MethodGet {
		writeJSON(w, http.StatusOK, item)
		return
	}
	if strings.HasPrefix(action, "artifacts/") && r.Method == http.MethodGet {
		format := strings.TrimPrefix(action, "artifacts/")
		for _, artifact := range item.Artifacts {
			if artifact.Format == format {
				writeJSON(w, http.StatusOK, artifact)
				return
			}
		}
		writeJSON(w, http.StatusNotFound, ErrorResponse{Error: "artifact not found"})
		return
	}
	writeJSON(w, http.StatusMethodNotAllowed, ErrorResponse{Error: "method not allowed"})
}

func (s *Server) handleSchedules(w http.ResponseWriter, r *http.Request, session Session) {
	switch r.Method {
	case http.MethodGet:
		items, err := s.store.ListSchedules(r.Context(), session.TenantID)
		if err != nil {
			s.writeInternalError(w, err)
			return
		}
		writeJSON(w, http.StatusOK, ScheduleList{Items: items})
	case http.MethodPost:
		var req ScheduleCreateRequest
		if err := decodeJSON(r, &req); err != nil {
			writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: err.Error()})
			return
		}
		if req.Name == "" || req.Timezone == "" || req.Cron == "" || len(req.Providers) == 0 {
			writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: "name, timezone, cron, and providers are required"})
			return
		}
		now := utcNow()
		item := Schedule{
			ID:        s.newID("sched"),
			TenantID:  session.TenantID,
			Name:      req.Name,
			Timezone:  req.Timezone,
			Cron:      req.Cron,
			Providers: req.Providers,
			Status:    "active",
			CreatedAt: now,
			UpdatedAt: now,
		}
		if err := s.store.CreateSchedule(r.Context(), item); err != nil {
			s.writeInternalError(w, err)
			return
		}
		if err := s.recordAudit(r.Context(), session.TenantID, routeCtx(r).RequestID, "schedule.created", "schedule", item.ID, "Created schedule"); err != nil {
			s.writeInternalError(w, err)
			return
		}
		writeJSON(w, http.StatusCreated, item)
	default:
		writeJSON(w, http.StatusMethodNotAllowed, ErrorResponse{Error: "method not allowed"})
	}
}

func (s *Server) handleScheduleDetail(w http.ResponseWriter, r *http.Request, session Session) {
	id, action := trimPrefixID(r.URL.Path, "/v1/schedules/")
	item, err := s.store.GetSchedule(r.Context(), session.TenantID, id)
	if err != nil {
		s.writeLookupError(w, err, "schedule not found")
		return
	}
	if action == "" {
		switch r.Method {
		case http.MethodGet:
			writeJSON(w, http.StatusOK, item)
		case http.MethodPatch:
			var req ScheduleUpdateRequest
			if err := decodeJSON(r, &req); err != nil {
				writeJSON(w, http.StatusBadRequest, ErrorResponse{Error: err.Error()})
				return
			}
			if req.Name != "" {
				item.Name = req.Name
			}
			if req.Timezone != "" {
				item.Timezone = req.Timezone
			}
			if req.Cron != "" {
				item.Cron = req.Cron
			}
			if len(req.Providers) > 0 {
				item.Providers = req.Providers
			}
			if req.NextRunAt != "" {
				item.NextRunAt = req.NextRunAt
			}
			item.UpdatedAt = utcNow()
			if err := s.store.UpdateSchedule(r.Context(), item); err != nil {
				s.writeLookupError(w, err, "schedule not found")
				return
			}
			if err := s.recordAudit(r.Context(), session.TenantID, routeCtx(r).RequestID, "schedule.updated", "schedule", item.ID, "Updated schedule"); err != nil {
				s.writeInternalError(w, err)
				return
			}
			writeJSON(w, http.StatusOK, item)
		default:
			writeJSON(w, http.StatusMethodNotAllowed, ErrorResponse{Error: "method not allowed"})
		}
		return
	}
	if r.Method != http.MethodPost {
		writeJSON(w, http.StatusMethodNotAllowed, ErrorResponse{Error: "method not allowed"})
		return
	}
	switch action {
	case "pause":
		item.Status = "paused"
	case "resume":
		item.Status = "active"
	default:
		writeJSON(w, http.StatusNotFound, ErrorResponse{Error: "not found"})
		return
	}
	item.UpdatedAt = utcNow()
	if err := s.store.UpdateSchedule(r.Context(), item); err != nil {
		s.writeLookupError(w, err, "schedule not found")
		return
	}
	if err := s.recordAudit(r.Context(), session.TenantID, routeCtx(r).RequestID, "schedule."+action, "schedule", item.ID, strings.Title(action)+"d schedule"); err != nil {
		s.writeInternalError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, item)
}

func (s *Server) handleAuditEvents(w http.ResponseWriter, r *http.Request, session Session) {
	items, err := s.store.ListAuditEvents(r.Context(), session.TenantID, r.URL.Query().Get("entityType"), r.URL.Query().Get("entityId"))
	if err != nil {
		s.writeInternalError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, AuditEventList{Items: items})
}

func (s *Server) requireSession(w http.ResponseWriter, r *http.Request, next func(http.ResponseWriter, *http.Request, Session)) {
	cookie, err := r.Cookie(sessionCookieName)
	if err != nil || cookie.Value == "" {
		writeJSON(w, http.StatusUnauthorized, ErrorResponse{Error: "unauthorized"})
		return
	}
	session, err := s.store.GetSession(r.Context(), cookie.Value)
	if err != nil {
		if errors.Is(err, ErrNotFound) {
			writeJSON(w, http.StatusUnauthorized, ErrorResponse{Error: "unauthorized"})
			return
		}
		s.writeInternalError(w, err)
		return
	}
	ctx := routeCtx(r)
	ctx.Session = &session
	next(w, withRouteContext(r, ctx), session)
}

func (s *Server) recordAudit(ctx context.Context, tenantID, requestID, action, entityType, entityID, message string) error {
	return s.store.CreateAuditEvent(ctx, AuditEvent{
		ID:         s.newID("audit"),
		TenantID:   tenantID,
		Action:     action,
		EntityType: entityType,
		EntityID:   entityID,
		RequestID:  requestID,
		Message:    message,
		CreatedAt:  utcNow(),
	})
}

func (s *Server) runCollectionJob(ctx context.Context, session Session, requestID string, item CollectionJob, req CollectionJobCreateRequest) CollectionJob {
	started := utcNow()
	item.Status = "running"
	item.StartedAt = started
	item.UpdatedAt = started
	item.Error = ""
	if err := s.store.UpdateCollectionJob(ctx, item); err != nil {
		item.Status = "failed"
		item.Error = "failed to persist running collection state"
		item.FinishedAt = utcNow()
		item.UpdatedAt = item.FinishedAt
		return item
	}
	_ = s.recordAudit(ctx, session.TenantID, requestID, "collection.started", "collection_job", item.ID, "Started collection job")

	result, err := s.collectionRunner.RunCollectionJob(ctx, CollectionRunRequest{
		Job:             item,
		GraphClientID:   req.GraphClientID,
		GraphAuthority:  req.GraphAuthority,
		GraphTokenCache: req.GraphTokenCache,
		InteractiveAuth: req.InteractiveAuth,
		RequestID:       requestID,
	})

	item.RunSummaryPath = result.RunSummaryPath
	item.InvoicesDir = result.InvoicesDir
	item.FinishedAt = utcNow()
	item.UpdatedAt = item.FinishedAt
	item.Error = strings.TrimSpace(result.Error)
	if err != nil {
		if item.Error == "" {
			item.Error = err.Error()
		}
		item.Status = "failed"
	} else if result.Status == "failed" {
		item.Status = "failed"
	} else {
		item.Status = "succeeded"
		item.Error = ""
	}

	if storeErr := s.store.UpdateCollectionJob(ctx, item); storeErr != nil {
		item.Status = "failed"
		if item.Error == "" {
			item.Error = "failed to persist completed collection state"
		}
	}

	action := "collection.succeeded"
	message := "Collection job completed successfully"
	if item.Status == "failed" {
		action = "collection.failed"
		message = pick(item.Error, "Collection job failed")
	}
	_ = s.recordAudit(ctx, session.TenantID, requestID, action, "collection_job", item.ID, message)
	return item
}

func (s *Server) writeLookupError(w http.ResponseWriter, err error, notFoundMessage string) {
	if errors.Is(err, ErrNotFound) {
		writeJSON(w, http.StatusNotFound, ErrorResponse{Error: notFoundMessage})
		return
	}
	s.writeInternalError(w, err)
}

func (s *Server) writeInternalError(w http.ResponseWriter, _ error) {
	writeJSON(w, http.StatusInternalServerError, ErrorResponse{Error: "internal server error"})
}

func buildArtifacts(req ReportCreateRequest) []ReportArtifact {
	artifacts := make([]ReportArtifact, 0, len(req.Formats))
	for _, format := range req.Formats {
		switch format {
		case "json":
			artifacts = append(artifacts, ReportArtifact{Format: format, Path: pick(req.JSONOutput, "reports/invoice_report.json")})
		case "csv":
			artifacts = append(artifacts, ReportArtifact{Format: format, Path: pick(req.CSVOutput, "reports/invoice_report.csv")})
		case "summary_csv":
			artifacts = append(artifacts, ReportArtifact{Format: format, Path: pick(req.SummaryCSVOutput, "reports/invoice_report.summary.csv")})
		case "pdf":
			artifacts = append(artifacts, ReportArtifact{Format: format, Path: pick(req.PDFOutput, "reports/invoice_report.pdf")})
		}
	}
	return artifacts
}

func decodeJSON(r *http.Request, dst any) error {
	defer r.Body.Close()
	if err := json.NewDecoder(r.Body).Decode(dst); err != nil {
		return errors.New("invalid JSON body")
	}
	return nil
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}

func withRouteContext(r *http.Request, ctx routeContext) *http.Request {
	return r.WithContext(contextWithValue(r.Context(), routeContextKey, ctx))
}

func routeCtx(r *http.Request) routeContext {
	if value := r.Context().Value(routeContextKey); value != nil {
		if ctx, ok := value.(routeContext); ok {
			return ctx
		}
	}
	return routeContext{}
}

func trimPrefixID(path, prefix string) (string, string) {
	trimmed := strings.TrimPrefix(path, prefix)
	parts := strings.Split(trimmed, "/")
	if len(parts) == 1 {
		return parts[0], ""
	}
	return parts[0], strings.Join(parts[1:], "/")
}

func (s Session) toUser() User {
	return User{
		ID:          s.UserID,
		Email:       s.Email,
		DisplayName: s.DisplayName,
		TenantID:    s.TenantID,
		Permissions: append([]string(nil), s.Permissions...),
	}
}

func (s *Server) newID(prefix string) string {
	seq := atomic.AddUint64(&s.idCounter, 1)
	var buf [4]byte
	if _, err := rand.Read(buf[:]); err != nil {
		return fmt.Sprintf("%s-%d", prefix, seq)
	}
	return fmt.Sprintf("%s-%d-%s", prefix, seq, hex.EncodeToString(buf[:]))
}

func pick(value, fallback string) string {
	if value != "" {
		return value
	}
	return fallback
}

func utcNow() string {
	return time.Now().UTC().Format(time.RFC3339)
}
