import json
from typing import Any, TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from app.core.config import Settings
from app.models.schemas import ContextPrecisionMetric, QueryFilters, RiskAssessment
from app.services.guardrails import validate_policy_question
from app.services.retrieval import hybrid_retrieve, to_citations


class ComplianceState(TypedDict, total=False):
    question: str
    employee_context: str | None
    filters: QueryFilters
    top_k: int
    valid: bool
    guardrail_message: str
    retrieved_chunks: list[dict[str, Any]]
    interpretation: str
    compliance_status: str
    compliance_reasoning: str
    risk: dict[str, Any]
    recommendations: list[str]
    answer: str
    agent_trace: dict[str, str]
    token_usage: dict[str, int]
    context_precision: dict[str, Any]


def build_compliance_graph(settings: Settings):
    llm = ChatOpenAI(model=settings.chat_model, temperature=0.1, api_key=settings.openai_api_key, max_tokens=900, timeout=45)

    def validate_node(state: ComplianceState) -> ComplianceState:
        valid, message = validate_policy_question(state["question"])
        return {"valid": valid, "guardrail_message": message, "agent_trace": {"guardrails": message}}

    def retrieve_node(state: ComplianceState) -> ComplianceState:
        chunks = hybrid_retrieve(settings, state["question"], state["filters"], state["top_k"])
        context_precision = calculate_context_precision(state["question"], chunks)
        trace = state.get("agent_trace", {})
        trace["policy_retrieval_agent"] = (
            f"Retrieved {len(chunks)} policy chunks using hybrid search. "
            f"Estimated context precision: {context_precision.score:.0%}."
        )
        return {"retrieved_chunks": chunks, "context_precision": context_precision.model_dump(), "agent_trace": trace}

    def interpretation_node(state: ComplianceState) -> ComplianceState:
        context = format_context(state["retrieved_chunks"])
        response = llm.invoke(
            [
                (
                    "system",
                    "You are a Policy Interpretation Agent. Explain only what the cited policy context supports. "
                    "Be precise, plain-language, avoid adding external facts, and do not use markdown formatting.",
                ),
                (
                    "human",
                    f"Question: {state['question']}\nEmployee context: {state.get('employee_context') or 'None'}\n\nPolicy context:\n{context}",
                ),
            ]
        )
        trace = state.get("agent_trace", {})
        trace["policy_interpretation_agent"] = strip_markdown(response.content[:800])
        return {"interpretation": strip_markdown(response.content), "agent_trace": trace}

    def compliance_node(state: ComplianceState) -> ComplianceState:
        response = llm.invoke(
            [
                (
                    "system",
                    "You are a Compliance Checker Agent. Return strict JSON with keys status and reasoning. "
                    "status must be one of compliant, non_compliant, needs_review, unclear. "
                    "Do not use markdown formatting.",
                ),
                (
                    "human",
                    f"Question: {state['question']}\nInterpretation:\n{state['interpretation']}\n\nDecide whether the requested action is compliant.",
                ),
            ]
        )
        parsed = parse_json(response.content, {"status": "unclear", "reasoning": response.content})
        trace = state.get("agent_trace", {})
        trace["compliance_checker_agent"] = strip_markdown(str(parsed.get("reasoning", "")))
        return {
            "compliance_status": normalize_status(parsed.get("status")),
            "compliance_reasoning": strip_markdown(str(parsed.get("reasoning", ""))),
            "agent_trace": trace,
        }

    def risk_node(state: ComplianceState) -> ComplianceState:
        response = llm.invoke(
            [
                (
                    "system",
                    "You are a Risk Assessment Agent. Return strict JSON with keys level, score, reasoning, escalate. "
                    "level is low, medium, high, critical, or unknown. score is 0-100. "
                    "Do not use markdown formatting.",
                ),
                (
                    "human",
                    f"Question: {state['question']}\nStatus: {state['compliance_status']}\nReasoning: {state['compliance_reasoning']}",
                ),
            ]
        )
        parsed = parse_json(
            response.content,
            {"level": "unknown", "score": 50, "reasoning": response.content, "escalate": True},
        )
        score = coerce_score(parsed.get("score", 50))
        risk = RiskAssessment(
            level=risk_level_from_score(score),
            score=score,
            reasoning=strip_markdown(str(parsed.get("reasoning", ""))),
            escalate=bool(parsed.get("escalate", False)),
        ).model_dump()
        trace = state.get("agent_trace", {})
        trace["risk_assessment_agent"] = risk["reasoning"]
        return {"risk": risk, "agent_trace": trace}

    def recommendation_node(state: ComplianceState) -> ComplianceState:
        response = llm.invoke(
            [
                (
                    "system",
                    "You are a Recommendation Agent. Return strict JSON with key recommendations containing 3 to 5 short strings. "
                    "Do not use markdown formatting.",
                ),
                (
                    "human",
                    f"Question: {state['question']}\nStatus: {state['compliance_status']}\nRisk: {state['risk']}\nInterpretation: {state['interpretation']}",
                ),
            ]
        )
        parsed = parse_json(response.content, {"recommendations": [response.content]})
        recommendations = [strip_markdown(str(item)) for item in (parsed.get("recommendations") or [])]
        trace = state.get("agent_trace", {})
        trace["recommendation_agent"] = "; ".join(recommendations[:5])
        return {"recommendations": recommendations[:5], "agent_trace": trace}

    def answer_node(state: ComplianceState) -> ComplianceState:
        citations = to_citations(state["retrieved_chunks"])
        citation_lines = "\n".join(
            f"- {citation.policy_name}, page {citation.page}, section {citation.section or 'n/a'}"
            for citation in citations[:6]
        )
        response = llm.invoke(
            [
                (
                    "system",
                    "You are the final Compliance Assistant. Produce a concise answer grounded in cited policies. "
                    "Mention when human review or escalation is needed. Do not use markdown formatting.",
                ),
                (
                    "human",
                    f"Question: {state['question']}\nInterpretation: {state['interpretation']}\n"
                    f"Compliance status: {state['compliance_status']}\nRisk: {state['risk']}\n"
                    f"Recommendations: {state['recommendations']}\nSources:\n{citation_lines}",
                ),
            ]
        )
        trace = state.get("agent_trace", {})
        trace["final_response_agent"] = "Generated grounded answer with citations."
        return {"answer": strip_markdown(response.content), "agent_trace": trace}

    def blocked_node(state: ComplianceState) -> ComplianceState:
        trace = state.get("agent_trace", {})
        trace["final_response_agent"] = "Blocked by input guardrails."
        return {
            "answer": state["guardrail_message"],
            "compliance_status": "unclear",
            "risk": RiskAssessment(level="unknown", score=0, reasoning="Question was not accepted by guardrails.").model_dump(),
            "recommendations": ["Rephrase the question as a policy or compliance scenario."],
            "retrieved_chunks": [],
            "context_precision": ContextPrecisionMetric().model_dump(),
            "agent_trace": trace,
        }

    def route_after_validation(state: ComplianceState) -> str:
        return "retrieve_policy" if state.get("valid") else "blocked_response"

    graph = StateGraph(ComplianceState)
    graph.add_node("validate_input", validate_node)
    graph.add_node("retrieve_policy", retrieve_node)
    graph.add_node("interpret_policy", interpretation_node)
    graph.add_node("check_compliance", compliance_node)
    graph.add_node("assess_risk", risk_node)
    graph.add_node("recommend_actions", recommendation_node)
    graph.add_node("compose_answer", answer_node)
    graph.add_node("blocked_response", blocked_node)
    graph.set_entry_point("validate_input")
    graph.add_conditional_edges(
        "validate_input",
        route_after_validation,
        {"retrieve_policy": "retrieve_policy", "blocked_response": "blocked_response"},
    )
    graph.add_edge("retrieve_policy", "interpret_policy")
    graph.add_edge("interpret_policy", "check_compliance")
    graph.add_edge("check_compliance", "assess_risk")
    graph.add_edge("assess_risk", "recommend_actions")
    graph.add_edge("recommend_actions", "compose_answer")
    graph.add_edge("compose_answer", END)
    graph.add_edge("blocked_response", END)
    return graph.compile()


def format_context(chunks: list[dict[str, Any]]) -> str:
    lines = []
    for idx, chunk in enumerate(chunks, start=1):
        lines.append(
            f"[{idx}] {chunk.get('policy_name')} | page {chunk.get('page')} | "
            f"{chunk.get('section') or 'n/a'}\n{chunk.get('text', '')[:1000]}"
        )
    return "\n\n".join(lines)


def strip_markdown(text: str) -> str:
    return (
        text.replace("**", "")
        .replace("__", "")
        .replace("`", "")
        .replace("###", "")
        .replace("##", "")
        .replace("#", "")
        .strip()
    )


def coerce_score(value: Any) -> int:
    try:
        return max(0, min(100, int(value)))
    except (TypeError, ValueError):
        digits = "".join(char for char in str(value) if char.isdigit())
        return max(0, min(100, int(digits or 50)))


def risk_level_from_score(score: int) -> str:
    if score >= 76:
        return "critical"
    if score >= 51:
        return "high"
    if score >= 26:
        return "medium"
    return "low"


def calculate_context_precision(question: str, chunks: list[dict[str, Any]]) -> ContextPrecisionMetric:
    if not chunks:
        return ContextPrecisionMetric()

    question_terms = {
        term.strip(".,:;!?()[]{}\"'").lower()
        for term in question.split()
        if len(term.strip(".,:;!?()[]{}\"'")) >= 4
    }
    scored = []
    for chunk in chunks:
        text = str(chunk.get("text", "")).lower()
        overlap = sum(1 for term in question_terms if term in text)
        retrieval_score = float(chunk.get("score") or 0)
        scored.append(overlap >= 2 or retrieval_score >= 0.65)

    relevant = sum(1 for item in scored if item)
    score = relevant / len(chunks)
    return ContextPrecisionMetric(
        score=round(score, 4),
        relevant_contexts=relevant,
        total_contexts=len(chunks),
        explanation=(
            "Context precision estimates the share of retrieved policy passages that were relevant enough "
            "to support the answer. Higher scores mean the model received cleaner, less noisy context."
        ),
    )


def parse_json(text: str, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end >= start:
            return json.loads(text[start : end + 1])
        return json.loads(text)
    except Exception:
        return fallback


def normalize_status(status: Any) -> str:
    value = str(status or "unclear").lower()
    return value if value in {"compliant", "non_compliant", "needs_review", "unclear"} else "unclear"


def normalize_risk(level: Any) -> str:
    value = str(level or "unknown").lower()
    return value if value in {"low", "medium", "high", "critical", "unknown"} else "unknown"
