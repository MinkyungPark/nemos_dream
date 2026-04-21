"""Stage 4 entrypoint — orchestrates metrics, viz, and SFT export."""

from __future__ import annotations

from pathlib import Path


def run(
    accepted_path: str | Path,
    rejected_path: str | Path,
    output_dir: str | Path,
) -> dict[str, str]:
    """Render the report and emit the SFT JSONL.

    Returns a dict of emitted artifact paths, e.g.::

        {
            "report_html": "data/reports/report.html",
            "report_json": "data/reports/report.json",
            "sft_jsonl":   "data/reports/sft.jsonl",
        }
    """
    raise NotImplementedError("stage 4 owner: implement")
