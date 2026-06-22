import fs from "node:fs";
import path from "node:path";
import { parse } from "yaml";

const repoRoot = path.resolve(import.meta.dirname, "..", "..", "..");
const openapiPath = path.join(repoRoot, "integrations", "openapi", "invoices.yaml");
const outputPath = path.join(import.meta.dirname, "..", "src", "api", "generated.ts");

const openapi = parse(fs.readFileSync(openapiPath, "utf8"));

const requiredOperations = [
  ["get", "/healthz", "getHealthz"],
  ["post", "/auth/login", "login"],
  ["post", "/auth/logout", "logout"],
  ["post", "/auth/refresh", "refreshSession"],
  ["get", "/v1/me", "getCurrentUser"],
  ["get", "/v1/provider-configs", "listProviderConfigs"],
  ["post", "/v1/provider-configs", "createProviderConfig"],
  ["get", "/v1/collection-jobs", "listCollectionJobs"],
  ["post", "/v1/collection-jobs", "createCollectionJob"],
  ["get", "/v1/reports", "listReports"],
  ["post", "/v1/reports", "createReport"],
  ["get", "/v1/schedules", "listSchedules"],
  ["post", "/v1/schedules", "createSchedule"],
  ["get", "/v1/audit-events", "listAuditEvents"]
];

for (const [method, route, operationId] of requiredOperations) {
  const operation = openapi?.paths?.[route]?.[method];
  if (!operation || operation.operationId !== operationId) {
    throw new Error(`OpenAPI contract missing ${method.toUpperCase()} ${route} -> ${operationId}`);
  }
}

const operations = {};
for (const [route, methods] of Object.entries(openapi.paths ?? {})) {
  for (const [method, details] of Object.entries(methods)) {
    operations[details.operationId] = {
      method: method.toUpperCase(),
      path: route
    };
  }
}

const content = `// Generated from integrations/openapi/invoices.yaml by scripts/generate-api-client.mjs.

export const operations = ${JSON.stringify(operations, null, 2)} as const;

export type OperationName = keyof typeof operations;

export function buildPath(
  operation: OperationName,
  params?: Record<string, string | number>
): string {
  let route = operations[operation].path as string;
  for (const [key, value] of Object.entries(params ?? {})) {
    route = route.replace(\`{\${key}}\`, String(value));
  }
  return route;
}
`;

fs.writeFileSync(outputPath, content, "utf8");
