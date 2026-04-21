"""Phase 3 safety + PII guardrails."""

from __future__ import annotations

from nemos_dream.schemas import Stage3Output, Turn
from nemos_dream.stage3_validate import phase3_guardrails


def _to_stage3(s2):
    return Stage3Output(**s2.model_dump())


def test_local_pii_pass_ok():
    assert phase3_guardrails.local_pii_pass("안녕하세요 반갑습니다")


def test_local_pii_pass_flags_email():
    assert not phase3_guardrails.local_pii_pass("보내줘 foo@bar.com 으로")


def test_local_pii_pass_flags_kr_phone():
    assert not phase3_guardrails.local_pii_pass("제 번호는 010-1234-5678 입니다")


def test_apply_populates_quality_flags_even_when_already_invalid(stage2_row):
    row = _to_stage3(stage2_row)
    row.valid = False  # simulate prior phase reject
    phase3_guardrails.apply([row])
    # Flags were still populated for metric visibility
    assert row.quality.safety_pass is True
    assert row.quality.pii_pass is True


def test_apply_flips_valid_on_pii(stage2_row):
    stage2_row.korean_dialogue = [
        Turn(index=0, speaker="x", text="이메일은 foo@bar.com 이야")
    ]
    stage2_row.source_dialogue = [stage2_row.source_dialogue[0]]
    row = _to_stage3(stage2_row)
    phase3_guardrails.apply([row])
    assert not row.valid
    assert any(rr.rule == "pii" for rr in row.reject_reasons)


def test_apply_flips_valid_on_safety(stage2_row):
    row = _to_stage3(stage2_row)
    phase3_guardrails.apply([row], safety_fn=lambda _t: False)
    assert not row.valid
    assert any(rr.rule == "safety" for rr in row.reject_reasons)
