import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AppShell } from "./AppShell";
import { ErrorBoundary } from "./ErrorBoundary";
import { PermissionGate } from "./PermissionGate";

vi.mock("../auth", () => ({
  useAuth: () => ({
    user: {
      displayName: "Finance Operator",
      tenantId: "tenant-alpha",
      email: "finance@example.com"
    },
    logout: vi.fn().mockResolvedValue(undefined),
    refresh: vi.fn().mockResolvedValue(undefined),
    hasPermission: (prefix: string) => prefix !== "audit"
  })
}));

test("app shell renders permitted navigation links", () => {
  render(
    <MemoryRouter future={{ v7_relativeSplatPath: true, v7_startTransition: true }}>
      <AppShell />
    </MemoryRouter>
  );

  expect(screen.getByRole("link", { name: /providers/i })).toBeInTheDocument();
  expect(screen.queryByRole("link", { name: /audit/i })).not.toBeInTheDocument();
});

test("permission gate hides children when permission is missing", () => {
  render(<PermissionGate prefix="audit" fallback={<p>Blocked</p>}><p>Allowed</p></PermissionGate>);
  expect(screen.getByText("Blocked")).toBeInTheDocument();
});

test("error boundary shows a retry fallback", () => {
  const Problem = () => {
    throw new Error("boom");
  };

  const originalError = console.error;
  console.error = vi.fn();
  render(
    <ErrorBoundary>
      <Problem />
    </ErrorBoundary>
  );
  expect(screen.getByRole("button", { name: /retry the session/i })).toBeInTheDocument();
  console.error = originalError;
});
