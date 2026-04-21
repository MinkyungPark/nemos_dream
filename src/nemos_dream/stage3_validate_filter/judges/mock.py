"""Deterministic mock judge — returns hardcoded scores, no network."""

from __future__ import annotations

from typing import Any

from nemos_dream.schemas import Stage2Output


class MockJudge:
    async def score(self, row: Stage2Output) -> dict[str, Any]:
        raise NotImplementedError("stage 3 owner: implement")
