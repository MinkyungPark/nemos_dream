"""Real tests — schema round-trip. Runs without any stage being implemented."""

from __future__ import annotations

from nemos_dream.schemas import Stage1Output, Stage2Output, Stage3Output


def test_stage1_round_trip(stage1_row):
    dumped = stage1_row.model_dump_json()
    assert Stage1Output.model_validate_json(dumped) == stage1_row


def test_stage2_round_trip(stage2_row):
    dumped = stage2_row.model_dump_json()
    assert Stage2Output.model_validate_json(dumped) == stage2_row


def test_stage3_round_trip(stage3_row):
    dumped = stage3_row.model_dump_json()
    assert Stage3Output.model_validate_json(dumped) == stage3_row


def test_stage_layering(stage3_row):
    """Stage 3 output must still satisfy every earlier stage's contract."""
    s1 = Stage1Output.model_validate(stage3_row.model_dump())
    s2 = Stage2Output.model_validate(stage3_row.model_dump())
    assert s1.id == s2.id == stage3_row.id
    assert s1.dialogue_decomposed == stage3_row.dialogue_decomposed
    assert s1.source_dialogue == stage3_row.source_dialogue
    # v4 canonical + v3 mirror — both must round-trip.
    assert s2.final_dialogue == stage3_row.final_dialogue
    assert s2.korean_dialogue == stage3_row.korean_dialogue
    assert s2.persona == stage3_row.persona
    assert s2.speaker_personas == stage3_row.speaker_personas


def test_stage2_mirrors_final_dialogue_to_korean_dialogue(stage2_row):
    """Populating only ``final_dialogue`` should backfill ``korean_dialogue``."""
    dumped = stage2_row.model_dump()
    dumped["korean_dialogue"] = []
    s2 = Stage2Output.model_validate(dumped)
    assert s2.korean_dialogue == s2.final_dialogue


def test_stage2_mirrors_korean_dialogue_to_final_dialogue(stage2_row):
    """Legacy writers that only set ``korean_dialogue`` must still populate the v4 field."""
    dumped = stage2_row.model_dump()
    dumped["final_dialogue"] = []
    dumped["step3_korean_dialogue"] = []
    s2 = Stage2Output.model_validate(dumped)
    assert s2.final_dialogue == s2.korean_dialogue
