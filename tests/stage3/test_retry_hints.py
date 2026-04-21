"""retry_hints mapping logic."""

from __future__ import annotations

from nemos_dream.schemas import RejectReason, Stage3Output
from nemos_dream.stage3_validate import retry_hints


def _to_stage3(s2):
    return Stage3Output(**s2.model_dump())


def test_no_actions_for_clean_row(stage2_row):
    row = _to_stage3(stage2_row)
    assert retry_hints.derive(row) == []


def test_safety_reject_hard_stops(stage2_row):
    row = _to_stage3(stage2_row)
    row.valid = False
    row.reject_reasons.append(
        RejectReason(stage="stage3.phase3", rule="safety", detail="x")
    )
    actions = retry_hints.derive(row)
    assert len(actions) == 1 and actions[0].action == "none"


def test_dup_reject_drops(stage2_row):
    row = _to_stage3(stage2_row)
    row.valid = False
    row.reject_reasons.append(
        RejectReason(stage="stage3.phase1", rule="near_dup", detail="x")
    )
    actions = retry_hints.derive(row)
    assert len(actions) == 1 and actions[0].action == "none"


def test_turn_count_triggers_stage1_redecompose(stage2_row):
    row = _to_stage3(stage2_row)
    row.valid = False
    row.reject_reasons.append(
        RejectReason(stage="stage3.phase2", rule="turn_count_parity", detail="x")
    )
    actions = retry_hints.derive(row)
    assert any(a.action == "stage1_redecompose" for a in actions)


def test_mapped_ref_missing_triggers_websearch_cultural(stage2_row):
    row = _to_stage3(stage2_row)
    row.valid = False
    row.reject_reasons.append(
        RejectReason(stage="stage3.phase2", rule="mapped_ref_surface", detail="x")
    )
    actions = retry_hints.derive(row)
    kinds = {a.action for a in actions}
    assert "websearch_cultural" in kinds
    assert "maps_ref_redo" in kinds


def test_low_naturalness_triggers_stage2_rewrite(stage2_row):
    row = _to_stage3(stage2_row)
    row.valid = False
    row.reject_reasons.append(
        RejectReason(stage="stage3.phase4", rule="intra_kr_coherence", detail="x")
    )
    row.quality.naturalness = 1
    actions = retry_hints.derive(row)
    kinds = {a.action for a in actions}
    assert "stage2_rewrite" in kinds


def test_apply_sets_retry_actions(stage2_row):
    row = _to_stage3(stage2_row)
    retry_hints.apply([row])
    assert row.retry_actions == []
