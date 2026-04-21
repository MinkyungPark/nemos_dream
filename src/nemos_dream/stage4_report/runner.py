"""Stage 4 entrypoint: ``Stage3Output`` streams → report + ``Stage4Sft`` rows."""

from __future__ import annotations

from pathlib import Path


def run(
    accepted_path: str | Path,
    rejected_path: str | Path,
    output_dir: str | Path,
) -> dict[str, str]:
    """Render the report and emit the SFT JSONL.

    Auto-discovers stage1 and stage2 JSONL files next to the accepted/rejected
    paths (looks for ``../stage1/*.jsonl``, ``../stage2/*.jsonl`` relative to
    ``accepted_path``). Pass explicit paths via the keyword arguments below if
    the layout differs.

    Returns a dict of emitted artifact paths.
    """
    accepted_path = Path(accepted_path)
    rejected_path = Path(rejected_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Auto-discover sibling stage directories
    data_root = accepted_path.parent.parent  # data/stage3 → data/
    stage1_path = _first_jsonl(data_root / "stage1") or _first_jsonl(data_root / "raw")
    stage2_path = _first_jsonl(data_root / "stage2")
    raw_path = _first_jsonl(data_root / "raw")

    artifacts: dict[str, str] = {}

    # ── SFT export ────────────────────────────────────────────────────────────
    from nemos_dream.stage4_report.sft_export import export as _export

    sft_path = output_dir / "sft.jsonl"
    n_sft = _export(accepted_path, sft_path)
    artifacts["sft"] = str(sft_path)
    print(f"  sft export: {n_sft} rows → {sft_path}")

    # ── Case viewer (stage-by-stage progression) ──────────────────────────────
    from nemos_dream.stage4_report.case_viewer import build_html as _case_html

    # Combine accepted + rejected into a single stage3 file for the viewer
    combined_path = output_dir / "_stage3_combined.jsonl"
    _combine_jsonl([accepted_path, rejected_path], combined_path)

    case_path = output_dir / "case_viewer.html"
    try:
        _case_html(
            stage1_path=stage1_path,
            stage2_path=stage2_path,
            stage3_path=combined_path,
            output_path=case_path,
        )
        artifacts["case_viewer"] = str(case_path)
        print(f"  case viewer: {case_path}")
    except Exception as exc:
        print(f"  case viewer skipped: {exc}")

    # ── Distribution shift ────────────────────────────────────────────────────
    try:
        from nemos_dream.stage4_report.distribution_shift import build_report as _dist

        dist_path = _dist(
            stage1_path=stage1_path,
            stage2_path=stage2_path,
            stage3_path=combined_path,
            raw_path=raw_path,
            output_dir=output_dir,
        )
        artifacts["distribution_shift"] = str(dist_path)
        print(f"  distribution shift: {dist_path}")
    except ImportError:
        print("  distribution shift skipped: scikit-learn not installed")
    except Exception as exc:
        print(f"  distribution shift skipped: {exc}")

    return artifacts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _first_jsonl(directory: Path) -> Path | None:
    if not directory.exists():
        return None
    for path in sorted(directory.glob("*.jsonl")):
        return path
    return None


def _combine_jsonl(paths: list[Path], output: Path) -> None:
    with output.open("w", encoding="utf-8") as f:
        for p in paths:
            if p.exists():
                for line in p.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        f.write(line + "\n")
