from __future__ import annotations

import pytest

from nemos_dream.stage2_rewrite_marker.rewrite import rewrite


@pytest.mark.xfail(reason="stage 2 stub", strict=False, raises=NotImplementedError)
def test_rewrite_returns_nonempty(stage1_row):
    from nemos_dream.schemas import RewriteMeta

    target = RewriteMeta(target_platform="twitter", target_age_group="20s")
    out = rewrite(stage1_row, target)
    assert isinstance(out, str) and out
