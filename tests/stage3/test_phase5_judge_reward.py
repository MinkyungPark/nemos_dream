"""Phase 5 judge + reward (async)."""

from __future__ import annotations

import pytest

from nemos_dream.schemas import Stage3Output
from nemos_dream.stage3_validate import phase5_judge_reward


def _to_stage3(s2):
    return Stage3Output(**s2.model_dump())


@pytest.mark.asyncio
async def test_apply_async_uses_deterministic_stub(stage2_row):
    row = _to_stage3(stage2_row)
    await phase5_judge_reward.apply_async([row])
    q = row.quality
    assert q.property_preservation is not None
    assert q.aggregate is not None
    assert q.reward is not None and "correctness" in q.reward
    assert q.judge_reasoning and "property_preservation" in q.judge_reasoning


@pytest.mark.asyncio
async def test_apply_async_enforces_axis_floor(stage2_row):
    row = _to_stage3(stage2_row)

    async def judge(_r):
        return {
            "property_preservation": 1,
            "naturalness": 4,
            "cultural_appropriateness": 4,
            "register_consistency": 4,
            "persona_style_consistency": 4,
            "reasoning": {},
        }

    async def reward(_r):
        return {"correctness": 0.5, "coherence": 0.5}

    await phase5_judge_reward.apply_async(
        [row], judge_fn=judge, reward_fn=reward, axis_floor=2
    )
    assert not row.valid
    assert any(rr.rule == "axis_floor" for rr in row.reject_reasons)


@pytest.mark.asyncio
async def test_apply_async_enforces_aggregate_floor(stage2_row):
    row = _to_stage3(stage2_row)

    async def judge(_r):
        return {
            "property_preservation": 2,
            "naturalness": 2,
            "cultural_appropriateness": 2,
            "register_consistency": 2,
            "persona_style_consistency": 2,
            "reasoning": {},
        }

    async def reward(_r):
        return {"correctness": 0.2}

    await phase5_judge_reward.apply_async(
        [row], judge_fn=judge, reward_fn=reward, aggregate_floor=3.0
    )
    assert not row.valid
    assert any(rr.rule == "aggregate_floor" for rr in row.reject_reasons)
