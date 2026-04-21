"""Stage 3 → Stage 4 SFT export.

Converts ``Stage3Output`` accepted rows into ``Stage4Sft`` (OpenAI chat shape)
and writes them to a JSONL file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_SYSTEM_PROMPT = (
    "You rewrite English social media dialogues into natural Korean conversations "
    "that match the given speaker personas and Korean cultural context. "
    "Replace English cultural references with appropriate Korean equivalents."
)


def _row_to_sft(row: dict[str, Any]) -> dict[str, Any]:
    """Convert a single Stage3Output row to Stage4Sft shape."""
    source_turns = row.get("source_dialogue") or []
    ko_turns = row.get("korean_dialogue") or []
    source_text = "\n".join(f"{t.get('speaker','')}: {t.get('text','')}" for t in source_turns)
    ko_text = "\n".join(f"{t.get('speaker','')}: {t.get('text','')}" for t in ko_turns)

    quality = row.get("quality") or {}
    meta = row.get("translation_meta") or {}
    personas = row.get("speaker_personas") or []

    platform = (
        meta.get("target_platform")
        or (personas[0].get("extra") or {}).get("target_platform")
        if personas else None
    )
    age_group = (
        meta.get("target_age_group")
        or (next((p.get("age") for p in personas if p.get("age")), None))
    )

    quality_score: dict[str, Any] = {}
    for axis in ("property_preservation", "naturalness", "cultural_appropriateness", "register_consistency", "persona_style_consistency"):
        if quality.get(axis) is not None:
            quality_score[axis] = {"score": quality[axis]}

    return {
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": source_text},
            {"role": "assistant", "content": ko_text},
        ],
        "metadata": {
            "source_id": str(row.get("id") or ""),
            "domain": "dialogue",
            "target_platform": platform,
            "target_age_group": age_group,
            "target_community": meta.get("target_community") or "",
            "target_gender_style": "neutral",
            "quality_score": quality_score,
        },
    }


def export(
    accepted_path: str | Path,
    output_path: str | Path,
) -> int:
    """Convert accepted Stage3 rows to SFT JSONL. Returns number of rows written."""
    accepted_path = Path(accepted_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows_written = 0
    with output_path.open("w", encoding="utf-8") as f:
        for line in accepted_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("valid") is False:
                continue
            sft_row = _row_to_sft(row)
            f.write(json.dumps(sft_row, ensure_ascii=False) + "\n")
            rows_written += 1
    return rows_written
