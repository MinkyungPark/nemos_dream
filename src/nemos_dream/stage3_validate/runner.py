"""Stage 3 entrypoint: ``Stage2Output`` rows → ``Stage3Output`` rows (+ splits).

The runner chains the five scoring phases (schema+dedup → rules →
guardrails → semantic → judge+reward), derives retry hints, runs the
NAT ReAct self-verify loop on rows with actionable retry hints, and
then writes the README-mandated artifacts under ``output_dir``:

- ``accepted.jsonl`` — rows with ``valid=True`` (includes rows that
  went through self-verify and came out valid)
- ``rejected.jsonl`` — rows with ``valid=False`` (post-self-verify)
- ``retry_queue.jsonl`` — rows that were fed to self-verify
- ``repaired.jsonl`` — rows after self-verify (``iter >= 1``)
- ``dataset_metrics.json`` — absolute quality/diversity telemetry
- ``reject_details.json`` — per-row reject diary for debugging
- ``parse_errors.json`` — line-level schema-parse failures

All LLM / embedding calls are required — stage 3 is NVIDIA-native and
has no offline stubs. The runner builds its clients through
``stage3_validate.clients.build_default_clients`` which reads
``NVIDIA_API_KEY`` from the environment (or ``.env`` if the caller
loaded it). Tests supply their own in-memory ``judge_fn`` / ``reward_fn``
/ ``safety_fn`` / ``embed_fn`` / ``pii_fn`` shims and set
``run_self_verify=False`` to skip the NAT agent.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from nemos_dream.stage3_validate import (
    clients,
    config,
    dataset_metrics,
    phase1_schema_dedup,
    phase2_rules,
    phase3_guardrails,
    phase4_semantic,
    phase5_judge_reward,
    retry_hints,
)

EmbedFn = Callable[[list[str]], list[list[float]]]
JudgeFn = Callable[..., Awaitable[dict[str, Any]]]
RewardFn = Callable[..., Awaitable[dict[str, float]]]
SafetyFn = Callable[[str], Awaitable[bool]]
PiiFn = Callable[[str], bool]


def _reject_diary(rows: list[Any]) -> list[dict[str, Any]]:
    out = []
    for r in rows:
        if r.valid:
            continue
        out.append(
            {
                "id": r.id,
                "source_dialogue": [t.model_dump() for t in r.source_dialogue],
                "reject_reasons": [rr.model_dump() for rr in r.reject_reasons],
                "retry_actions": [a.model_dump() for a in r.retry_actions],
                "mapped_refs": [m.model_dump() for m in r.mapped_refs],
            }
        )
    return out


def _retry_queue(rows: list[Any]) -> list[Any]:
    """Rejected rows with at least one non-``none`` retry_action.

    These are what the NAT self-verify agent should work on. Safety
    rejects (hard-stop) have ``retry_actions=[{"action":"none", ...}]``
    so they're excluded.
    """
    out = []
    for r in rows:
        if r.valid:
            continue
        actionable = [a for a in r.retry_actions if a.action != "none"]
        if actionable:
            out.append(r)
    return out


async def run_async(
    input_path: str | Path,
    output_dir: str | Path,
    *,
    cfg: config.Stage3Config | None = None,
    embed_fn: EmbedFn | None = None,
    judge_fn: JudgeFn | None = None,
    reward_fn: RewardFn | None = None,
    safety_fn: SafetyFn | None = None,
    pii_fn: PiiFn | None = None,
    run_self_verify: bool = True,
) -> dict[str, int]:
    """Async end-to-end stage-3 runner.

    If any of the five callables is ``None``, the runner constructs the
    default NVIDIA-native client from ``clients.build_default_clients``.
    A missing ``NVIDIA_API_KEY`` therefore fails loudly at first use —
    that's intentional: stage 3 is NIM-backed end-to-end.

    When ``run_self_verify=True`` (the default) the runner runs phases
    1-5 + retry_hints, then drives the NAT ReAct self-verify agent
    (``phase6_self_verify`` via ``self_verify_runner``) over every row
    with actionable retry actions. Tests set this to ``False``.
    """
    # Resolve both paths eagerly so later write_text calls don't race
    # against any cwd-sensitive plumbing inside stage-2 rewrite / Curator.
    input_path = Path(input_path).resolve()
    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    cfg = cfg or config.load()
    defaults = clients.build_default_clients() if any(
        x is None for x in (embed_fn, judge_fn, reward_fn, safety_fn)
    ) else {}

    embed_fn = embed_fn or defaults.get("embed_fn")
    judge_fn = judge_fn or defaults.get("judge_fn")
    reward_fn = reward_fn or defaults.get("reward_fn")
    safety_fn = safety_fn or defaults.get("safety_fn")
    pii_fn = pii_fn or phase3_guardrails.make_pii_fn()

    if embed_fn is None or judge_fn is None or reward_fn is None or safety_fn is None:
        raise RuntimeError(
            "stage 3 requires NIM clients: set NVIDIA_API_KEY (and load .env "
            "if applicable) or pass embed_fn/judge_fn/reward_fn/safety_fn "
            "explicitly from a test harness."
        )

    rows, parse_errors = phase1_schema_dedup.run(
        input_path,
        embed_fn=embed_fn,
        semantic_threshold=cfg.semantic_cosine_threshold,
    )

    rules_cfg = {"ascii_ratio_max": cfg.ascii_ratio_max}
    phase2_rules.apply(rows, rules_cfg)
    await phase3_guardrails.apply_async(rows, safety_fn=safety_fn, pii_fn=pii_fn)
    phase4_semantic.apply(rows, embed_fn=embed_fn, coherence_floor=cfg.intra_kr_coherence_floor)
    # Phase 5 (judge + reward) is the most expensive step — two LLM calls
    # per row against the NEMO_3_SUPER / NEMO_REWARD endpoints. Skip
    # rows that phases 2-4 have already invalidated so we don't burn a
    # judge-pass on rows we're about to throw into ``rejected.jsonl`` or
    # the retry queue. Invalid rows still get ``retry_hints.apply``
    # below, which only reads ``reject_reasons`` — no judge scores
    # needed to derive retry actions.
    rows_for_phase5 = [r for r in rows if r.valid]
    if rows_for_phase5:
        await phase5_judge_reward.apply_async(
            rows_for_phase5,
            judge_fn=judge_fn,
            reward_fn=reward_fn,
            axis_floor=cfg.axis_floor,
            aggregate_floor=cfg.aggregate_floor,
            weights=cfg.quality_weights,
        )
    retry_hints.apply(rows)

    # Snapshot the pre-self-verify retry queue for the audit log. Self-verify
    # mutates its target rows in place, so copy the JSON now — otherwise
    # retry_queue.jsonl would end up mirroring the post-repair state.
    pre_retry_rows = _retry_queue(rows)
    pre_retry_snapshot = [r.model_dump_json() for r in pre_retry_rows]

    repaired_rows: list[Any] = []
    if run_self_verify and pre_retry_rows:
        from nemos_dream.stage3_validate.self_verify_runner import (
            build_stage_callables,
            run_self_verify_over_queue,
        )

        stages = build_stage_callables(
            embed_fn=embed_fn,
            judge_fn=judge_fn,
            reward_fn=reward_fn,
            safety_fn=safety_fn,
            pii_fn=pii_fn,
            rules_cfg=rules_cfg,
            axis_floor=cfg.axis_floor,
            aggregate_floor=cfg.aggregate_floor,
            weights=cfg.quality_weights,
            coherence_floor=cfg.intra_kr_coherence_floor,
        )
        await run_self_verify_over_queue(
            pre_retry_rows,
            stages=stages,
            enabled_actions=cfg.self_verify_enabled_actions,
            max_iter=cfg.self_verify_max_iter,
        )
        repaired_rows = [r for r in pre_retry_rows if (r.iter or 0) > 0]

    accepted = [r for r in rows if r.valid]
    rejected = [r for r in rows if not r.valid]

    (out_dir / "accepted.jsonl").write_text(
        "\n".join(r.model_dump_json() for r in accepted) + ("\n" if accepted else ""),
        encoding="utf-8",
    )
    (out_dir / "rejected.jsonl").write_text(
        "\n".join(r.model_dump_json() for r in rejected) + ("\n" if rejected else ""),
        encoding="utf-8",
    )
    (out_dir / "retry_queue.jsonl").write_text(
        "\n".join(pre_retry_snapshot) + ("\n" if pre_retry_snapshot else ""),
        encoding="utf-8",
    )
    (out_dir / "repaired.jsonl").write_text(
        "\n".join(r.model_dump_json() for r in repaired_rows)
        + ("\n" if repaired_rows else ""),
        encoding="utf-8",
    )

    metrics = dataset_metrics.compute(accepted, rejected, embed_fn=embed_fn)
    (out_dir / "dataset_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "reject_details.json").write_text(
        json.dumps(_reject_diary(rows), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (out_dir / "parse_errors.json").write_text(
        json.dumps(
            [{"lineno": ln, "detail": d} for ln, d in parse_errors],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return {
        "accepted": len(accepted),
        "rejected": len(rejected),
        "retry_queue": len(pre_retry_rows),
        "repaired": len(repaired_rows),
        "repaired_valid": sum(1 for r in repaired_rows if r.valid),
        "parse_errors": len(parse_errors),
    }


def run(input_path: str | Path, output_dir: str | Path, **kwargs: Any) -> dict[str, int]:
    """Sync wrapper over :func:`run_async`."""
    import asyncio

    return asyncio.run(run_async(input_path, output_dir, **kwargs))
