import React from "react";
import { CONTEXT_PRESETS, QUESTION_TEMPLATES } from "../data/templates.js";
import { ArrowRight, Loader2, Search, Sparkles } from "./Icon.js";

export function QueryComposer({
  question,
  setQuestion,
  employeeContext,
  setEmployeeContext,
  category,
  setCategory,
  categories,
  loading,
  error,
  onSubmit,
}) {
  function applyTemplate(template) {
    setQuestion(template.question);
    setEmployeeContext(template.context);
    setCategory(categories.includes(template.category) ? template.category : "");
  }

  function addContext(preset) {
    setEmployeeContext((current) => {
      if (!current) return preset;
      if (current.includes(preset)) return current;
      return `${current}; ${preset}`;
    });
  }

  return (
    <section className="command-panel">
      <div className="panel-title">
        <div>
          <span>Ask</span>
          <h2>Analyze an action</h2>
        </div>
        <Sparkles size={18} />
      </div>

      <div className="template-grid">
        {QUESTION_TEMPLATES.map((template) => (
          <button className="template-card" type="button" key={template.title} onClick={() => applyTemplate(template)}>
            <span>{template.title}</span>
            <ArrowRight size={15} />
          </button>
        ))}
      </div>

      <form className="query-form" onSubmit={onSubmit}>
        <label>
          Compliance question
          <textarea value={question} onChange={(event) => setQuestion(event.target.value)} rows={6} />
        </label>

        <label>
          Scenario context
          <textarea
            value={employeeContext}
            onChange={(event) => setEmployeeContext(event.target.value)}
            rows={3}
            placeholder="Role, data type, urgency, vendor, access level..."
          />
        </label>

        <div className="context-chips">
          {CONTEXT_PRESETS.map((preset) => (
            <button key={preset} type="button" onClick={() => addContext(preset)}>
              {preset}
            </button>
          ))}
        </div>

        <label>
          Retrieval scope
          <select value={category} onChange={(event) => setCategory(event.target.value)}>
            <option value="">All policy categories</option>
            {categories.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>

        <button className="button button-primary" disabled={loading || !question.trim()}>
          {loading ? <Loader2 className="spin" size={18} /> : <Search size={18} />}
          Run compliance review
        </button>
        {error && <div className="error-box">{error}</div>}
      </form>
    </section>
  );
}
