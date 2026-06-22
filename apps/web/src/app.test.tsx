import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./app";

const fetchMock = vi.fn<typeof fetch>();

beforeEach(() => {
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  fetchMock.mockReset();
});

test("renders login flow and lands on overview after successful auth", async () => {
  fetchMock
    .mockResolvedValueOnce(
      new Response(JSON.stringify({ error: "unauthorized" }), {
        status: 401,
        headers: { "Content-Type": "application/json" },
      })
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          user: {
            id: "user-1",
            email: "finance@example.com",
            displayName: "Finance",
            tenantId: "tenant-alpha",
            permissions: ["providers:read", "collections:read", "reports:read", "schedules:read", "audit:read"],
          },
        }),
        {
          status: 200,
          headers: {
            "Content-Type": "application/json",
            "X-Request-ID": "req-1",
          },
        }
      )
    );

  render(<App />);

  expect(await screen.findByRole("heading", { name: /sign into the invoice control plane/i })).toBeInTheDocument();

  await userEvent.click(screen.getByRole("button", { name: /start tenant session/i }));

  await waitFor(() => {
    expect(screen.getByRole("heading", { name: /roadmap baseline is live/i })).toBeInTheDocument();
  });
});
