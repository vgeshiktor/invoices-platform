import { useEffect, useState } from "react";
import { apiClient } from "../api/client";
import type { CollectionJob } from "../api/types";

const collectionStatusCopy: Record<CollectionJob["status"], string> = {
  queued: "Queued and waiting to start.",
  running: "Worker orchestration is running now.",
  succeeded: "Completed and persisted successfully.",
  failed: "Finished with a persisted failure summary.",
};

function exportSupportBundle(items: CollectionJob[]) {
  const payload = {
    exportedAt: new Date().toISOString(),
    jobs: items,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "support-bundle.json";
  link.click();
  URL.revokeObjectURL(url);
}

export function CollectionsPage() {
  const [items, setItems] = useState<CollectionJob[]>([]);
  const [requestId, setRequestId] = useState<string>();
  const [error, setError] = useState("");

  async function load() {
    const result = await apiClient.listCollectionJobs();
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
          <p className="eyebrow">Weeks 4-5</p>
          <h2>Collection runs</h2>
        </div>
        <div className="row actions-row">
          <button className="button ghost" onClick={() => exportSupportBundle(items)}>
            Export support bundle
          </button>
          <button
            className="button primary"
            onClick={() =>
              void apiClient
                .createCollectionJob({
                  providers: ["gmail", "outlook"],
                  month: new Date().getMonth() + 1,
                  year: new Date().getFullYear(),
                })
                .then((result) => {
                  setRequestId(result.requestId);
                  return load();
                })
                .catch((cause: Error) => setError(cause.message))
            }
          >
            Collect current month
          </button>
        </div>
      </div>
      {requestId ? <p className="status">Last request ID: {requestId}</p> : null}
      {error ? <p className="status error">{error}</p> : null}
      <div className="card-list">
        {items.map((item) => (
          <article className="resource-card" key={item.id}>
            <div className="resource-header">
              <div>
                <h3>{item.providers.join(" + ")}</h3>
                <p className="muted">
                  {String(item.month).padStart(2, "0")}/{item.year}
                </p>
              </div>
              <span className={`pill state-${item.status}`}>{item.status}</span>
            </div>
            <p className="muted">Run request ID: {item.requestId || "pending"}</p>
            <p className="muted">{collectionStatusCopy[item.status]}</p>
            {item.retryOf ? <p className="muted">Retry of: {item.retryOf}</p> : null}
            {item.startedAt ? <p className="muted">Started: {item.startedAt}</p> : null}
            {item.finishedAt ? <p className="muted">Finished: {item.finishedAt}</p> : null}
            {item.runSummaryPath ? <p className="muted">Summary: {item.runSummaryPath}</p> : null}
            {item.invoicesDir ? <p className="muted">Invoices: {item.invoicesDir}</p> : null}
            {item.error ? <p className="status error">{item.error}</p> : null}
            {item.status === "failed" ? (
              <button
                className="button secondary"
                onClick={() =>
                  void apiClient
                    .retryCollectionJob(item.id)
                    .then((result) => {
                      setRequestId(result.requestId);
                      return load();
                    })
                    .catch((cause: Error) => setError(cause.message))
                }
              >
                Retry failed run
              </button>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}
