"""Phase 1 schema validation + NV-Embed-based semantic dedup."""

from __future__ import annotations

from nemos_dream.stage3_validate import phase1_schema_dedup


def _stub_embed(vectors: dict[str, list[float]] | None = None, dim: int = 8):
    """Return an ``embed_fn`` that hashes text to a deterministic vector.

    Equal texts get equal vectors (cosine = 1.0) so two copies of the same
    row trip the exact-dup threshold. Different texts get different
    vectors that fall well below the semantic threshold.
    """
    import hashlib

    def fn(texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            digest = hashlib.md5(t.encode("utf-8")).digest()
            vec = [((digest[i % len(digest)] / 255.0) * 2.0) - 1.0 for i in range(dim)]
            out.append(vec)
        return out

    return fn


def test_semantic_dedup_flags_exact_dup(stage2_row):
    dup = stage2_row.model_copy(deep=True)
    dup.id = f"{stage2_row.id}-dup"
    exact, semantic = phase1_schema_dedup.semantic_dedup_ids(
        [stage2_row, dup], embed_fn=_stub_embed()
    )
    assert dup.id in exact
    assert stage2_row.id not in exact
    assert stage2_row.id not in semantic


def test_semantic_dedup_empty_list():
    exact, semantic = phase1_schema_dedup.semantic_dedup_ids([], embed_fn=_stub_embed())
    assert exact == set()
    assert semantic == set()


def test_run_reports_schema_error(tmp_path):
    p = tmp_path / "bad.jsonl"
    p.write_text('{"not":"a valid row"}\n', encoding="utf-8")
    rows, errors = phase1_schema_dedup.run(p, embed_fn=_stub_embed())
    assert rows == []
    assert len(errors) == 1


def test_run_roundtrips_valid_rows(stage2_row, tmp_path):
    p = tmp_path / "ok.jsonl"
    p.write_text(stage2_row.model_dump_json() + "\n", encoding="utf-8")
    rows, errors = phase1_schema_dedup.run(p, embed_fn=_stub_embed())
    assert errors == []
    assert len(rows) == 1
    assert rows[0].valid is True
