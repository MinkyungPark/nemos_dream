"""Judge protocol — shared interface for mock + NIM implementations.

Both judges must return the same dict shape so ``s4_semantic`` can swap
backends via Hydra config. See ``../nemotron-test/pipeline/judges/protocol.py``
for the reference contract.
"""

from __future__ import annotations

from typing import Any, Protocol

from nemos_dream.schemas import Stage2Output


class Judge(Protocol):
    """All judge implementations conform to this async protocol."""

    async def score(self, row: Stage2Output) -> dict[str, Any]:
        """Return the four-axis rubric score plus ``issues`` + ``suggested_fix``."""
        ...
