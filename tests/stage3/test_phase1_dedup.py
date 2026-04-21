"""Phase 1 schema validation + dedup."""

from __future__ import annotations

import json
from pathlib import Path

from nemos_dream.stage3_validate import phase1_schema_dedup


def test_minhash_dedup_flags_near_dup(stage2_row, tmp_path):
    dup = stage2_row.model_copy(deep=True)
    dup.id = f"{stage2_row.id}-dup"

    dropped = phase1_schema_dedup.minhash_dedup_ids([stage2_row, dup])
    assert dup.id in dropped
    assert stage2_row.id not in dropped


def test_semantic_dedup_noop_without_embed_fn(stage2_row):
    dup = stage2_row.model_copy(deep=True)
    dup.id = f"{stage2_row.id}-dup"
    assert phase1_schema_dedup.semantic_dedup_ids([stage2_row, dup], embed_fn=None) == set()


def test_run_reports_schema_error(tmp_path):
    p = tmp_path / "bad.jsonl"
    p.write_text('{"not":"a valid row"}\n', encoding="utf-8")
    rows, errors = phase1_schema_dedup.run(p)
    assert rows == []
    assert len(errors) == 1


def test_run_roundtrips_valid_rows(stage2_row, tmp_path):
    p = tmp_path / "ok.jsonl"
    p.write_text(stage2_row.model_dump_json() + "\n", encoding="utf-8")
    rows, errors = phase1_schema_dedup.run(p)
    assert errors == []
    assert len(rows) == 1
    assert rows[0].valid is True
