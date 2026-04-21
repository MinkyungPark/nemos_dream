"""Stage 2a — Korean rewriting conditioned on stage-1 metadata."""

from __future__ import annotations

from nemos_dream.schemas import RewriteMeta, Stage1Output


def rewrite(row: Stage1Output, target: RewriteMeta) -> str:
    """Return the pre-marker Korean body text for ``row`` under ``target``."""
    raise NotImplementedError("stage 2 owner: implement")
