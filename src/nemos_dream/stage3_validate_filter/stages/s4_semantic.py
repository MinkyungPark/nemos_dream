"""S4 — semantic validation.

Two signals combined:

* **Back-translation cosine** — translate ``ko_text`` → English, embed both the
  back-translation and the original ``source_text`` with NV-Embed, compute cosine.
* **LLM judge (4 axes)** — property preservation, naturalness, cultural
  appropriateness, register consistency. Judge backend selected via
  ``configs/stage3/judge/{mock,nim}.yaml``.
"""

from __future__ import annotations

from nemos_dream.schemas import Stage3Output
from nemos_dream.stage3_validate_filter.stages.base import Stage


class SemanticStage(Stage):
    def run(self, records: list[Stage3Output]) -> list[Stage3Output]:
        raise NotImplementedError("stage 3 owner: implement")
