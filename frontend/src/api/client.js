const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || data.message || `Request failed: ${response.status}`);
  }
  return data;
}

export function getPolicies() {
  return request("/api/v1/policies");
}

export function getAnalytics() {
  return request("/api/v1/analytics");
}

export function ingestPolicies() {
  return request("/api/v1/ingest", { method: "POST" });
}

export function queryCompliance(payload) {
  return request("/api/v1/query", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}
