package api

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestHealthz(t *testing.T) {
	req := httptest.NewRequest(http.MethodGet, "/healthz", nil)
	rec := httptest.NewRecorder()

	NewServer().Handler().ServeHTTP(rec, req)

	if rec.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", rec.Code)
	}
}

func TestLoginAndGetMe(t *testing.T) {
	server := NewServer()
	loginBody, _ := json.Marshal(LoginRequest{
		Email:    "owner@example.com",
		TenantID: "tenant-alpha",
	})
	loginReq := httptest.NewRequest(http.MethodPost, "/auth/login", bytes.NewReader(loginBody))
	loginRec := httptest.NewRecorder()

	server.Handler().ServeHTTP(loginRec, loginReq)

	if loginRec.Code != http.StatusOK {
		t.Fatalf("expected login 200, got %d", loginRec.Code)
	}
	cookies := loginRec.Result().Cookies()
	if len(cookies) == 0 {
		t.Fatal("expected session cookie")
	}

	meReq := httptest.NewRequest(http.MethodGet, "/v1/me", nil)
	meReq.AddCookie(cookies[0])
	meRec := httptest.NewRecorder()

	server.Handler().ServeHTTP(meRec, meReq)

	if meRec.Code != http.StatusOK {
		t.Fatalf("expected me 200, got %d", meRec.Code)
	}
}

func TestCreateProviderConfigAndAuditTrail(t *testing.T) {
	server := NewServer()
	cookie := loginForTest(t, server)

	payload, _ := json.Marshal(ProviderConfigCreateRequest{
		Provider:     "gmail",
		AccountEmail: "finance@example.com",
		Scopes:       []string{"gmail.readonly"},
	})
	req := httptest.NewRequest(http.MethodPost, "/v1/provider-configs", bytes.NewReader(payload))
	req.AddCookie(cookie)
	rec := httptest.NewRecorder()

	server.Handler().ServeHTTP(rec, req)

	if rec.Code != http.StatusCreated {
		t.Fatalf("expected create 201, got %d", rec.Code)
	}

	auditReq := httptest.NewRequest(http.MethodGet, "/v1/audit-events", nil)
	auditReq.AddCookie(cookie)
	auditRec := httptest.NewRecorder()
	server.Handler().ServeHTTP(auditRec, auditReq)

	if auditRec.Code != http.StatusOK {
		t.Fatalf("expected audit 200, got %d", auditRec.Code)
	}
}

func TestCollectionJobRunsAndPersistsFinalState(t *testing.T) {
	server := NewServer(
		WithCollectionRunner(fakeCollectionRunner{
			result: CollectionRunResult{
				Status:         "succeeded",
				RunSummaryPath: "/tmp/run_summary.json",
				InvoicesDir:    "/tmp/invoices_06_2026",
			},
		}),
	)
	cookie := loginForTest(t, server)

	payload, _ := json.Marshal(CollectionJobCreateRequest{
		Providers: []string{"gmail"},
		Month:     6,
		Year:      2026,
	})
	req := httptest.NewRequest(http.MethodPost, "/v1/collection-jobs", bytes.NewReader(payload))
	req.AddCookie(cookie)
	rec := httptest.NewRecorder()
	server.Handler().ServeHTTP(rec, req)

	if rec.Code != http.StatusCreated {
		t.Fatalf("expected create 201, got %d", rec.Code)
	}
	var job CollectionJob
	if err := json.NewDecoder(rec.Body).Decode(&job); err != nil {
		t.Fatalf("decode job: %v", err)
	}
	if job.Status != "succeeded" {
		t.Fatalf("expected succeeded status, got %s", job.Status)
	}
	if job.RunSummaryPath == "" || job.InvoicesDir == "" || job.StartedAt == "" || job.FinishedAt == "" {
		t.Fatalf("expected persisted runtime fields, got %#v", job)
	}
}

func TestCollectionJobFailurePersistsErrorAndSupportsRetry(t *testing.T) {
	server := NewServer(
		WithCollectionRunner(fakeCollectionRunner{
			err: "provider timeout",
			result: CollectionRunResult{
				Status: "failed",
				Error:  "provider timeout",
			},
		}),
	)
	cookie := loginForTest(t, server)

	payload, _ := json.Marshal(CollectionJobCreateRequest{
		Providers: []string{"outlook"},
		Month:     6,
		Year:      2026,
	})
	req := httptest.NewRequest(http.MethodPost, "/v1/collection-jobs", bytes.NewReader(payload))
	req.AddCookie(cookie)
	rec := httptest.NewRecorder()
	server.Handler().ServeHTTP(rec, req)

	var failedJob CollectionJob
	if err := json.NewDecoder(rec.Body).Decode(&failedJob); err != nil {
		t.Fatalf("decode failed job: %v", err)
	}
	if failedJob.Status != "failed" || failedJob.Error == "" {
		t.Fatalf("expected failed job with error, got %#v", failedJob)
	}

	retryReq := httptest.NewRequest(http.MethodPost, "/v1/collection-jobs/"+failedJob.ID+"/retry", nil)
	retryReq.AddCookie(cookie)
	retryRec := httptest.NewRecorder()
	server.Handler().ServeHTTP(retryRec, retryReq)

	if retryRec.Code != http.StatusCreated {
		t.Fatalf("expected retry 201, got %d", retryRec.Code)
	}
	var retried CollectionJob
	if err := json.NewDecoder(retryRec.Body).Decode(&retried); err != nil {
		t.Fatalf("decode retried job: %v", err)
	}
	if retried.RetryOf != failedJob.ID || retried.Status != "failed" {
		t.Fatalf("expected failed retry linked to original job, got %#v", retried)
	}
}

func loginForTest(t *testing.T, server *Server) *http.Cookie {
	t.Helper()

	payload, _ := json.Marshal(LoginRequest{
		Email:    "operator@example.com",
		TenantID: "tenant-alpha",
	})
	req := httptest.NewRequest(http.MethodPost, "/auth/login", bytes.NewReader(payload))
	rec := httptest.NewRecorder()
	server.Handler().ServeHTTP(rec, req)
	if rec.Code != http.StatusOK {
		t.Fatalf("expected login 200, got %d", rec.Code)
	}
	return rec.Result().Cookies()[0]
}

type fakeCollectionRunner struct {
	result CollectionRunResult
	err    string
}

func (f fakeCollectionRunner) RunCollectionJob(_ context.Context, _ CollectionRunRequest) (CollectionRunResult, error) {
	if f.err != "" {
		return f.result, errors.New(f.err)
	}
	return f.result, nil
}
