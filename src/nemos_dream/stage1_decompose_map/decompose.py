"""Stage 1a — English → :class:`schemas.Decomposed`.

Primary path: **NeMo Data Designer** (batch, Nemotron via NIM).
Fallback path: direct NIM ``chat.completions`` with ``nvext.guided_json``.

Both paths must return the same ``Decomposed`` shape. Fallback is sequential
and only fires when Data Designer fails or returns an empty batch.
"""

from __future__ import annotations

from collections.abc import Iterable

from nemos_dream.schemas import Decomposed, RawInput


def decompose_batch(rows: Iterable[RawInput]) -> list[Decomposed]:
    """Primary: NeMo Data Designer batch run over ``rows``.

    Raises a signalled exception (not a bare ``ValueError``) so the caller can
    transparently fall back to :func:`decompose_one`.
    """
    raise NotImplementedError("stage 1 owner: implement")


def decompose_one(row: RawInput) -> Decomposed:
    """Fallback: single-row NIM call with ``nvext.guided_json``.

    Includes normalisation of soft enum violations (see
    ``../nemo_dream_step1/src/part1_decompose/nim_guided_json.py`` for the
    reference alias maps and range clamps).
    """
    raise NotImplementedError("stage 1 owner: implement")
