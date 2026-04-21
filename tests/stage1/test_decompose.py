from __future__ import annotations

import pytest

from nemos_dream.stage1_decompose_map.decompose import decompose_one


@pytest.mark.xfail(reason="stage 1 stub", strict=False, raises=NotImplementedError)
def test_decompose_one_shape(raw_row):
    out = decompose_one(raw_row)
    assert out.source_text == raw_row.source_text
