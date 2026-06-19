import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ApiError, apiClient } from "./api/client";
import { AuthProvider, useAuth } from "./auth";

afterEach(() => {
  vi.restoreAllMocks();
});

function Harness() {
  const { user, loading, login, logout, refresh, hasPermission } = useAuth();

  return (
    <div>
      <p>loading:{String(loading)}</p>
      <p>user:{user?.email ?? "none"}</p>
      <p>canProviders:{String(hasPermission("providers"))}</p>
      <button
        onClick={() =>
          void login({
            email: "fresh@example.com",
            tenantId: "tenant-beta",
            permissions: ["providers:read"]
          })
        }
      >
        login
      </button>
      <button onClick={() => void refresh()}>refresh</button>
      <button onClick={() => void logout()}>logout</button>
    </div>
  );
}

test("auth provider loads unauthorized state then supports login refresh and logout", async () => {
  vi.spyOn(apiClient, "getCurrentUser").mockRejectedValue(new ApiError("unauthorized", 401, "req-401"));
  vi.spyOn(apiClient, "login").mockResolvedValue({
    data: {
      user: {
        id: "user-1",
        email: "fresh@example.com",
        displayName: "Fresh",
        tenantId: "tenant-beta",
        permissions: ["providers:read"]
      }
    },
    requestId: "req-login"
  });
  vi.spyOn(apiClient, "refreshSession").mockResolvedValue({
    data: {
      user: {
        id: "user-1",
        email: "fresh@example.com",
        displayName: "Fresh",
        tenantId: "tenant-beta",
        permissions: ["providers:read", "reports:read"]
      }
    },
    requestId: "req-refresh"
  });
  vi.spyOn(apiClient, "logout").mockResolvedValue({
    data: { message: "logged out" },
    requestId: "req-logout"
  });

  render(
    <AuthProvider>
      <Harness />
    </AuthProvider>
  );

  await waitFor(() => expect(screen.getByText("loading:false")).toBeInTheDocument());
  expect(screen.getByText("user:none")).toBeInTheDocument();
  expect(screen.getByText("canProviders:false")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "login" }));
  await waitFor(() => expect(screen.getByText("user:fresh@example.com")).toBeInTheDocument());
  expect(screen.getByText("canProviders:true")).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: "refresh" }));
  await waitFor(() => expect(apiClient.refreshSession).toHaveBeenCalled());

  await userEvent.click(screen.getByRole("button", { name: "logout" }));
  await waitFor(() => expect(screen.getByText("user:none")).toBeInTheDocument());
});

test("useAuth throws outside provider", () => {
  const originalError = console.error;
  console.error = vi.fn();
  expect(() => render(<Harness />)).toThrow(/useAuth must be used inside AuthProvider/i);
  console.error = originalError;
});
