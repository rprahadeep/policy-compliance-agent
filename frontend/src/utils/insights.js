export function statusLabel(status) {
  return String(status || "unclear").replaceAll("_", " ");
}

export function riskTone(level) {
  if (["critical", "high"].includes(level)) return "danger";
  if (level === "medium") return "warning";
  if (level === "low") return "good";
  return "neutral";
}

export function riskLevelFromScore(score) {
  const value = Math.max(0, Math.min(100, Number(score || 0)));
  if (value >= 76) return "critical";
  if (value >= 51) return "high";
  if (value >= 26) return "medium";
  return "low";
}

export function sourceCoverage(citations = []) {
  const policies = new Set(citations.map((citation) => citation.policy_name).filter(Boolean));
  const pages = new Set(citations.map((citation) => `${citation.policy_name}-${citation.page}`).filter(Boolean));
  return {
    policyCount: policies.size,
    pageCount: pages.size,
    confidence: Math.min(98, Math.max(18, citations.length * 12 + policies.size * 8)),
  };
}

export function formatPercent(value) {
  const numeric = Number(value || 0);
  return `${Math.round(Math.max(0, Math.min(1, numeric)) * 100)}%`;
}

export function policyOptions(policies) {
  return [...new Set(policies.map((policy) => policy.category).filter(Boolean))];
}
