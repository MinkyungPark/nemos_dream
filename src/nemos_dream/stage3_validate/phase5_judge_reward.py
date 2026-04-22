"""Phase 5 — Nemotron judge + Nemotron-4-340B-Reward (async fan-out).

``judge_fn`` and ``reward_fn`` are awaited per row under an
``asyncio.Semaphore(concurrency)`` cap. The runner wires them from
``stage3_validate.clients.JudgeClient`` / ``RewardClient`` — both hit
NVIDIA-hosted NIM endpoints. There is no offline stub: phase 5 only runs
when NIM credentials are present.

Judge axes follow the canonical ``QualityScores`` contract (1-5):

- ``property_preservation`` — speech-act / register / emotion intensity
- ``naturalness`` — reads like natural Korean for this platform/age
- ``cultural_appropriateness`` — cultural substitutions are idiomatic
- ``register_consistency`` — honorific level stays consistent
- ``persona_style_consistency`` — each speaker matches its persona

Reward returns ``dict[str, float]`` with two 1-5 scores: ``correctness``
and ``coherence``. ``correctness`` here is **not** EN↔KR semantic
equivalence — it scores fidelity to the stage-1/2 ground truth
(``mapped_refs`` substitutions, ``overall_register``/``overall_emotion``
intensity/``speech_acts``, and per-speaker ``persona``), because this
pipeline is a cultural rewrite rather than a translation. Shape is kept
as ``(correctness, coherence)`` so ``dataset_metrics.reward_distribution``
keys don't move.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from nemos_dream.schemas import RejectReason, Stage3Output

JudgeFn = Callable[..., Awaitable[dict[str, Any]]]
RewardFn = Callable[..., Awaitable[dict[str, float]]]

_AXES = (
    "property_preservation",
    "naturalness",
    "cultural_appropriateness",
    "register_consistency",
    "persona_style_consistency",
)


def _kr_text(row: Stage3Output) -> str:
    turns = row.final_dialogue or row.korean_dialogue
    return "\n".join(f"{t.speaker}: {t.text}" for t in turns) if turns else ""


def _en_text(row: Stage3Output) -> str:
    return "\n".join(f"{t.speaker}: {t.text}" for t in row.source_dialogue)


def _refs_repr(row: Stage3Output) -> str:
    if not row.mapped_refs:
        return "(none)"
    return ", ".join(
        f"{m.term}→{m.ko} [type={m.type}, source={m.source}]" for m in row.mapped_refs
    )


def _persona_repr(row: Stage3Output) -> str:
    # v4 — PersonaEntry list
    if row.persona:
        parts = []
        for p in row.persona:
            rp = p.retrieved_persona
            summary = (rp.summary_text or rp.persona or "").strip().replace("\n", " ")
            if len(summary) > 120:
                summary = summary[:117] + "..."
            parts.append(
                f"{p.speaker_name_en}→{rp.name} "
                f"(age={rp.age}, occ={rp.occupation or '-'}): {summary or '-'}"
            )
        return " | ".join(parts)
    # v3 fallback — Persona list on speaker_personas
    if row.speaker_personas:
        return " | ".join(
            f"{p.speaker_ref} [register={p.formality}, emotion={p.emotion.type}]"
            for p in row.speaker_personas
        )
    return "(none)"


def _judge_kwargs(row: Stage3Output) -> dict[str, Any]:
    meta = row.dialogue_decomposed
    return {
        "en": _en_text(row),
        "ko": _kr_text(row),
        "register": meta.overall_register,
        "emotion": meta.overall_emotion.type,
        "intensity": meta.overall_emotion.intensity,
        "speech_acts": list(meta.speech_acts),
        "refs": _refs_repr(row),
        "persona": _persona_repr(row),
    }


def _reward_kwargs(row: Stage3Output) -> dict[str, Any]:
    meta = row.dialogue_decomposed
    return {
        "en": _en_text(row),
        "ko": _kr_text(row),
        "register": meta.overall_register,
        "emotion": meta.overall_emotion.type,
        "intensity": meta.overall_emotion.intensity,
        "speech_acts": list(meta.speech_acts),
        "refs": _refs_repr(row),
        "persona": _persona_repr(row),
    }


def _aggregate(scores: dict[str, Any], weights: dict[str, float]) -> float:
    num, den = 0.0, 0.0
    for axis, w in weights.items():
        val = scores.get(axis)
        if isinstance(val, int):
            num += w * val
            den += w
    return round(num / den, 3) if den else 0.0


async def _fan_out(
    fn: Callable[..., Awaitable[Any]],
    kwargs_list: list[dict[str, Any]],
    *,
    concurrency: int,
) -> list[Any]:
    sem = asyncio.Semaphore(concurrency)

    async def _wrap(kw: dict[str, Any]) -> Any:
        async with sem:
            return await fn(**kw)

    return await asyncio.gather(*(_wrap(kw) for kw in kwargs_list), return_exceptions=True)


async def apply_async(
    rows: list[Stage3Output],
    *,
    judge_fn: JudgeFn,
    reward_fn: RewardFn,
    concurrency: int = 4,
    axis_floor: int = 2,
    aggregate_floor: float = 3.0,
    weights: dict[str, float] | None = None,
) -> None:
    if not rows:
        return

    w = weights or {
        "property_preservation": 0.20,
        "naturalness": 0.20,
        "cultural_appropriateness": 0.35,
        "register_consistency": 0.125,
        "persona_style_consistency": 0.125,
    }

    judge_kwargs = [_judge_kwargs(r) for r in rows]
    reward_kwargs = [_reward_kwargs(r) for r in rows]

    judge_out, reward_out = await asyncio.gather(
        _fan_out(judge_fn, judge_kwargs, concurrency=concurrency),
        _fan_out(reward_fn, reward_kwargs, concurrency=concurrency),
    )

    for row, jres, rres in zip(rows, judge_out, reward_out, strict=True):
        q = row.quality

        if isinstance(jres, Exception):
            row.reject_reasons.append(
                RejectReason(
                    stage="stage3.phase5",
                    rule="judge_error",
                    detail=f"{type(jres).__name__}: {jres}",
                )
            )
            row.valid = False
            continue
        if isinstance(rres, Exception):
            row.reject_reasons.append(
                RejectReason(
                    stage="stage3.phase5",
                    rule="reward_error",
                    detail=f"{type(rres).__name__}: {rres}",
                )
            )
            row.valid = False
            continue

        scores: dict[str, Any] = jres or {}
        rew: dict[str, float] = rres or {}

        for axis in _AXES:
            val = scores.get(axis)
            if isinstance(val, int):
                setattr(q, axis, val)
        q.judge_reasoning = {
            **(q.judge_reasoning or {}),
            **(scores.get("reasoning") or {}),
        }
        q.aggregate = _aggregate(scores, w)
        q.reward = rew

        if not row.valid:
            continue

        failing = [
            a for a in _AXES
            if isinstance(scores.get(a), int) and scores[a] < axis_floor
        ]
        if failing:
            row.reject_reasons.append(
                RejectReason(
                    stage="stage3.phase5",
                    rule="axis_floor",
                    detail=f"axes below floor {axis_floor}: {failing}",
                    extra={"axes": failing, "floor": axis_floor},
                )
            )
            row.valid = False
            continue
        if q.aggregate is not None and q.aggregate < aggregate_floor:
            row.reject_reasons.append(
                RejectReason(
                    stage="stage3.phase5",
                    rule="aggregate_floor",
                    detail=f"aggregate {q.aggregate:.2f} < floor {aggregate_floor:.2f}",
                    extra={"aggregate": q.aggregate, "floor": aggregate_floor},
                )
            )
            row.valid = False
