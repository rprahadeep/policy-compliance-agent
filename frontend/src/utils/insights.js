export function statusLabel(status) {
  return String(status || "unclear").replaceAll("_", " ");
}

export function riskTone(level) {
  if (["critical", "high"].includes(level)) return "danger";
  if (level === "medium") return "warning";
  if (level === "low") return "good";
  return "neutral";
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

export function policyOptions(policies) {
  return [...new Set(policies.map((policy) => policy.category).filter(Boolean))];
}
