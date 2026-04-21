"""dataset_metrics.compute — absolute population metrics."""

from __future__ import annotations

from nemos_dream.schemas import RejectReason, RetryAction, Stage3Output
from nemos_dream.stage3_validate import dataset_metrics


def _to_stage3(s2, *, valid=True, rr=None, actions=None, reward=None):
    row = Stage3Output(**s2.model_dump())
    row.valid = valid
    if rr:
        row.reject_reasons = rr
    if actions:
        row.retry_actions = actions
    if reward:
        row.quality.reward = reward
    return row


def test_compute_basic_shape(stage2_row):
    accepted = [_to_stage3(stage2_row, reward={"correctness": 0.9})]
    rejected = [
        _to_stage3(
            stage2_row,
            valid=False,
            rr=[RejectReason(stage="stage3.phase2", rule="ascii_ratio", detail="x")],
            actions=[RetryAction(action="stage2_rewrite")],
        )
    ]
    metrics = dataset_metrics.compute(accepted, rejected)

    assert metrics["counts"]["accepted"] == 1
    assert metrics["counts"]["rejected"] == 1
    assert metrics["reward_distribution"]["correctness"]["mean"] == 0.9
    assert metrics["reject_breakdown"]["stage3.phase2:ascii_ratio"] == 1
    assert "stage2_rewrite" in metrics["retry_stats"]["action_counts"]


def test_compute_distinct_n(stage2_row):
    accepted = [_to_stage3(stage2_row)]
    metrics = dataset_metrics.compute(accepted, [])
    # Every distinct_n value lives in [0, 1]
    for k in ("1", "2", "3"):
        v = metrics["distinct_n"][k]
        assert 0.0 <= v <= 1.0


def test_compute_embedding_diversity_with_embed_fn(stage2_row):
    a = _to_stage3(stage2_row)
    b = _to_stage3(stage2_row)
    b.id = f"{a.id}-2"

    def embed(texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] if i % 2 == 0 else [0.0, 1.0] for i in range(len(texts))]

    metrics = dataset_metrics.compute([a, b], [], embed_fn=embed)
    assert metrics["embedding_diversity"]["source"] == "nv_embed"
    assert metrics["embedding_diversity"]["mean_pairwise_distance"] == 1.0


def test_compute_handles_empty_inputs():
    metrics = dataset_metrics.compute([], [])
    assert metrics["counts"] == {"accepted": 0, "rejected": 0, "total": 0}
    assert metrics["reward_distribution"] == {}
