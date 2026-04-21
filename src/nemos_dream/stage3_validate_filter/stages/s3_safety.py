"""S3 — safety + PII rails.

* Content safety: ``nvidia/llama-3.1-nemoguard-8b-content-safety`` via NIM.
* Jailbreak: ``nemoguard-jailbreak-detect`` (run over the ORIGINAL English seed,
  not the Korean rewrite).
* PII: Presidio regex (KR_RRN, KR_PHONE, CARD) on ``ko_text``.
"""

from __future__ import annotations

from nemos_dream.schemas import Stage3Output
from nemos_dream.stage3_validate_filter.stages.base import Stage


class SafetyStage(Stage):
    def run(self, records: list[Stage3Output]) -> list[Stage3Output]:
        raise NotImplementedError("stage 3 owner: implement")
