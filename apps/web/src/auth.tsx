/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { ApiError, apiClient } from "./api/client";
import type { User } from "./api/types";

type AuthContextValue = {
  user: User | null;
  loading: boolean;
  login: (payload: {
    email: string;
    tenantId: string;
    displayName?: string;
    permissions?: string[];
  }) => Promise<string | undefined>;
  logout: () => Promise<string | undefined>;
  refresh: () => Promise<string | undefined>;
  hasPermission: (prefix: string) => boolean;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const result = await apiClient.getCurrentUser();
        if (!cancelled) {
          setUser(result.data);
        }
      } catch (error) {
        if (!(error instanceof ApiError) || error.status !== 401) {
          throw error;
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      async login(payload) {
        const result = await apiClient.login(payload);
        setUser(result.data.user);
        return result.requestId;
      },
      async logout() {
        const result = await apiClient.logout();
        setUser(null);
        return result.requestId;
      },
      async refresh() {
        const result = await apiClient.refreshSession();
        setUser(result.data.user);
        return result.requestId;
      },
      hasPermission(prefix) {
        return user?.permissions.some((permission) => permission.startsWith(prefix)) ?? false;
      },
    }),
    [loading, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
