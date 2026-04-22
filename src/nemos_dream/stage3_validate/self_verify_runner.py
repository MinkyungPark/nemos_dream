"""Drive the NAT ReAct self-verify agent over the stage-3 retry queue.

The orchestrator wires every tool in :class:`phase6_self_verify.StageCallables`
to real stage-1 / stage-2 / stage-3 entrypoints — no stubs, no offline
fallback. The NAT agent picks actions from ``row.retry_actions`` (cross-
referenced with ``Stage3Config.self_verify_enabled_actions``), repairs the
row in place, and re-runs phases 2-5 via the ``revalidate`` tool.

``run_self_verify_over_queue`` is the single entrypoint called by
``runner.run_async`` after phase 1-5 + ``retry_hints.apply``.
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from nemos_dream.schemas import (
    MappedRef,
    RawInput,
    Stage1Output,
    Stage2Output,
    Stage3Output,
)
from nemos_dream.stage1_decompose_map import cultural_map as _cultural_map
from nemos_dream.stage1_decompose_map._validator import validate_refs
from nemos_dream.stage1_decompose_map.decompose import decompose as _decompose
from nemos_dream.stage2_translate_rewrite.pipeline_modes import (
    DEFAULT_PIPELINE_MODE,
)
from nemos_dream.stage2_translate_rewrite.run_step3 import (
    DEFAULT_ENDPOINT as _STAGE2_ENDPOINT,
    DEFAULT_MODEL as _STAGE2_MODEL,
    DEFAULT_PERSONA_DIR as _STAGE2_PERSONA_DIR,
    DEFAULT_SEED as _STAGE2_SEED,
    load_environment as _stage2_load_env,
    run_single_row as _stage2_step3_run_single,
)
from nemos_dream.stage2_translate_rewrite.run_step4 import (
    run_single_row as _stage2_step4_run_single,
)
from nemos_dream.stage3_validate import (
    phase2_rules,
    phase3_guardrails,
    phase4_semantic,
    phase5_judge_reward,
    retry_hints,
)
from nemos_dream.stage3_validate.phase6_self_verify import (
    StageCallables,
    run_self_verify,
)

EmbedFn = Callable[[list[str]], list[list[float]]]
JudgeFn = Callable[..., Awaitable[dict[str, Any]]]
RewardFn = Callable[..., Awaitable[dict[str, float]]]
SafetyFn = Callable[[str], Awaitable[bool]]
PiiFn = Callable[[str], bool]


# --------------------------------------------------------------------------- #
# tool: revalidate — re-run phases 2-5 on the (possibly repaired) row
# --------------------------------------------------------------------------- #


async def _revalidate(
    row: Stage3Output,
    *,
    embed_fn: EmbedFn,
    judge_fn: JudgeFn,
    reward_fn: RewardFn,
    safety_fn: SafetyFn,
    pii_fn: PiiFn,
    rules_cfg: dict[str, Any],
    axis_floor: int,
    aggregate_floor: float,
    weights: dict[str, float],
    coherence_floor: float,
) -> Stage3Output:
    row.reject_reasons = []
    row.retry_actions = []
    row.valid = True
    # Keep historical axis scores on ``quality`` but clear the aggregate so
    # phase 5 recomputes it cleanly when the KR side changes.
    row.quality.aggregate = None

    rows = [row]
    phase2_rules.apply(rows, rules_cfg)
    if row.valid:
        await phase3_guardrails.apply_async(rows, safety_fn=safety_fn, pii_fn=pii_fn)
    if row.valid:
        phase4_semantic.apply(rows, embed_fn=embed_fn, coherence_floor=coherence_floor)
    if row.valid:
        await phase5_judge_reward.apply_async(
            rows,
            judge_fn=judge_fn,
            reward_fn=reward_fn,
            axis_floor=axis_floor,
            aggregate_floor=aggregate_floor,
            weights=weights,
        )
    retry_hints.apply(rows)
    return rows[0]


# --------------------------------------------------------------------------- #
# tool: maps_ref_redo — re-run stage-1b cultural mapping cascade
# --------------------------------------------------------------------------- #


async def _maps_ref_redo(row: Stage3Output) -> Stage3Output:
    refs = list(row.dialogue_decomposed.cultural_refs)
    if not refs:
        return row
    use_llm = os.environ.get("STAGE1_VALIDATE_LLM", "").lower() in {"1", "true", "yes"}
    # Run the blocking stage-1 pipeline in a thread so we don't block the event loop.
    mapped = await asyncio.to_thread(
        _cultural_map.map_refs, refs, dialogue=list(row.source_dialogue)
    )
    mapped = await asyncio.to_thread(validate_refs, mapped, use_llm=use_llm)
    row.mapped_refs = mapped
    return row


# --------------------------------------------------------------------------- #
# tool: websearch_cultural — force web+llm path for every cultural_ref
# --------------------------------------------------------------------------- #


def _resolve_via_websearch(row: Stage3Output) -> list[MappedRef]:
    refs = list(row.dialogue_decomposed.cultural_refs)
    mapped: list[MappedRef] = []
    dialogue = list(row.source_dialogue)
    for ref in refs:
        context = _cultural_map._extract_context(ref.term, dialogue)
        mapped.append(_cultural_map._web_then_llm(ref.term, ref.type, context=context))
    return validate_refs(mapped, use_llm=False)


async def _websearch_cultural(row: Stage3Output) -> Stage3Output:
    if not row.dialogue_decomposed.cultural_refs:
        return row
    row.mapped_refs = await asyncio.to_thread(_resolve_via_websearch, row)
    return row


# --------------------------------------------------------------------------- #
# tool: stage2_rewrite — re-run stage-2 step3 + step4 on the repaired row
# --------------------------------------------------------------------------- #


def _to_stage1(row: Stage3Output) -> Stage1Output:
    return Stage1Output(
        id=row.id,
        original_index=row.original_index,
        source_dialogue=list(row.source_dialogue),
        speakers=list(row.speakers),
        scene=row.scene,
        dialogue_decomposed=row.dialogue_decomposed,
        mapped_refs=list(row.mapped_refs),
    )


def _merge_stage2(stage2_row: Stage2Output, row: Stage3Output) -> Stage3Output:
    payload = row.model_dump()
    payload["final_dialogue"] = [t.model_dump() for t in stage2_row.final_dialogue]
    payload["step3_korean_dialogue"] = [
        t.model_dump() for t in stage2_row.step3_korean_dialogue
    ]
    payload["persona"] = [p.model_dump() for p in stage2_row.persona]
    payload["translation_meta"] = dict(stage2_row.translation_meta or {})
    payload["korean_dialogue"] = []  # let the validator re-mirror final_dialogue
    return Stage3Output.model_validate(payload)


def _run_stage2_single(row: Stage3Output) -> Stage2Output:
    stage1_row = _to_stage1(row)
    api_key = _stage2_load_env(None)
    artifact_root = Path(".artifacts") / "stage3_self_verify_stage2"
    artifact_root.mkdir(parents=True, exist_ok=True)
    stage2 = _stage2_step3_run_single(
        stage1_row,
        api_key=api_key,
        model_name=_STAGE2_MODEL,
        endpoint=_STAGE2_ENDPOINT,
        persona_dir=_STAGE2_PERSONA_DIR,
        artifact_root=artifact_root / "step3",
        mode="create",
        base_seed=_STAGE2_SEED,
        dataset_name_prefix="sv-step3",
        pipeline_mode=DEFAULT_PIPELINE_MODE,
    )
    stage2 = _stage2_step4_run_single(
        stage2,
        api_key=api_key,
        model_name=_STAGE2_MODEL,
        endpoint=_STAGE2_ENDPOINT,
        artifact_root=artifact_root / "step4",
        mode="create",
        dataset_name_prefix="sv-step4",
        pipeline_mode=DEFAULT_PIPELINE_MODE,
    )
    return stage2


async def _stage2_rewrite(row: Stage3Output) -> Stage3Output:
    stage2 = await asyncio.to_thread(_run_stage2_single, row)
    return _merge_stage2(stage2, row)


# --------------------------------------------------------------------------- #
# tool: stage1_redecompose — re-run stage-1a on source dialogue
# --------------------------------------------------------------------------- #


async def _stage1_redecompose(row: Stage3Output) -> Stage3Output:
    raw = RawInput(
        id=row.id,
        original_index=row.original_index,
        dialogue=[t.text for t in row.source_dialogue],
        speakers=[t.speaker for t in row.source_dialogue],
        narrative=row.scene.narrative_en or "",
    )
    results = await asyncio.to_thread(_decompose, [raw])
    if not results:
        return row
    r = results[0]
    row.source_dialogue = list(r.turns)
    row.speakers = list(r.speakers)
    row.scene = r.scene
    row.dialogue_decomposed = r.dialogue_decomposed
    return row


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #


def build_stage_callables(
    *,
    embed_fn: EmbedFn,
    judge_fn: JudgeFn,
    reward_fn: RewardFn,
    safety_fn: SafetyFn,
    pii_fn: PiiFn,
    rules_cfg: dict[str, Any],
    axis_floor: int,
    aggregate_floor: float,
    weights: dict[str, float],
    coherence_floor: float,
) -> StageCallables:
    """Wire the full set of repair adapters. Every tool is REAL (no stubs)."""

    async def revalidate(row: Stage3Output) -> Stage3Output:
        return await _revalidate(
            row,
            embed_fn=embed_fn,
            judge_fn=judge_fn,
            reward_fn=reward_fn,
            safety_fn=safety_fn,
            pii_fn=pii_fn,
            rules_cfg=rules_cfg,
            axis_floor=axis_floor,
            aggregate_floor=aggregate_floor,
            weights=weights,
            coherence_floor=coherence_floor,
        )

    return StageCallables(
        stage1_redecompose=_stage1_redecompose,
        maps_ref_redo=_maps_ref_redo,
        stage2_rewrite=_stage2_rewrite,
        websearch_cultural=_websearch_cultural,
        revalidate=revalidate,
    )


async def run_self_verify_over_queue(
    rows: list[Stage3Output],
    *,
    stages: StageCallables,
    enabled_actions: list[str],
    max_iter: int,
) -> None:
    """Mutate each row in ``rows`` by running the phase-6 repair loop.

    Phase 6 reads the fresh ``retry_actions`` off each row on every
    iteration (adaptive plan), so we pass ``enabled_actions`` as the
    config-level allow-list rather than a pre-filtered per-row list.
    Rows are processed sequentially to stay under stage-2 rewrite's
    single-worker NIM concurrency cap.
    """
    if not rows:
        return

    for row in rows:
        # Skip rows with no actionable hint at all.
        if not any(
            a.action != "none" and a.action in enabled_actions
            for a in row.retry_actions
        ):
            continue

        starting_iter = row.iter or 0
        repaired = await run_self_verify(
            row,
            stages=stages,
            enabled_actions=enabled_actions,
            max_iter=max_iter,
        )
        repaired.iter = starting_iter + 1
        if repaired is not row:
            idx = rows.index(row)
            rows[idx] = repaired
