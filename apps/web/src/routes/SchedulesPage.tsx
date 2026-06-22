import { useEffect, useState } from "react";
import { apiClient } from "../api/client";
import type { Schedule } from "../api/types";

export function SchedulesPage() {
  const [items, setItems] = useState<Schedule[]>([]);
  const [requestId, setRequestId] = useState<string>();
  const [error, setError] = useState("");

  async function load() {
    const result = await apiClient.listSchedules();
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
          <p className="eyebrow">Weeks 7-8</p>
          <h2>Schedules</h2>
        </div>
        <button
          className="button primary"
          onClick={() =>
            void apiClient
              .createSchedule({
                name: "Daily month collection",
                timezone: "Asia/Jerusalem",
                cron: "0 8 * * *",
                providers: ["gmail", "outlook"],
              })
              .then((result) => {
                setRequestId(result.requestId);
                return load();
              })
              .catch((cause: Error) => setError(cause.message))
          }
        >
          Add schedule
        </button>
      </div>
      {requestId ? <p className="status">Last request ID: {requestId}</p> : null}
      {error ? <p className="status error">{error}</p> : null}
      <div className="card-list">
        {items.map((item) => (
          <article className="resource-card" key={item.id}>
            <div className="resource-header">
              <div>
                <h3>{item.name}</h3>
                <p className="muted">
                  {item.cron} · {item.timezone}
                </p>
              </div>
              <span className={`pill state-${item.status}`}>{item.status}</span>
            </div>
            <p className="muted">Providers: {item.providers.join(", ")}</p>
            <div className="row actions-row">
              {item.status === "active" ? (
                <button
                  className="button secondary"
                  onClick={() =>
                    void apiClient
                      .pauseSchedule(item.id)
                      .then((result) => {
                        setRequestId(result.requestId);
                        return load();
                      })
                      .catch((cause: Error) => setError(cause.message))
                  }
                >
                  Pause
                </button>
              ) : (
                <button
                  className="button secondary"
                  onClick={() =>
                    void apiClient
                      .resumeSchedule(item.id)
                      .then((result) => {
                        setRequestId(result.requestId);
                        return load();
                      })
                      .catch((cause: Error) => setError(cause.message))
                  }
                >
                  Resume
                </button>
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
