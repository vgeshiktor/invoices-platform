import { useEffect, useState } from "react";
import { apiClient } from "../api/client";
import type { AuditEvent } from "../api/types";

export function AuditPage() {
  const [items, setItems] = useState<AuditEvent[]>([]);
  const [requestId, setRequestId] = useState<string>();
  const [error, setError] = useState("");

  useEffect(() => {
    void apiClient
      .listAuditEvents()
      .then((result) => {
        setItems(result.data.items);
        setRequestId(result.requestId);
      })
      .catch((cause: Error) => setError(cause.message));
  }, []);

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Weeks 9-10</p>
          <h2>Audit timeline</h2>
        </div>
        <p className="muted">
          Request correlation IDs flow through the backend and surface here for support diagnostics.
        </p>
      </div>
      {requestId ? <p className="status">Last request ID: {requestId}</p> : null}
      {error ? <p className="status error">{error}</p> : null}
      <div className="timeline">
        {items.map((item) => (
          <article className="timeline-entry" key={item.id}>
            <p className="timeline-headline">
              {item.action} · {item.entityType} · {item.entityId}
            </p>
            <p className="muted">{item.message || "No message"}</p>
            <p className="timeline-meta">
              {item.createdAt} · Request ID {item.requestId}
            </p>
          </article>
        ))}
      </div>
    </section>
  );
}
