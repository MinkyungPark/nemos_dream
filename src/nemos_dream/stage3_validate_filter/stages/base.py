"""Base class shared by every S1..S6 validator."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from nemos_dream.schemas import Stage3Output


@dataclass
class Stage(ABC):
    """One validator stage. Input and output are both :class:`Stage3Output`.

    The first stage (``s1_schema``) lifts a :class:`Stage2Output` into
    :class:`Stage3Output` by initialising empty ``quality`` + ``reject_reasons``.
    Each subsequent stage can:

    * mutate ``record.quality`` with its score,
    * call ``record.reject(...)`` to flip ``valid=False`` and append a reason,
    * short-circuit if ``record.valid`` is already ``False``.
    """

    name: str

    @abstractmethod
    def run(self, records: list[Stage3Output]) -> list[Stage3Output]:
        """Apply this stage to ``records`` and return the same list."""
        raise NotImplementedError("stage 3 owner: implement")
