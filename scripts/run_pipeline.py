"""End-to-end pipeline: stages 1 → 2 → 3 → 4.

Chains the four stage runners with the file-path convention from
``.claude/docs/stage-owner-guide.md``::

    <output_dir>/stage1/stage1_output.jsonl
    <output_dir>/stage2/stage2_output.jsonl
    <output_dir>/stage3/{accepted,rejected}.jsonl
    <output_dir>/reports/{report.*, sft.jsonl}

Usage::

    # Run 5 samples through stages 1→2→3 (stop before stage 4):
    uv run python scripts/run_pipeline.py \
        --hf-limit 5 --num-records 5 --stop-after 3

    # Full 1→4 end-to-end (default):
    uv run python scripts/run_pipeline.py \
        --input data/raw/sample_input.jsonl
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from dotenv import load_dotenv


def _fmt_elapsed(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.1f}s"
    m, s = divmod(seconds, 60)
    return f"{int(m)}m{s:04.1f}s"


def _file_size(path: Path) -> str:
    if not path.exists():
        return "0 B"
    size = path.stat().st_size
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _count_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8") as fh:
        return sum(1 for line in fh if line.strip())


def _read_first_row(path: Path) -> dict | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    return None
    return None


def _truncate(text: str, limit: int = 80) -> str:
    text = str(text or "").replace("\n", " ").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _banner(title: str) -> None:
    line = "=" * 72
    print(f"\n{line}\n  {title}\n{line}", flush=True)


def _section(title: str) -> None:
    print(f"\n▶ {title}", flush=True)


def _print_stage1_sample(row: dict | None) -> None:
    if not row:
        return
    turns = row.get("source_dialogue") or []
    refs = row.get("mapped_refs") or []
    scene = row.get("scene") or {}
    print(f"  sample id         : {row.get('id')}")
    print(f"  scene.setting     : {_truncate(scene.get('setting', ''), 70)}")
    print(f"  scene.relationship: {scene.get('relationship_type', '')}")
    print(f"  turns             : {len(turns)}")
    if turns:
        first = turns[0]
        print(f"  turn[0]           : [{first.get('speaker')}] {_truncate(first.get('text', ''))}")
    print(f"  mapped_refs       : {len(refs)}")
    for ref in refs[:3]:
        print(f"    - {ref.get('term', '')} → {ref.get('ko', '')}  ({ref.get('type', '')})")


def _print_stage2_sample(row: dict | None) -> None:
    if not row:
        return
    en_turns = row.get("source_dialogue") or []
    kr_turns = row.get("final_dialogue") or row.get("step3_korean_dialogue") or []
    personas = row.get("persona") or []
    print(f"  sample id         : {row.get('id')}")
    print(f"  persona count     : {len(personas)}")
    for p in personas[:2]:
        rp = p.get("retrieved_persona") or {}
        print(
            f"    - {rp.get('name', '')} ({rp.get('sex', '')}, "
            f"{rp.get('age', '')}세, {rp.get('occupation', '') or '-'})"
        )
    pairs = min(len(en_turns), len(kr_turns))
    print(f"  turn pairs        : EN={len(en_turns)} / KR={len(kr_turns)}")
    for i in range(min(2, pairs)):
        en = en_turns[i]
        kr = kr_turns[i]
        print(f"    EN[{i}] [{en.get('speaker')}] {_truncate(en.get('text', ''))}")
        print(f"    KR[{i}] [{kr.get('speaker')}] {_truncate(kr.get('text', ''))}")


def _print_stage3_sample(accepted_row: dict | None, rejected_row: dict | None) -> None:
    if accepted_row:
        q = accepted_row.get("quality") or {}
        print(f"  accepted sample id: {accepted_row.get('id')}")
        axes = q.get("axes") or {}
        print(
            "    quality axes    : "
            + ", ".join(f"{k}={v}" for k, v in list(axes.items())[:6])
        )
        print(f"    aggregate       : {q.get('aggregate')}")
    if rejected_row:
        print(f"  rejected sample id: {rejected_row.get('id')}")
        reasons = rejected_row.get("reject_reasons") or []
        for r in reasons[:3]:
            print(
                f"    - phase={r.get('phase')} code={r.get('code')} "
                f"note={_truncate(r.get('note', ''), 60)}"
            )


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="data/raw/soda.jsonl",
        help="Path to the raw JSONL. If --hf-spec is set, the file is (re)materialized here before stage 1.",
    )
    parser.add_argument("--output-dir", default="data/")
    parser.add_argument(
        "--hf-spec",
        default="allenai/soda",
        help="HuggingFace dataset id to download into --input. Pass empty string to skip the download.",
    )
    parser.add_argument("--hf-split", default="train")
    parser.add_argument("--hf-limit", type=int, default=4)
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Stage 1: overwrite output; stage 2: run with --no-resume. Default resumes both.",
    )
    parser.add_argument(
        "--num-records",
        type=int,
        default=None,
        help="Optional row cap forwarded to stage 2.",
    )
    parser.add_argument(
        "--stage2-pipeline-mode",
        default="default",
        choices=["default", "direct", "naive_persona"],
        help="Choose which stage-2 pipeline variant to run.",
    )
    parser.add_argument(
        "--stop-after",
        type=int,
        choices=[1, 2, 3, 4],
        default=4,
        help="Stop after this stage (inclusive). Use 3 to run only 1→2→3.",
    )
    args = parser.parse_args()

    out = Path(args.output_dir)
    stage1_out = out / "stage1" / "stage1_output.jsonl"
    from nemos_dream.stage2_translate_rewrite.pipeline_modes import default_stage2_output_path

    stage2_out = default_stage2_output_path(
        out / "stage2",
        args.stage2_pipeline_mode,
    )
    stage3_dir = out / "stage3"
    stage4_dir = out / "reports"

    pipeline_t0 = time.perf_counter()
    _banner(
        f"nemos_dream pipeline  |  stop_after=stage{args.stop_after}  "
        f"|  stage2_mode={args.stage2_pipeline_mode}  "
        f"|  hf_limit={args.hf_limit}  num_records={args.num_records}"
    )

    if args.hf_spec:
        _section(f"HF download · {args.hf_spec}:{args.hf_split} (limit={args.hf_limit})")
        t0 = time.perf_counter()
        from nemos_dream.io_utils import materialize_hf_to_jsonl

        n = materialize_hf_to_jsonl(
            args.hf_spec,
            args.input,
            limit=args.hf_limit,
            split=args.hf_split,
        )
        print(
            f"  wrote {n} rows → {args.input}  "
            f"({_file_size(Path(args.input))}, {_fmt_elapsed(time.perf_counter() - t0)})"
        )

    from nemos_dream.stage1_decompose_map.runner import run as run_stage1

    # ---------------- stage 1 ----------------
    _section("Stage 1 · decompose + cultural map")
    t0 = time.perf_counter()
    n1 = run_stage1(args.input, stage1_out, overwrite=args.overwrite)
    print(
        f"  rows written       : {n1}   ({_file_size(stage1_out)}, "
        f"{_fmt_elapsed(time.perf_counter() - t0)})"
    )
    print(f"  output             : {stage1_out}")
    _print_stage1_sample(_read_first_row(stage1_out))
    if args.stop_after <= 1:
        print(f"\nDone (stopped after stage 1).  total={_fmt_elapsed(time.perf_counter() - pipeline_t0)}")
        return 0

    from nemos_dream.stage2_translate_rewrite.runner import run as run_stage2

    # ---------------- stage 2 ----------------
    _section(f"Stage 2 · translate + rewrite (mode={args.stage2_pipeline_mode})")
    t0 = time.perf_counter()
    n2 = run_stage2(
        stage1_out,
        stage2_out,
        pipeline_mode=args.stage2_pipeline_mode,
        num_records=args.num_records,
        resume=not args.overwrite,
    )
    print(
        f"  rows written       : {n2}   ({_file_size(stage2_out)}, "
        f"{_fmt_elapsed(time.perf_counter() - t0)})"
    )
    print(f"  output             : {stage2_out}")
    _print_stage2_sample(_read_first_row(stage2_out))
    if args.stop_after <= 2:
        print(f"\nDone (stopped after stage 2).  total={_fmt_elapsed(time.perf_counter() - pipeline_t0)}")
        return 0

    from nemos_dream.stage3_validate.runner import run as run_stage3

    # ---------------- stage 3 ----------------
    _section("Stage 3 · validate (schema → rules → guardrails → semantic → judge+reward)")
    t0 = time.perf_counter()
    counts = run_stage3(stage2_out, stage3_dir)
    elapsed = time.perf_counter() - t0
    total = counts.get("accepted", 0) + counts.get("rejected", 0)
    accept_rate = (counts.get("accepted", 0) / total * 100.0) if total else 0.0
    print(f"  total seen         : {total}   ({_fmt_elapsed(elapsed)})")
    print(
        f"  accepted           : {counts.get('accepted', 0)}  "
        f"({accept_rate:.1f}% accept rate)"
    )
    print(f"  rejected           : {counts.get('rejected', 0)}")
    print(f"  retry_queue        : {counts.get('retry_queue', 0)}")
    print(f"  parse_errors       : {counts.get('parse_errors', 0)}")
    accepted_path = stage3_dir / "accepted.jsonl"
    rejected_path = stage3_dir / "rejected.jsonl"
    print(
        f"  artifacts          : accepted.jsonl ({_count_rows(accepted_path)} rows, "
        f"{_file_size(accepted_path)}), rejected.jsonl ({_count_rows(rejected_path)} rows, "
        f"{_file_size(rejected_path)})"
    )
    print(f"  output dir         : {stage3_dir}")
    _print_stage3_sample(_read_first_row(accepted_path), _read_first_row(rejected_path))
    if args.stop_after <= 3:
        print(f"\nDone (stopped after stage 3).  total={_fmt_elapsed(time.perf_counter() - pipeline_t0)}")
        return 0

    from nemos_dream.stage4_report.runner import run as run_stage4

    # ---------------- stage 4 ----------------
    _section("Stage 4 · report + SFT export")
    t0 = time.perf_counter()
    artifacts = run_stage4(
        stage3_dir / "accepted.jsonl",
        stage3_dir / "rejected.jsonl",
        stage4_dir,
    )
    print(f"  artifacts          : {artifacts}   ({_fmt_elapsed(time.perf_counter() - t0)})")
    print(f"  output dir         : {stage4_dir}")

    print(f"\nDone.  total={_fmt_elapsed(time.perf_counter() - pipeline_t0)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
