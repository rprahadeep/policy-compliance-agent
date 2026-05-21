from typing import Any, Literal

from pydantic import BaseModel, Field


ComplianceStatus = Literal["compliant", "non_compliant", "needs_review", "unclear"]
RiskLevel = Literal["low", "medium", "high", "critical", "unknown"]


class QueryFilters(BaseModel):
    category: str | None = None
    framework: str | None = None
    policy_name: str | None = None

    def to_metadata_filter(self) -> dict[str, Any]:
        filters: dict[str, Any] = {}
        if self.category:
            filters["category"] = {"$eq": self.category}
        if self.framework:
            filters["framework"] = {"$eq": self.framework}
        if self.policy_name:
            filters["policy_name"] = {"$eq": self.policy_name}
        return filters


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    employee_context: str | None = Field(default=None, max_length=2000)
    filters: QueryFilters = Field(default_factory=QueryFilters)
    top_k: int = Field(default=5, ge=3, le=20)


class Citation(BaseModel):
    source_id: str
    policy_name: str
    page: int
    section: str | None = None
    category: str | None = None
    framework: str | None = None
    excerpt: str
    score: float | None = None


class RiskAssessment(BaseModel):
    level: RiskLevel = "unknown"
    score: int = Field(default=0, ge=0, le=100)
    reasoning: str
    escalate: bool = False


class ContextPrecisionMetric(BaseModel):
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    relevant_contexts: int = 0
    total_contexts: int = 0
    explanation: str = "Context precision estimates how much retrieved policy context was relevant to the question before answer generation."


class QueryResponse(BaseModel):
    answer: str
    compliance_status: ComplianceStatus
    risk: RiskAssessment
    recommendations: list[str]
    citations: list[Citation]
    agent_trace: dict[str, str]
    context_precision: ContextPrecisionMetric = Field(default_factory=ContextPrecisionMetric)
    token_usage: dict[str, int] = Field(default_factory=dict)


class IngestResponse(BaseModel):
    indexed_chunks: int
    policies: list[str]
    index_name: str
    local_store_path: str


class PolicyInfo(BaseModel):
    name: str
    path: str
    pages: int | None = None
    size_bytes: int
    category: str
    framework: str


class AnalyticsResponse(BaseModel):
    total_queries: int
    compliance_status_counts: dict[str, int]
    risk_level_counts: dict[str, int]
    top_topics: list[dict[str, Any]]
    recent_queries: list[dict[str, Any]]


class EvaluationCase(BaseModel):
    question: str
    expected_terms: list[str] = Field(default_factory=list)
    filters: QueryFilters = Field(default_factory=QueryFilters)


class EvaluationRequest(BaseModel):
    cases: list[EvaluationCase]


class EvaluationResult(BaseModel):
    question: str
    retrieved: int
    matched_terms: list[str]
    context_precision: float


class EvaluationResponse(BaseModel):
    average_context_precision: float
    results: list[EvaluationResult]


class LLMJudgeRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=2000)
    actual_output: str | None = Field(default=None, max_length=8000)
    expected_output: str | None = Field(default=None, max_length=8000)
    retrieval_context: list[str] = Field(default_factory=list)
    filters: QueryFilters = Field(default_factory=QueryFilters)
    top_k: int = Field(default=8, ge=3, le=20)
    generate_answer: bool = True
    metrics: list[str] = Field(
        default_factory=lambda: [
            "answer_relevancy",
            "faithfulness",
            "contextual_relevancy",
            "contextual_precision",
        ]
    )
    threshold: float = Field(default=0.7, ge=0.0, le=1.0)


class LLMJudgeMetricResult(BaseModel):
    name: str
    score: float | None = None
    passed: bool | None = None
    threshold: float
    reason: str
    skipped: bool = False


class LLMJudgeResponse(BaseModel):
    question: str
    actual_output: str
    evaluated_context_count: int
    overall_score: float
    passed: bool
    metrics: list[LLMJudgeMetricResult]
    generated_response: QueryResponse | None = None
