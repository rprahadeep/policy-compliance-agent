import React, { useEffect, useMemo, useState } from "react";
import { getAnalytics, getPolicies, ingestPolicies, queryCompliance } from "./api/client.js";
import { AppHeader } from "./components/AppHeader.jsx";
import { DecisionBrief } from "./components/DecisionBrief.jsx";
import { EvidencePanel } from "./components/EvidencePanel.jsx";
import { MetricStrip } from "./components/MetricStrip.jsx";
import { QueryComposer } from "./components/QueryComposer.jsx";
import { policyOptions } from "./utils/insights.js";

export function App() {
  const [question, setQuestion] = useState("Do privileged user accounts need multi-factor authentication before accessing company systems?");
  const [employeeContext, setEmployeeContext] = useState("Employee is requesting elevated access to an internal production administration console.");
  const [category, setCategory] = useState("");
  const [policies, setPolicies] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [answer, setAnswer] = useState(null);
  const [loading, setLoading] = useState(false);
  const [ingesting, setIngesting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    refresh();
  }, []);

  const categories = useMemo(() => policyOptions(policies), [policies]);

  async function refresh() {
    try {
      const [policyData, analyticsData] = await Promise.all([getPolicies(), getAnalytics()]);
      setPolicies(policyData);
      setAnalytics(analyticsData);
    } catch {
      setError("FastAPI is not reachable. Start the backend on port 8000.");
    }
  }

  async function handleIngest() {
    setError("");
    setIngesting(true);
    try {
      const data = await ingestPolicies();
      setAnswer({
        answer: `Policy index synchronized. ${data.indexed_chunks} chunks are now available in Pinecone across ${data.policies.length} source documents.`,
        compliance_status: "compliant",
        risk: { level: "low", score: 0, reasoning: "Document ingestion completed successfully.", escalate: false },
        recommendations: ["Run a compliance review.", "Filter by category when the scenario is narrow.", "Use the evidence panel to inspect cited clauses."],
        citations: [],
        agent_trace: {
          ingestion_pipeline: `Indexed into ${data.index_name}. Local chunk cache: ${data.local_store_path}.`,
        },
      });
      refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setIngesting(false);
    }
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await queryCompliance({
        question,
        employee_context: employeeContext || null,
        filters: { category: category || null },
        top_k: 8,
      });
      setAnswer(data);
      refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <AppHeader onIngest={handleIngest} ingesting={ingesting} />
      <MetricStrip policies={policies} analytics={analytics} answer={answer} />
      <section className="workbench">
        <QueryComposer
          question={question}
          setQuestion={setQuestion}
          employeeContext={employeeContext}
          setEmployeeContext={setEmployeeContext}
          category={category}
          setCategory={setCategory}
          categories={categories}
          loading={loading}
          error={error}
          onSubmit={handleSubmit}
        />
        <DecisionBrief answer={answer} />
        <EvidencePanel answer={answer} policies={policies} analytics={analytics} />
      </section>
    </main>
  );
}
