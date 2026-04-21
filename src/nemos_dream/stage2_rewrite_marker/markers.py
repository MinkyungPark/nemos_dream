"""Stage 2b — rule-based internet-marker injection.

Reads ``configs/stage2/laughter_map.json`` (maps ``(laughter, intensity)`` →
Korean token) and the row's ``InternetMarkers`` to decide:

* where to splice ``ㅋㅋ``, ``ㅎㅎ``, ``ㅠㅠ``
* whether to add CAPS-equivalent emphasis (e.g. repeated consonant tail)
* emoji injection budgets by ``register``

This module must be pure (no LLM calls) so stage 2 remains reproducible.
"""

from __future__ import annotations

from nemos_dream.schemas import InternetMarkers


def inject_markers(ko_text: str, markers: InternetMarkers, *, intensity: int) -> str:
    """Return ``ko_text`` with markers spliced in per the rule table."""
    raise NotImplementedError("stage 2 owner: implement")
