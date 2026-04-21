"""Phase 4 intra-KR coherence."""

from __future__ import annotations

from nemos_dream.schemas import Stage3Output, Turn
from nemos_dream.stage3_validate import phase4_semantic


def _to_stage3(s2):
    return Stage3Output(**s2.model_dump())


def test_apply_populates_coherence_score(stage2_row):
    row = _to_stage3(stage2_row)
    phase4_semantic.apply([row])
    assert row.quality.intra_kr_coherence is not None
    assert row.quality.judge_reasoning["intra_kr_coherence_source"] == "char_jaccard_stub"


def test_apply_with_embed_fn_uses_nv_embed_source(stage2_row):
    row = _to_stage3(stage2_row)

    def embed(texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]  # all identical → cosine 1.0

    phase4_semantic.apply([row], embed_fn=embed, coherence_floor=0.5)
    assert row.quality.judge_reasoning["intra_kr_coherence_source"] == "nv_embed"
    assert row.quality.intra_kr_coherence == 1.0
    assert row.valid


def test_apply_rejects_below_floor(stage2_row):
    row = _to_stage3(stage2_row)

    def embed(texts: list[str]) -> list[list[float]]:
        # alternating orthogonal vectors → cosine 0.0 adjacent
        return [[1.0, 0.0] if i % 2 == 0 else [0.0, 1.0] for i in range(len(texts))]

    phase4_semantic.apply([row], embed_fn=embed, coherence_floor=0.5)
    assert not row.valid
    assert any(rr.rule == "intra_kr_coherence" for rr in row.reject_reasons)
