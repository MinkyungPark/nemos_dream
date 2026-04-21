"""S6 — reward-model scoring for final ranking / top-N curation.

Uses ``nvidia/nemotron-4-340b-reward``. We weight ``correctness`` and
``coherence`` only — ``helpfulness`` is a context-free judgement that's biased
for an EN→KR rewriting task (see draft plan).
"""

from __future__ import annotations

from nemos_dream.schemas import Stage3Output
from nemos_dream.stage3_validate_filter.stages.base import Stage


class RewardStage(Stage):
    def run(self, records: list[Stage3Output]) -> list[Stage3Output]:
        raise NotImplementedError("stage 3 owner: implement")
