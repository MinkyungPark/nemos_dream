from __future__ import annotations

import pytest

from nemos_dream.schemas import InternetMarkers
from nemos_dream.stage2_rewrite_marker.markers import inject_markers


@pytest.mark.xfail(reason="stage 2 stub", strict=False, raises=NotImplementedError)
def test_inject_markers_no_laughter():
    markers = InternetMarkers(laughter="none", emphasis=[], sarcasm_marker=False)
    out = inject_markers("오늘 날씨 좋다", markers, intensity=1)
    assert "ㅋ" not in out and "ㅎ" not in out


@pytest.mark.xfail(reason="stage 2 stub", strict=False, raises=NotImplementedError)
def test_inject_markers_laughter_intensity_scales():
    low = InternetMarkers(laughter="lol", emphasis=[], sarcasm_marker=False)
    high = InternetMarkers(laughter="rofl", emphasis=[], sarcasm_marker=False)
    lo_out = inject_markers("웃기다", low, intensity=1)
    hi_out = inject_markers("웃기다", high, intensity=5)
    assert lo_out.count("ㅋ") < hi_out.count("ㅋ")
