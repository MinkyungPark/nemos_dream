"""Prompts for stage-1 sociolinguistic decomposition.

Fill in when implementing. The system prompt should ground the LLM in the
``Decomposed`` schema (see ``schemas.py``) and make it refuse to invent
``cultural_refs`` that aren't verbatim spans of the source text.
"""

from __future__ import annotations

SYSTEM_PROMPT: str = ""
"""Primary system prompt for decomposition. Populated during implementation."""

FEW_SHOT_EXAMPLES: list[dict[str, str]] = []
"""Optional few-shot examples (user/assistant pairs) for the Data Designer config."""
