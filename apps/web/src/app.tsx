import type { ReactNode } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import { AppShell } from "./components/AppShell";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { PermissionGate } from "./components/PermissionGate";
import { AuditPage } from "./routes/AuditPage";
import { CollectionsPage } from "./routes/CollectionsPage";
import { DashboardPage } from "./routes/DashboardPage";
import { LoginPage } from "./routes/LoginPage";
import { ProvidersPage } from "./routes/ProvidersPage";
import { ReportsPage } from "./routes/ReportsPage";
import { SchedulesPage } from "./routes/SchedulesPage";

function ProtectedLayout() {
  const { loading, user } = useAuth();

  if (loading) {
    return <main className="auth-screen"><p className="status">Loading tenant session...</p></main>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <AppShell />;
}

function ProtectedRoute({
  prefix,
  element,
}: {
  prefix: string;
  element: ReactNode;
}) {
  return <PermissionGate prefix={prefix} fallback={<Navigate to="/" replace />}>{element}</PermissionGate>;
}

export function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <BrowserRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/" element={<ProtectedLayout />}>
              <Route index element={<DashboardPage />} />
              <Route path="providers" element={<ProtectedRoute prefix="providers" element={<ProvidersPage />} />} />
              <Route path="collections" element={<ProtectedRoute prefix="collections" element={<CollectionsPage />} />} />
              <Route path="reports" element={<ProtectedRoute prefix="reports" element={<ReportsPage />} />} />
              <Route path="schedules" element={<ProtectedRoute prefix="schedules" element={<SchedulesPage />} />} />
              <Route path="audit" element={<ProtectedRoute prefix="audit" element={<AuditPage />} />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ErrorBoundary>
  );
}
