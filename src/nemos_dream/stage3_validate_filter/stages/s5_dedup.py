"""S5 — exact / fuzzy / semantic deduplication via NeMo Curator.

* ``ExactDuplicates`` — hash on ``ko_text``.
* ``FuzzyDuplicates`` — MinHashLSH, Jaccard ≥ 0.8 on k-gram shingles.
* ``SemanticDedup`` — cosine ≥ 0.92 on ``nvidia/nv-embedqa-e5-v5`` embeddings.
"""

from __future__ import annotations

from nemos_dream.schemas import Stage3Output
from nemos_dream.stage3_validate_filter.stages.base import Stage


class DedupStage(Stage):
    def run(self, records: list[Stage3Output]) -> list[Stage3Output]:
        raise NotImplementedError("stage 3 owner: implement")
