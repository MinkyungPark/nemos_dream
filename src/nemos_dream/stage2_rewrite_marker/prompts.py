"""Prompts for stage-2 Korean rewriting.

Populate ``REWRITE_PROMPT`` during implementation. Reference the template in
``draft_plan.md`` (section "3) 한국어로 재작성") — the prompt must:

* Forbid literal translation.
* Inject ``speech_act``, ``register``, ``emotion``, ``age_group``,
  ``target_platform``, and a rendered ``cultural_replacements`` table.
* Explicitly reserve marker-slot tokens (e.g. ``{LAUGH}``) for stage-2b.
"""

from __future__ import annotations

REWRITE_PROMPT: str = ""
"""Primary rewrite prompt. Populated during implementation."""

STYLE_FEW_SHOTS: dict[str, list[dict[str, str]]] = {}
"""Platform-specific few-shot examples keyed by ``target_platform``."""
