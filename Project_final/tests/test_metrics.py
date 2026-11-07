from eval.metrics import (
    aggregate_match,
    bootstrap_score_ci,
    bootstrap_score_ci_pairs,
    score_from_counts,
    summarize_outcomes,
    wilson_interval,
)


def test_wilson_handles_empty_and_boundaries():
    assert wilson_interval(0, 0) == (0.0, 1.0)
    assert wilson_interval(0, 10)[0] == 0.0
    assert wilson_interval(10, 10)[1] == 1.0


def test_score_and_outcome_summary():
    assert score_from_counts(2, 1, 1) == 0.625
    summary = summarize_outcomes([1, 0, -1, 1])
    assert summary["wins"] == 2
    assert summary["draws"] == 1
    assert summary["losses"] == 1
    assert summary["score"] == 0.625


def test_bootstrap_is_reproducible_and_pair_aware():
    results = [1, -1, 1, -1]
    assert bootstrap_score_ci(results, n_boot=100, seed=7) == bootstrap_score_ci(
        results, n_boot=100, seed=7
    )
    assert bootstrap_score_ci_pairs([[1, -1], [1, 1]], n_boot=100, seed=7) == (
        0.5,
        1.0,
    )
    assert bootstrap_score_ci_pairs([], seed=7) == (0.0, 1.0)


def test_aggregate_match_uses_pair_bootstrap_and_cost_metrics():
    records = [
        {
            "a_is_black": True,
            "result_black": 1,
            "n_moves": 4,
            "seed": 0,
            "pair": 0,
            "move_log": [
                {"p": 1, "ms": 2.0, "stats": {"nodes": 10}},
                {"p": -1, "ms": 4.0, "stats": {"simulations": 20}},
            ],
        },
        {
            "a_is_black": False,
            "result_black": -1,
            "n_moves": 5,
            "seed": 0,
            "pair": 0,
            "move_log": [
                {"p": -1, "ms": 3.0, "stats": {"simulations": 30}},
                {"p": 1, "ms": 5.0, "stats": {"nodes": 12}},
            ],
        },
    ]
    result = aggregate_match(records, "a", "b")
    assert result["a_summary"]["score"] == 1.0
    assert result["latency"]["a"]["p95_ms"] == 2.95
    assert result["cost"]["a"]["nodes_mean"] == 10.0
    assert result["cost"]["b"]["simulations_mean"] == 20.0
    assert len(result["a_score_bootstrap_ci"]) == 2
