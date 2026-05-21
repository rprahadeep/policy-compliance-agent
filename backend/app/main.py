from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.models.schemas import (
    AnalyticsResponse,
    EvaluationRequest,
    EvaluationResponse,
    EvaluationResult,
    IngestResponse,
    LLMJudgeRequest,
    LLMJudgeResponse,
    PolicyInfo,
    QueryRequest,
    QueryResponse,
)
from app.services.agents import build_compliance_graph
from app.services.analytics import record_query, summarize_analytics
from app.services.deepeval_judge import require_openai_for_judge, run_llm_judge
from app.services.documents import chunk_policy_pages, count_pdf_pages, infer_category, list_policy_pdfs, load_policy_pages
from app.services.local_store import save_chunks
from app.services.pinecone_store import require_vector_config, upsert_chunks
from app.services.retrieval import hybrid_retrieve, to_citations


settings = get_settings()

app = FastAPI(
    title="Policy Compliance Intelligence Assistant",
    version="1.0.0",
    description="FastAPI service for policy RAG, LangGraph agent reasoning, and compliance risk guidance.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "model": settings.chat_model,
        "index": settings.pinecone_index_name,
        "langsmith": "enabled" if settings.langsmith_tracing else "disabled",
    }


@app.get("/api/v1/policies", response_model=list[PolicyInfo])
def list_policies() -> list[PolicyInfo]:
    policies = []
    for path in list_policy_pdfs(settings.policy_dir):
        policies.append(
            PolicyInfo(
                name=path.stem.replace("-", " "),
                path=str(path.relative_to(settings.base_dir)),
                pages=count_pdf_pages(path),
                size_bytes=path.stat().st_size,
                category=infer_category(path),
                framework="NIST",
            )
        )
    return policies


@app.post("/api/v1/ingest", response_model=IngestResponse)
def ingest() -> IngestResponse:
    try:
        require_vector_config(settings)
        pages = load_policy_pages(settings.policy_dir)
        chunks = chunk_policy_pages(pages)
        if not chunks:
            raise HTTPException(status_code=400, detail="No policy text was found to ingest.")
        indexed = upsert_chunks(settings, chunks)
        save_chunks(settings.local_store, chunks)
        return IngestResponse(
            indexed_chunks=indexed,
            policies=sorted({chunk.policy_name for chunk in chunks}),
            index_name=settings.pinecone_index_name,
            local_store_path=str(settings.local_store.relative_to(settings.base_dir)),
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/query", response_model=QueryResponse)
def query(request: QueryRequest) -> QueryResponse:
    try:
        require_vector_config(settings)
        response = execute_query(request)
        record_query(
            settings.analytics_file,
            request.question,
            response.compliance_status,
            response.risk.level,
            response.risk.score,
        )
        return response
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/v1/analytics", response_model=AnalyticsResponse)
def analytics() -> AnalyticsResponse:
    return AnalyticsResponse(**summarize_analytics(settings.analytics_file))


@app.post("/api/v1/evaluate/retrieval", response_model=EvaluationResponse)
def evaluate_retrieval(request: EvaluationRequest) -> EvaluationResponse:
    try:
        require_vector_config(settings)
        results = []
        for case in request.cases:
            chunks = hybrid_retrieve(settings, case.question, case.filters, top_k=8)
            context = " ".join(chunk.get("text", "").lower() for chunk in chunks)
            matched_terms = [term for term in case.expected_terms if term.lower() in context]
            precision = len(matched_terms) / len(case.expected_terms) if case.expected_terms else 0.0
            results.append(
                EvaluationResult(
                    question=case.question,
                    retrieved=len(chunks),
                    matched_terms=matched_terms,
                    context_precision=precision,
                )
            )
        average = sum(result.context_precision for result in results) / len(results) if results else 0.0
        return EvaluationResponse(average_context_precision=average, results=results)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/evaluate/llm-judge", response_model=LLMJudgeResponse)
def evaluate_llm_judge(request: LLMJudgeRequest) -> LLMJudgeResponse:
    try:
        generated_response = None
        actual_output = request.actual_output
        retrieval_context = request.retrieval_context

        if request.generate_answer and not actual_output:
            require_vector_config(settings)
            generated_response = execute_query(
                QueryRequest(
                    question=request.question,
                    filters=request.filters,
                    top_k=request.top_k,
                )
            )
            actual_output = generated_response.answer
            retrieval_context = [citation.excerpt for citation in generated_response.citations]
        elif not retrieval_context:
            require_vector_config(settings)
            chunks = hybrid_retrieve(settings, request.question, request.filters, top_k=request.top_k)
            retrieval_context = [chunk.get("text", "") for chunk in chunks if chunk.get("text")]
        else:
            require_openai_for_judge(settings)

        if not actual_output:
            raise HTTPException(
                status_code=400,
                detail="Provide actual_output or set generate_answer=true so the backend can generate an answer to judge.",
            )

        metric_results = run_llm_judge(
            settings=settings,
            question=request.question,
            actual_output=actual_output,
            retrieval_context=retrieval_context,
            expected_output=request.expected_output,
            metric_names=request.metrics,
            threshold=request.threshold,
        )
        scored = [result for result in metric_results if not result.skipped and result.score is not None]
        overall_score = sum(result.score for result in scored) / len(scored) if scored else 0.0
        return LLMJudgeResponse(
            question=request.question,
            actual_output=actual_output,
            evaluated_context_count=len(retrieval_context),
            overall_score=round(overall_score, 4),
            passed=bool(scored) and all(result.passed for result in scored),
            metrics=metric_results,
            generated_response=generated_response,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def execute_query(request: QueryRequest) -> QueryResponse:
    graph = build_compliance_graph(settings)
    state = graph.invoke(
        {
            "question": request.question,
            "employee_context": request.employee_context,
            "filters": request.filters,
            "top_k": request.top_k,
        }
    )
    return QueryResponse(
        answer=state["answer"],
        compliance_status=state["compliance_status"],
        risk=state["risk"],
        recommendations=state["recommendations"],
        citations=to_citations(state.get("retrieved_chunks", [])),
        agent_trace=state.get("agent_trace", {}),
        context_precision=state.get("context_precision", {}),
        token_usage=state.get("token_usage", {}),
    )
