from app.services.deepeval_judge import missing_requirements, normalize_metric_names


def test_normalize_metric_names_dedupes_and_converts_hyphens():
    assert normalize_metric_names(["Answer-Relevancy", "answer_relevancy", " faithfulness "]) == [
        "answer_relevancy",
        "faithfulness",
    ]


def test_missing_requirements_reports_context_and_expected_output():
    missing = missing_requirements({"retrieval_context", "expected_output"}, [], None)
    assert missing == ["retrieval_context", "expected_output"]
