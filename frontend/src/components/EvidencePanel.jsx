import React, { useMemo, useState } from "react";
import { BrainCircuit, ChevronDown, FileSearch, Layers3 } from "./Icon.js";

export function EvidencePanel({ answer, policies, analytics }) {
  const [activePolicy, setActivePolicy] = useState("all");
  const citations = answer?.citations || [];
  const policyNames = useMemo(() => [...new Set(citations.map((citation) => citation.policy_name))], [citations]);
  const filtered = activePolicy === "all" ? citations : citations.filter((citation) => citation.policy_name === activePolicy);

  return (
    <aside className="evidence-panel">
      <section className="evidence-section">
        <div className="side-title">
          <FileSearch size={18} />
          <h2>Evidence locker</h2>
        </div>
        <select value={activePolicy} onChange={(event) => setActivePolicy(event.target.value)}>
          <option value="all">All cited policies</option>
          {policyNames.map((name) => (
            <option key={name} value={name}>{name}</option>
          ))}
        </select>
        <div className="citation-list">
          {filtered.length === 0 && <p className="muted">No citations yet.</p>}
          {filtered.map((citation) => (
            <details className="citation-item" key={citation.source_id} open>
              <summary>
                <span>{citation.policy_name}</span>
                <ChevronDown size={15} />
              </summary>
              <small>Page {citation.page} | {citation.section || citation.category} | Score {citation.score ?? "n/a"}</small>
              <p>{citation.excerpt}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="evidence-section">
        <div className="side-title">
          <BrainCircuit size={18} />
          <h2>Agent trace</h2>
        </div>
        <div className="agent-list">
          {Object.entries(answer?.agent_trace || {}).length === 0 && <p className="muted">Agent outputs will appear after a query.</p>}
          {Object.entries(answer?.agent_trace || {}).map(([agent, text]) => (
            <article key={agent}>
              <strong>{agent.replaceAll("_", " ")}</strong>
              <p>{text}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="evidence-section compact">
        <div className="side-title">
          <Layers3 size={18} />
          <h2>Coverage map</h2>
        </div>
        {policies.map((policy) => (
          <div className="policy-row" key={policy.path}>
            <span>{policy.category}</span>
            <b>{policy.pages || "-"} pages</b>
          </div>
        ))}
        <div className="topics-inline">
          {(analytics?.top_topics || []).slice(0, 6).map((topic) => (
            <span key={topic.topic}>{topic.topic}</span>
          ))}
        </div>
      </section>
    </aside>
  );
}
