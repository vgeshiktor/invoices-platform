import type { ReactNode } from "react";
import { useAuth } from "../auth";

export function PermissionGate({
  prefix,
  children,
  fallback = null,
}: {
  prefix: string;
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { hasPermission } = useAuth();
  return hasPermission(prefix) ? <>{children}</> : <>{fallback}</>;
}
