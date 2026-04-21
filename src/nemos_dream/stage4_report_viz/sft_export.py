"""Export accepted :class:`Stage3Output` rows to the final SFT shape.

The emitted row must match ``data/reports/example_sft.json`` exactly:
``{messages: [system, user, assistant], metadata: {...}}`` — where the
assistant content is ``ko_text`` and the metadata echoes ``RewriteMeta`` plus
the four-axis quality scores.
"""

from __future__ import annotations

from nemos_dream.schemas import Stage3Output, Stage4Sft


def to_sft(row: Stage3Output) -> Stage4Sft:
    """Project a validated stage-3 row to the final SFT training row shape."""
    raise NotImplementedError("stage 4 owner: implement")
