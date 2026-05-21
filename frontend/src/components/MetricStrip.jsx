import React from "react";
import { formatPercent } from "../utils/insights.js";
import { AlertTriangle, BarChart3, BookOpen, Gauge } from "./Icon.js";

export function MetricStrip({ policies, analytics, answer }) {
  const highRisk = (analytics?.risk_level_counts?.high || 0) + (analytics?.risk_level_counts?.critical || 0);
  const confidence = answer?.citations?.length ? Math.min(98, answer.citations.length * 13) : 0;
  const contextPrecision = answer?.context_precision?.score ?? 0;

  return (
    <section className="metric-strip">
      <Metric icon={<BookOpen size={18} />} label="Indexed sources" value={policies.length} />
      <Metric icon={<BarChart3 size={18} />} label="Queries analyzed" value={analytics?.total_queries ?? 0} />
      <Metric icon={<AlertTriangle size={18} />} label="High risk flags" value={highRisk} />
      <Metric icon={<Gauge size={18} />} label="Evidence confidence" value={`${confidence}%`} />
      <Metric icon={<Gauge size={18} />} label="Context precision" value={formatPercent(contextPrecision)} />
    </section>
  );
}

function Metric({ icon, label, value }) {
  return (
    <div className="metric-cell">
      <div>{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
