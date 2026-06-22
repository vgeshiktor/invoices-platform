import { useEffect, useState } from "react";

import { apiClient } from "../api/client";
import type { Report, ReportArtifact } from "../api/types";

const formatOrder: ReportArtifact["format"][] = ["json", "pdf", "csv", "summary_csv"];

type FormatState = Record<ReportArtifact["format"], boolean>;

const defaultFormats: FormatState = {
  json: true,
  pdf: true,
  csv: false,
  summary_csv: false,
};

function selectedFormats(formats: FormatState) {
  return formatOrder.filter((format) => formats[format]);
}

function formatAmount(value?: number) {
  return value?.toFixed(2) ?? "0.00";
}

export function ReportsPage() {
  const [items, setItems] = useState<Report[]>([]);
  const [formats, setFormats] = useState<FormatState>(defaultFormats);
  const [requestId, setRequestId] = useState<string>();
  const [error, setError] = useState("");

  async function load() {
    const result = await apiClient.listReports();
    setItems(result.data.items);
    setRequestId(result.requestId);
  }

  useEffect(() => {
    void load().catch((cause: Error) => setError(cause.message));
  }, []);

  function toggleFormat(format: ReportArtifact["format"]) {
    setFormats((current) => ({ ...current, [format]: !current[format] }));
  }

  async function queueReport() {
    const activeFormats = selectedFormats(formats);
    const payloadFormats: ReportArtifact["format"][] = activeFormats.length > 0 ? activeFormats : ["json"];
    const result = await apiClient.createReport({
      inputDir: "invoices/invoices_01_2026",
      formats: payloadFormats,
    });
    setRequestId(result.requestId);
    await load();
  }

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Week 6</p>
          <h2>Reports</h2>
        </div>
        <button
          className="button primary"
          onClick={() => void queueReport().catch((cause: Error) => setError(cause.message))}
        >
          Queue report
        </button>
      </div>
      <div className="row actions-row">
        {formatOrder.map((format) => (
          <label className="muted" key={format}>
            <input checked={formats[format]} onChange={() => toggleFormat(format)} type="checkbox" />
            {" "}
            {format}
          </label>
        ))}
      </div>
      {requestId ? <p className="status">Last request ID: {requestId}</p> : null}
      {error ? <p className="status error">{error}</p> : null}
      <div className="card-list">
        {items.map((item) => (
          <article className="resource-card" key={item.id}>
            <div className="resource-header">
              <div>
                <h3>{item.inputDir}</h3>
                <p className="muted">{item.formats.join(", ")}</p>
              </div>
              <span className={`pill state-${item.status}`}>{item.status}</span>
            </div>
            {item.startedAt ? <p className="muted">Started: {item.startedAt}</p> : null}
            {item.finishedAt ? <p className="muted">Finished: {item.finishedAt}</p> : null}
            {item.error ? <p className="status error">{item.error}</p> : null}
            {item.totals ? (
              <div className="row actions-row">
                <p className="muted">
                  Net <span>{formatAmount(item.totals.netTotal)}</span>
                </p>
                <p className="muted">
                  VAT <span>{formatAmount(item.totals.vatTotal)}</span>
                </p>
                <p className="muted">
                  Gross <span>{formatAmount(item.totals.grossTotal)}</span>
                </p>
              </div>
            ) : null}
            <div className="card-list">
              {item.artifacts.map((artifact) => (
                <a href={artifact.path} key={`${item.id}-${artifact.format}`}>
                  {artifact.format}: {artifact.path}
                </a>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
