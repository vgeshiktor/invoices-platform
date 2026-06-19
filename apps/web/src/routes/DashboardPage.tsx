import { useMemo } from "react";
import { useAuth } from "../auth";

export function DashboardPage() {
  const { user } = useAuth();
  const cards = useMemo(
    () => [
      {
        label: "Permission sets",
        value: user?.permissions.length ?? 0,
        caption: "Action groups exposed by `/v1/me`"
      },
      {
        label: "Phase coverage",
        value: "1-10",
        caption: "Routes scaffolded for every active milestone"
      },
      {
        label: "Session mode",
        value: "Cookie",
        caption: "Server-managed auth with refresh and logout"
      }
    ],
    [user?.permissions.length]
  );

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <p className="eyebrow">Overview</p>
          <h2>Roadmap baseline is live</h2>
        </div>
        <p className="muted">
          The frontend now mirrors the GitHub Weeks 1-10 roadmap with protected routes and resource screens.
        </p>
      </div>
      <div className="metrics-grid">
        {cards.map((card) => (
          <article className="metric-card" key={card.label}>
            <p className="metric-label">{card.label}</p>
            <strong className="metric-value">{card.value}</strong>
            <p className="muted">{card.caption}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
