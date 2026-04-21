"""Phase 2 hard-gate rules."""

from __future__ import annotations

from nemos_dream.schemas import (
    Persona,
    PersonaEntry,
    RejectReason,
    RetrievedPersona,
    Stage3Output,
    Turn,
)
from nemos_dream.stage3_validate import phase2_rules


def _to_stage3(s2):
    return Stage3Output(**s2.model_dump())


def test_turn_count_parity_passes_when_aligned(stage2_row):
    row = _to_stage3(stage2_row)
    assert phase2_rules.turn_count_parity(row, {}) is None


def test_turn_count_parity_flags_mismatch(stage2_row):
    stage2_row.korean_dialogue = stage2_row.korean_dialogue[:-1]
    row = _to_stage3(stage2_row)
    rr = phase2_rules.turn_count_parity(row, {})
    assert isinstance(rr, RejectReason)
    assert rr.rule == "turn_count_parity"


def test_turn_index_order_flags_out_of_order(stage2_row):
    stage2_row.korean_dialogue[1] = Turn(
        index=9, speaker=stage2_row.korean_dialogue[1].speaker, text="x"
    )
    row = _to_stage3(stage2_row)
    rr = phase2_rules.turn_index_order(row, {})
    assert rr is not None and rr.rule == "turn_index_order"


def test_speaker_ref_integrity_flags_unknown_v4_persona(stage2_row):
    stage2_row.persona.append(
        PersonaEntry(
            speaker_index=99,
            speaker_name_en="__nobody__",
            retrieved_persona=RetrievedPersona(name="아무개", age=30),
            source_speaker_profile=stage2_row.speakers[0],
        )
    )
    row = _to_stage3(stage2_row)
    rr = phase2_rules.speaker_ref_integrity(row, {})
    assert rr is not None and rr.rule == "speaker_ref_integrity"


def test_speaker_ref_integrity_v3_fallback(stage2_row):
    # Clear v4 persona so the rule falls through to the v3 branch.
    stage2_row.persona = []
    stage2_row.speaker_personas.append(
        Persona(speaker_ref="__nobody__", gender="unknown", age="unknown")
    )
    row = _to_stage3(stage2_row)
    rr = phase2_rules.speaker_ref_integrity(row, {})
    assert rr is not None and rr.rule == "speaker_ref_integrity"


def test_ascii_ratio_allows_korean(stage2_row):
    row = _to_stage3(stage2_row)
    assert phase2_rules.ascii_ratio(row, {"ascii_ratio_max": 0.40}) is None


def test_ascii_ratio_flags_english_heavy(stage2_row):
    stage2_row.korean_dialogue = [
        Turn(index=i, speaker=t.speaker, text="this is mostly english text here")
        for i, t in enumerate(stage2_row.korean_dialogue)
    ]
    row = _to_stage3(stage2_row)
    rr = phase2_rules.ascii_ratio(row, {"ascii_ratio_max": 0.40})
    assert rr is not None and rr.rule == "ascii_ratio"


def test_mapped_ref_surface_requires_ko_in_kr(stage2_row):
    stage2_row.korean_dialogue = [
        Turn(index=i, speaker=t.speaker, text="모두 한글이지만 매핑된 단어는 없습니다.")
        for i, t in enumerate(stage2_row.korean_dialogue)
    ]
    row = _to_stage3(stage2_row)
    rr = phase2_rules.mapped_ref_surface(row, {})
    assert rr is not None and rr.rule == "mapped_ref_surface"


def test_apply_stops_at_first_fail(stage2_row):
    stage2_row.korean_dialogue = stage2_row.korean_dialogue[:-1]  # turn_count fails first
    row = _to_stage3(stage2_row)
    phase2_rules.apply([row], {})
    assert not row.valid
    # One reject per phase (short-circuit after first)
    assert len(row.reject_reasons) == 1
