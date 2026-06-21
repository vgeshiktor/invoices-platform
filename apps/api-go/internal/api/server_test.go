package api

import (
	"bytes"
	"encoding/json"
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
