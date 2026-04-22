"""Phase 6 — NAT-tool-driven self-verify + modify loop.

Stage 3 runner produces ``retry_queue`` rows annotated with
``retry_actions`` (derived from ``reject_reasons`` in ``retry_hints.py``).
This module consumes that queue and repairs each row using real
stage-1 / stage-2 adapters wrapped as NeMo Agent Toolkit (NAT) tools.

The original ReAct agent loop was replaced with a simpler, deterministic
driver: each row's ``retry_actions`` tell us exactly which repair tools
to invoke, and we call them in order — then call ``revalidate`` — until
the row is valid or the action list is exhausted. NAT still owns the
tool abstraction (``StructuredTool`` / ``BaseTool`` — the same primitive
NAT agents consume), and each tool is a real stage adapter wired through
:class:`StageCallables`. There is no offline fallback.

Why the simplification: running the full ReAct loop on a 120B model for
one dialogue row costs 20-40s per retry cycle, and its text-parse
dispatch (``Action:`` / ``Action Input:``) is brittle against
Nemotron's occasional tool-name hallucinations. ``retry_actions`` are
already the right repair hints — the "agent" intelligence lives in
``retry_hints.derive``. Letting an LLM re-derive them in a ReAct loop
was doing the same work twice with more failure modes.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from nemos_dream.schemas import Stage3Output

logger = logging.getLogger(__name__)


@dataclass
class StageCallables:
    """Repair-tool adapter bundle wired by the orchestrator.

    Every callable must be a *real* implementation — phase 6 does not
    support stubs. See ``self_verify_runner.build_stage_callables``.
    """

    stage1_redecompose: Callable[[Stage3Output], Awaitable[Stage3Output]]
    maps_ref_redo: Callable[[Stage3Output], Awaitable[Stage3Output]]
    stage2_rewrite: Callable[[Stage3Output], Awaitable[Stage3Output]]
    websearch_cultural: Callable[[Stage3Output], Awaitable[Stage3Output]]
    revalidate: Callable[[Stage3Output], Awaitable[Stage3Output]]


_TOOL_DESCRIPTIONS = {
    "stage1_redecompose": (
        "Re-run stage-1 dialogue decomposition on the EN source. Use when "
        "turn_count_parity, turn_index_order, or speech-acts look wrong."
    ),
    "maps_ref_redo": (
        "Re-resolve mapped_refs via dict → retriever → web+llm chain. "
        "Use when cultural_ref_coverage, mapped_ref_ko_hangul, or "
        "mapped_ref_type_consistency fails."
    ),
    "stage2_rewrite": (
        "Regenerate the Korean rewrite with adjusted persona/register. "
        "Use when register_consistency, persona_style_consistency, "
        "naturalness, or property_preservation is low."
    ),
    "websearch_cultural": (
        "Fetch fresh cultural-ref evidence via web search. Use alongside "
        "maps_ref_redo when the dict + retriever path still fails."
    ),
    "revalidate": (
        "Re-run stage-3 phases 2-5 on the (possibly repaired) row."
    ),
}


def _row_input_str(row: Stage3Output) -> str:
    return json.dumps(
        {
            "id": row.id,
            "reject_reasons": [rr.model_dump() for rr in row.reject_reasons],
            "retry_actions": [a.model_dump() for a in row.retry_actions],
            "quality": row.quality.model_dump(),
        },
        ensure_ascii=False,
    )


def build_nat_tools(stages: StageCallables, state: dict[str, Any]):
    """Wrap each stage adapter as a NAT/LangChain ``StructuredTool``.

    NAT consumes plain LangChain ``BaseTool`` instances (see
    ``nat.agent.base.BaseAgent`` — its ``tools: list[BaseTool]`` field).
    Keeping our repair adapters as ``StructuredTool`` lets callers feed
    them into any NAT workflow that expects ``BaseTool``, while also
    giving us a uniform ``ainvoke`` surface for the deterministic driver
    in :func:`run_self_verify`.
    """
    from langchain_core.tools import StructuredTool  # noqa: PLC0415

    registry: dict[str, Callable[[Stage3Output], Awaitable[Stage3Output]]] = {
        "stage1_redecompose": stages.stage1_redecompose,
        "maps_ref_redo": stages.maps_ref_redo,
        "stage2_rewrite": stages.stage2_rewrite,
        "websearch_cultural": stages.websearch_cultural,
        "revalidate": stages.revalidate,
    }

    def _make_tool(name: str, fn: Callable[[Stage3Output], Awaitable[Stage3Output]]):
        async def _coro(_: str = "") -> str:
            state["row"] = await fn(state["row"])
            row = state["row"]
            return json.dumps(
                {
                    "valid": row.valid,
                    "reject_reasons": [rr.rule for rr in row.reject_reasons],
                    "quality_aggregate": row.quality.aggregate,
                },
                ensure_ascii=False,
            )

        return StructuredTool.from_function(
            coroutine=_coro,
            name=name,
            description=_TOOL_DESCRIPTIONS[name],
        )

    return {name: _make_tool(name, fn) for name, fn in registry.items()}


async def run_self_verify(
    row: Stage3Output,
    *,
    stages: StageCallables,
    enabled_actions: list[str],
    max_iter: int = 2,
) -> Stage3Output:
    """Repair ``row`` by invoking its ``retry_actions`` through NAT tools.

    Adaptive contract:

    - Start from ``row.retry_actions`` (intersected with ``enabled_actions``).
    - On each pass, apply one repair tool then call ``revalidate``. The
      ``revalidate`` tool re-runs phases 2-5 *and* re-derives
      ``retry_actions`` via :mod:`retry_hints`, so the plan for the
      next pass reflects the *current* rejection reasons rather than the
      original ones. Example: after ``maps_ref_redo`` fixes the ref
      types, ``mapped_ref_surface`` may surface next — that maps to
      ``stage2_rewrite`` on the following iteration.
    - We never call the same tool twice on the same row.
    - Budget: ``max_iter`` repair+revalidate cycles. Early-stop on
      ``row.valid``.

    Returns the (possibly now-valid) row. Every tool call is a real
    NVIDIA NIM round-trip; there is no offline fallback.
    """
    state_ctx: dict[str, Any] = {"row": row}
    tools = build_nat_tools(stages, state_ctx)
    revalidate_tool = tools["revalidate"]

    enabled = {a for a in enabled_actions if a != "none" and a in tools}
    seen: set[str] = set()

    def _next_action() -> str | None:
        current = state_ctx["row"].retry_actions
        for act in current:
            name = act.action
            if name in enabled and name not in seen:
                return name
        return None

    for step in range(1, max(1, max_iter) + 1):
        action = _next_action()
        if action is None:
            break
        seen.add(action)
        logger.info("[phase6] id=%s step=%d action=%s", row.id, step, action)
        await tools[action].ainvoke("")
        obs = await revalidate_tool.ainvoke("")
        logger.info("[phase6] id=%s revalidate -> %s", row.id, obs)
        if state_ctx["row"].valid:
            break

    return state_ctx["row"]


__all__ = [
    "StageCallables",
    "build_nat_tools",
    "run_self_verify",
]
