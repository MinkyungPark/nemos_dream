"""S1 — Pydantic validation + lift to :class:`Stage3Output`.

Also integrates ``nemo_curator.DocumentDataset`` for column-level type checks
(Dask/cuDF). Nested objects fall back to Pydantic.
"""

from __future__ import annotations

from nemos_dream.schemas import Stage3Output
from nemos_dream.stage3_validate_filter.stages.base import Stage


class SchemaValidationStage(Stage):
    def run(self, records: list[Stage3Output]) -> list[Stage3Output]:
        raise NotImplementedError("stage 3 owner: implement")
