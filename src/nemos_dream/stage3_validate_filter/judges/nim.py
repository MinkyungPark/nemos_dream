"""Nemotron-70B judge via NIM — produces the 4-axis rubric scores."""

from __future__ import annotations

from typing import Any

from nemos_dream.schemas import Stage2Output


class NimJudge:
    async def score(self, row: Stage2Output) -> dict[str, Any]:
        raise NotImplementedError("stage 3 owner: implement")
