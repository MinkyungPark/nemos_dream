from __future__ import annotations

import pytest

from nemos_dream.stage4_report_viz.metrics import aggregate_quality


@pytest.mark.xfail(reason="stage 4 stub", strict=False, raises=NotImplementedError)
def test_aggregate_quality_returns_mean(stage3_row):
    out = aggregate_quality([stage3_row])
    assert "naturalness" in out
