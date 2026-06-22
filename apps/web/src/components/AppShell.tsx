import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth";

const navItems = [
  { to: "/", label: "Overview", prefix: "collections" },
  { to: "/providers", label: "Providers", prefix: "providers" },
  { to: "/collections", label: "Collections", prefix: "collections" },
  { to: "/reports", label: "Reports", prefix: "reports" },
  { to: "/schedules", label: "Schedules", prefix: "schedules" },
  { to: "/audit", label: "Audit", prefix: "audit" },
];

export function AppShell() {
  const { user, logout, refresh, hasPermission } = useAuth();

  return (
    <div className="shell">
      <aside className="shell-sidebar">
        <div>
          <p className="eyebrow">Invoices control plane</p>
          <h1>Ops command deck</h1>
          <p className="muted">
            Tenant-scoped workflows for auth, providers, collection, reporting, schedules, and audit.
          </p>
        </div>
        <nav className="shell-nav">
          {navItems
            .filter((item) => hasPermission(item.prefix))
            .map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}
              >
                {item.label}
              </NavLink>
            ))}
        </nav>
        <div className="tenant-card">
          <p className="tenant-name">{user?.displayName}</p>
          <p className="tenant-meta">{user?.tenantId}</p>
          <p className="tenant-meta">{user?.email}</p>
          <div className="row actions-row">
            <button className="button ghost" onClick={() => void refresh()}>
              Refresh
            </button>
            <button className="button secondary" onClick={() => void logout()}>
              Logout
            </button>
          </div>
        </div>
      </aside>
      <main className="shell-main">
        <Outlet />
      </main>
    </div>
  );
}
