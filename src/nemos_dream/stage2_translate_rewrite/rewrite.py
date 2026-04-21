"""Stage 2b — post-processing rewrite of the Korean draft.

Conditions on stage-1 metadata (``decomposed`` + ``mapped_refs``) and optional
``RewriteMeta`` targeting to produce the final Korean SNS post. This is where
cultural substitution, register, internet markers, persona flavour, etc. get
applied. The output must go into ``Stage2Output.ko_text``; the pre-rewrite
Korean draft goes into ``ko_text_draft``.

``RewriteMeta`` is open — feel free to extend it with additional metadata via
its ``extra`` field.
"""

from __future__ import annotations

from nemos_dream.schemas import RewriteMeta, Stage1Output


def rewrite(row: Stage1Output, ko_draft: str, target: RewriteMeta) -> str:
    """Return the final Korean SNS post for ``row``."""
    raise NotImplementedError("stage 2 owner: implement")
