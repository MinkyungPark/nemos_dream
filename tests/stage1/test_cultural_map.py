from __future__ import annotations

import pytest

from nemos_dream.stage1_decompose_map.cultural_map import map_refs


@pytest.mark.xfail(reason="stage 1 stub", strict=False, raises=NotImplementedError)
def test_map_refs_preserves_count(stage1_row):
    mapped = map_refs(stage1_row.decomposed.cultural_refs)
    assert len(mapped) == len(stage1_row.decomposed.cultural_refs)
