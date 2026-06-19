import { Navigate } from "react-router-dom";
import { useState } from "react";
import { useAuth } from "../auth";

export function LoginPage() {
  const { login, user } = useAuth();
  const [email, setEmail] = useState("finance.operator@example.com");
  const [tenantId, setTenantId] = useState("tenant-alpha");
  const [displayName, setDisplayName] = useState("Finance Operator");
  const [permissionsText, setPermissionsText] = useState("");
  const [error, setError] = useState("");
  const [lastRequestId, setLastRequestId] = useState<string>();

  if (user) {
    return <Navigate to="/" replace />;
  }

  return (
    <main className="auth-screen">
      <section className="auth-card">
        <p className="eyebrow">Week 1-2 foundation</p>
        <h1>Sign into the invoice control plane</h1>
        <p className="muted">
          The baseline Go API uses server-managed cookie sessions and permission lists from `/v1/me`.
        </p>
        <form
          className="stack"
          onSubmit={(event) => {
            event.preventDefault();
            setError("");
            void login({
              email,
              tenantId,
              displayName,
              permissions: permissionsText
                .split(",")
                .map((item) => item.trim())
                .filter(Boolean),
            })
              .then((requestId) => setLastRequestId(requestId))
              .catch((cause: Error) => setError(cause.message));
          }}
        >
          <label className="field">
            <span>Email</span>
            <input value={email} onChange={(event) => setEmail(event.target.value)} />
          </label>
          <label className="field">
            <span>Tenant ID</span>
            <input value={tenantId} onChange={(event) => setTenantId(event.target.value)} />
          </label>
          <label className="field">
            <span>Display name</span>
            <input value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
          </label>
          <label className="field">
            <span>Optional permissions CSV</span>
            <input
              placeholder="providers:read,providers:write,..."
              value={permissionsText}
              onChange={(event) => setPermissionsText(event.target.value)}
            />
          </label>
          {error ? <p className="status error">{error}</p> : null}
          {lastRequestId ? <p className="status">Request ID: {lastRequestId}</p> : null}
          <button className="button primary" type="submit">
            Start tenant session
          </button>
        </form>
      </section>
    </main>
  );
}
