from __future__ import annotations

import pytest

from nemos_dream.stage3_validate_filter.judges.mock import MockJudge


@pytest.mark.xfail(reason="stage 3 stub", strict=False, raises=NotImplementedError)
async def test_mock_judge_returns_four_axes(stage2_row):
    judge = MockJudge()
    score = await judge.score(stage2_row)
    for axis in (
        "property_preservation",
        "naturalness",
        "cultural_appropriateness",
        "register_consistency",
    ):
        assert axis in score
