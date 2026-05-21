import React from "react";
import { formatPercent, riskLevelFromScore, riskTone, statusLabel } from "../utils/insights.js";
import { CheckCircle2, FileSearch, ShieldCheck } from "./Icon.js";

export function DecisionBrief({ answer }) {
  if (!answer) return <EmptyDecision />;

  const riskScore = answer.risk?.score ?? 0;
  const riskLevel = riskLevelFromScore(riskScore);
  const tone = riskTone(riskLevel);
  const contextPrecision = answer.context_precision;
  const contextPrecisionScore = contextPrecision?.score ?? 0;

  return (
    <section className="decision-brief">
      <div className="decision-topline">
        <div>
          <span className="section-kicker">Decision brief</span>
          <h2>{statusLabel(answer.compliance_status)}</h2>
        </div>
        <div className={`risk-badge ${tone}`}>
          <span>{riskLevel}</span>
          <strong>{riskScore}</strong>
        </div>
      </div>

      <section className="metric-explainer">
        <div>
          <span>Context precision</span>
          <strong>{formatPercent(contextPrecisionScore)}</strong>
        </div>
        <div className="confidence-meter" aria-label="Context precision">
          <i style={{ width: formatPercent(contextPrecisionScore) }} />
        </div>
        <p>
          {contextPrecision?.explanation ||
            "Context precision estimates how much of the retrieved policy context was relevant before the answer was generated."}
        </p>
        <small>
          {contextPrecision?.relevant_contexts ?? 0} of {contextPrecision?.total_contexts ?? 0} retrieved passages counted as relevant.
        </small>
      </section>

      <AnswerText text={answer.answer} />

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

function AnswerText({ text = "" }) {
  const lines = text.split(/\n+/).map((line) => line.trim()).filter(Boolean);

  if (!lines.length) return <p className="answer-copy">No answer was generated.</p>;

  return (
    <div className="answer-copy">
      {lines.map((line, index) => {
        const numbered = line.match(/^(\d+)\.\s+(.*)$/);
        return (
          <p className={numbered ? "answer-list-line" : undefined} key={`${line}-${index}`}>
            {numbered && <span>{numbered[1]}.</span>}
            <span>{renderInlineMarkdown(numbered ? numbered[2] : line)}</span>
          </p>
        );
      })}
    </div>
  );
}

function renderInlineMarkdown(text) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={`${part}-${index}`}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
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
