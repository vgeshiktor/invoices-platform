import { useEffect, useState } from "react";
import { apiClient } from "../api/client";
import type { ProviderConfig } from "../api/types";

export function ProvidersPage() {
  const [items, setItems] = useState<ProviderConfig[]>([]);
  const [requestId, setRequestId] = useState<string>();
  const [error, setError] = useState("");

  async function load() {
    const result = await apiClient.listProviderConfigs();
    setItems(result.data.items);
    setRequestId(result.requestId);
  }

  useEffect(() => {
    void load().catch((cause: Error) => setError(cause.message));
  }, []);

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Week 3</p>
          <h2>Provider settings</h2>
        </div>
        <button
          className="button primary"
          onClick={() =>
            void apiClient
              .createProviderConfig({ provider: "gmail", accountEmail: "billing@example.com" })
              .then((result) => {
                setRequestId(result.requestId);
                return load();
              })
              .catch((cause: Error) => setError(cause.message))
          }
        >
          Add Gmail provider
        </button>
      </div>
      {requestId ? <p className="status">Last request ID: {requestId}</p> : null}
      {error ? <p className="status error">{error}</p> : null}
      <div className="card-list">
        {items.map((item) => (
          <article className="resource-card" key={item.id}>
            <div className="resource-header">
              <div>
                <h3>{item.provider.toUpperCase()}</h3>
                <p className="muted">{item.accountEmail || "No account email yet"}</p>
              </div>
              <span className={`pill state-${item.state}`}>{item.state}</span>
            </div>
            <p className="muted">Health: {item.health || "unknown"}</p>
            <div className="row actions-row">
              <button
                className="button ghost"
                onClick={() =>
                  void apiClient
                    .startProviderOAuth(item.id)
                    .then((result) => setRequestId(result.requestId))
                    .catch((cause: Error) => setError(cause.message))
                }
              >
                Begin OAuth
              </button>
              <button
                className="button secondary"
                onClick={() =>
                  void apiClient
                    .completeProviderOAuth(item.id)
                    .then((result) => {
                      setRequestId(result.requestId);
                      return load();
                    })
                    .catch((cause: Error) => setError(cause.message))
                }
              >
                Connect
              </button>
              <button
                className="button ghost"
                onClick={() =>
                  void apiClient
                    .refreshProviderOAuth(item.id)
                    .then((result) => {
                      setRequestId(result.requestId);
                      return load();
                    })
                    .catch((cause: Error) => setError(cause.message))
                }
              >
                Refresh
              </button>
              <button
                className="button ghost"
                onClick={() =>
                  void apiClient
                    .revokeProviderOAuth(item.id)
                    .then((result) => {
                      setRequestId(result.requestId);
                      return load();
                    })
                    .catch((cause: Error) => setError(cause.message))
                }
              >
                Revoke
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
