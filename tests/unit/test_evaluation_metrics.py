from evaluation.metrics import ranking_metrics


def test_ranking_metrics_exclude_questions_without_expected_retrievals():
    metrics = ranking_metrics([], [])
    assert metrics == {
        "recall_at_k": None,
        "precision_at_k": None,
        "mrr": None,
        "ndcg": None,
    }


def test_ranking_metrics_calculate_relevant_rank():
    metrics = ranking_metrics([{"chunk_id": "wrong"}, {"chunk_id": "expected"}], ["expected"], k=2)
    assert metrics["recall_at_k"] == 1.0
    assert metrics["precision_at_k"] == 0.5
    assert metrics["mrr"] == 0.5
