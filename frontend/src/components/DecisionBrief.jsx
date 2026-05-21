import React from "react";
import { riskTone, sourceCoverage, statusLabel } from "../utils/insights.js";
import { CheckCircle2, FileSearch, ShieldCheck } from "./Icon.js";

export function DecisionBrief({ answer }) {
  if (!answer) return <EmptyDecision />;

  const coverage = sourceCoverage(answer.citations);
  const tone = riskTone(answer.risk?.level);

  return (
    <section className="decision-brief">
      <div className="decision-topline">
        <div>
          <span className="section-kicker">Decision brief</span>
          <h2>{statusLabel(answer.compliance_status)}</h2>
        </div>
        <div className={`risk-badge ${tone}`}>
          <span>{answer.risk?.level || "unknown"}</span>
          <strong>{answer.risk?.score ?? 0}</strong>
        </div>
      </div>

      <div className="confidence-row">
        <div>
          <span>Source coverage</span>
          <strong>{coverage.policyCount} policies / {coverage.pageCount} pages</strong>
        </div>
        <div className="confidence-meter" aria-label="Evidence confidence">
          <i style={{ width: `${coverage.confidence}%` }} />
        </div>
      </div>

      <p className="answer-copy">{answer.answer}</p>

      <section className="recommendation-list">
        <h3>Action plan</h3>
        {answer.recommendations?.map((item, index) => (
          <div className="recommendation-item" key={`${item}-${index}`}>
            <CheckCircle2 size={17} />
            <span>{item}</span>
          </div>
        ))}
      </section>

      {answer.risk?.reasoning && (
        <section className="risk-note">
          <h3>Risk rationale</h3>
          <p>{answer.risk.reasoning}</p>
          {answer.risk.escalate && <b>Escalation recommended</b>}
        </section>
      )}
    </section>
  );
}

function EmptyDecision() {
  return (
    <section className="decision-brief empty-brief">
      <ShieldCheck size={44} />
      <h2>Ready for review</h2>
      <p>Choose a scenario or write a question. The assistant will return a decision, risk rationale, action plan, and cited policy evidence.</p>
      <div className="empty-hints">
        <span><FileSearch size={15} /> Hybrid retrieval</span>
        <span><ShieldCheck size={15} /> Agent review</span>
        <span><CheckCircle2 size={15} /> Cited guidance</span>
      </div>
    </section>
  );
}
