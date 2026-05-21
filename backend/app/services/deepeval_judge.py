import os
from collections.abc import Callable

from deepeval.metrics import (
    AnswerRelevancyMetric,
    ContextualPrecisionMetric,
    ContextualRecallMetric,
    ContextualRelevancyMetric,
    FaithfulnessMetric,
)
from deepeval.test_case import LLMTestCase

from app.core.config import Settings
from app.models.schemas import LLMJudgeMetricResult


MetricFactory = Callable[[float, str], object]


SUPPORTED_METRICS: dict[str, tuple[MetricFactory, set[str]]] = {
    "answer_relevancy": (lambda threshold, model: AnswerRelevancyMetric(threshold=threshold, model=model, async_mode=False), set()),
    "faithfulness": (lambda threshold, model: FaithfulnessMetric(threshold=threshold, model=model, async_mode=False), {"retrieval_context"}),
    "contextual_relevancy": (
        lambda threshold, model: ContextualRelevancyMetric(threshold=threshold, model=model, async_mode=False),
        {"retrieval_context"},
    ),
    "contextual_precision": (
        lambda threshold, model: ContextualPrecisionMetric(threshold=threshold, model=model, async_mode=False),
        {"retrieval_context", "expected_output"},
    ),
    "contextual_recall": (
        lambda threshold, model: ContextualRecallMetric(threshold=threshold, model=model, async_mode=False),
        {"retrieval_context", "expected_output"},
    ),
}


def require_openai_for_judge(settings: Settings) -> None:
    if not settings.openai_api_key:
        raise RuntimeError("Missing required environment variable: OPENAI_API_KEY")
    os.environ["OPENAI_API_KEY"] = settings.openai_api_key


def run_llm_judge(
    settings: Settings,
    question: str,
    actual_output: str,
    retrieval_context: list[str],
    expected_output: str | None,
    metric_names: list[str],
    threshold: float,
) -> list[LLMJudgeMetricResult]:
    require_openai_for_judge(settings)
    test_case = LLMTestCase(
        input=question,
        actual_output=actual_output,
        expected_output=expected_output,
        retrieval_context=retrieval_context or None,
    )

    results: list[LLMJudgeMetricResult] = []
    for name in normalize_metric_names(metric_names):
        if name not in SUPPORTED_METRICS:
            results.append(
                LLMJudgeMetricResult(
                    name=name,
                    threshold=threshold,
                    reason=f"Unsupported metric. Supported metrics: {', '.join(SUPPORTED_METRICS)}",
                    skipped=True,
                )
            )
            continue

        factory, required = SUPPORTED_METRICS[name]
        missing = missing_requirements(required, retrieval_context, expected_output)
        if missing:
            results.append(
                LLMJudgeMetricResult(
                    name=name,
                    threshold=threshold,
                    reason=f"Skipped because required input is missing: {', '.join(missing)}.",
                    skipped=True,
                )
            )
            continue

        try:
            metric = factory(threshold, settings.chat_model)
            score = float(metric.measure(test_case, _show_indicator=False))
            results.append(
                LLMJudgeMetricResult(
                    name=name,
                    score=round(score, 4),
                    passed=bool(getattr(metric, "success", score >= threshold)),
                    threshold=threshold,
                    reason=str(getattr(metric, "reason", "")) or "Metric completed.",
                )
            )
        except Exception as exc:
            results.append(
                LLMJudgeMetricResult(
                    name=name,
                    threshold=threshold,
                    reason=f"Metric failed: {exc}",
                    skipped=True,
                )
            )
    return results


def normalize_metric_names(metric_names: list[str]) -> list[str]:
    seen = set()
    normalized = []
    for metric in metric_names:
        name = metric.strip().lower().replace("-", "_")
        if name and name not in seen:
            seen.add(name)
            normalized.append(name)
    return normalized


def missing_requirements(required: set[str], retrieval_context: list[str], expected_output: str | None) -> list[str]:
    missing = []
    if "retrieval_context" in required and not retrieval_context:
        missing.append("retrieval_context")
    if "expected_output" in required and not expected_output:
        missing.append("expected_output")
    return missing
