from __future__ import annotations

import pytest

from nemos_dream.stage4_report_viz.sft_export import to_sft


@pytest.mark.xfail(reason="stage 4 stub", strict=False, raises=NotImplementedError)
def test_sft_shape(stage3_row):
    sft = to_sft(stage3_row)
    roles = [m.role for m in sft.messages]
    assert roles == ["system", "user", "assistant"]
    assert sft.metadata.target_platform == stage3_row.rewrite_meta.target_platform
