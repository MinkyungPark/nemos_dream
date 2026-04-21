"""S2 — rule-based filter.

Rules (from draft plan and ``../nemotron-test/README.md``):

* R1 Laughter consistency — ``laughter == 'none'`` ⇒ no ``ㅋ+/ㅎ+`` in ``ko_text``
* R2 Laughter intensity — table-driven length of ``ㅋ+`` matches ``intensity``
* R3 Register ↔ honorifics — intimate ⇒ ``-요/-습니다`` < 10 %; formal ⇒ ≥ 80 %
* R4 ASCII residue — ASCII ratio < 20 % (brand names excepted)
* R5 Cultural substitution applied — every ``mapped_refs[i].ko`` appears in ``ko_text``
* R6 Length bounds — 5 ≤ chars ≤ 1000; source-ratio ∈ [0.4, 2.5]
* R7 Emoji cap — formal ⇒ 0; casual ⇒ ≤ 5
"""

from __future__ import annotations

from nemos_dream.schemas import Stage3Output
from nemos_dream.stage3_validate_filter.stages.base import Stage


class RuleValidationStage(Stage):
    def run(self, records: list[Stage3Output]) -> list[Stage3Output]:
        raise NotImplementedError("stage 3 owner: implement")
