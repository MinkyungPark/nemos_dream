from __future__ import annotations

import pytest

from nemos_dream.stage3_validate_filter.stages.s2_rules import RuleValidationStage


@pytest.mark.xfail(reason="stage 3 stub", strict=False, raises=NotImplementedError)
def test_rules_accept_clean_row(stage3_row):
    stage = RuleValidationStage(name="s2_rules")
    out = stage.run([stage3_row])
    assert out[0].valid
