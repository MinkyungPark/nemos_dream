"""Synthesize a v4 Stage2Output sample from the stage 1 example output.

Stage 3 needs a v4-shaped input to exercise its phases, so this helper
fabricates a minimal ``Stage2Output`` for each row of
``data/stage1/example_output.jsonl``:

- ``final_dialogue`` / ``step3_korean_dialogue`` are Korean-dominant
  synthetic turns (KR fillers + injected mapped_refs). This is enough
  for pipeline plumbing tests; quality metrics on this data are not
  meaningful.
- ``persona`` is a :class:`PersonaEntry` list deterministically derived
  from each stage-1 ``Speaker``.
- One row is intentionally mutated to fail turn-count parity, one row
  is a near-duplicate of the first, one row has injected PII — so phase
  2/3 have something to reject.

Run with::

    PYTHONPATH=src python tests/stage3/synthesize_stage2_sample.py

Writes to ``data/stage2/sample_v3.jsonl`` (filename is legacy; the
payload is v4-shaped).
"""

from __future__ import annotations

import json
from pathlib import Path

from nemos_dream.schemas import (
    PersonaEntry,
    PersonaSelectionMeta,
    RetrievedPersona,
    Stage1Output,
    Stage2Output,
    Turn,
)


def _age_hint_to_ko(hint: str) -> str:
    return {
        "teen": "10대",
        "20s": "20대",
        "30s": "30대",
        "40plus": "40대",
        "unknown": "20대",
    }.get(hint, "20대")


def _gender_hint_to_ko(hint: str) -> str:
    return {"male": "남성", "female": "여성"}.get(hint, "미상")


_KO_FILLERS = [
    "그래서 그 이야기를 좀 더 자세히 해주고 싶어요.",
    "요즘 그게 정말 마음에 걸리더라고요.",
    "솔직히 말하면 기분이 많이 복잡해요.",
    "오늘 하루 종일 그 생각만 하고 있었어요.",
    "그런 상황이 생기면 어떻게 해야 할지 모르겠더라고요.",
    "가끔은 친구한테 털어놓고 싶어질 때가 있어요.",
    "예전 같으면 그냥 넘어갔을 텐데 이번에는 좀 다르더라고요.",
    "아직 정리가 잘 안 돼서 횡설수설할 수도 있어요.",
    "생각해 보니 내가 먼저 이야기를 꺼낸 적이 없었더라고요.",
    "이런 얘기는 쉽게 꺼내기 어렵잖아요, 그래도 오늘은 말해보려고요.",
    "되게 사소한 일인데 머릿속에서 떠나지가 않아요.",
    "나 혼자 끙끙대는 것보다 나눠 주는 게 낫다고 생각했어요.",
]


def _row_offset(row_id: str) -> int:
    return sum(ord(c) for c in row_id)


def _mock_ko_turn(turn: Turn, offset: int) -> Turn:
    """Deterministic Korean-dominant synthetic translation.

    Avoids inline English speaker names (those live on ``Turn.speaker``) so
    the body text is Korean-heavy. The row offset rotates the filler window
    so every row draws a different subsequence — otherwise MinHash Jaccard
    pins everything as near-dup.
    """
    filler = _KO_FILLERS[(turn.index + offset) % len(_KO_FILLERS)]
    return Turn(index=turn.index, speaker=turn.speaker, text=f"이번 발화: {filler}")


def _mock_ko_rewrite(turn: Turn, mapped_refs: list[tuple[str, str]], offset: int) -> Turn:
    """Final-pass KR body that weaves every mapped_ref.ko into the text."""
    filler = _KO_FILLERS[(turn.index + offset) % len(_KO_FILLERS)]
    refs = " ".join(ko for _, ko in mapped_refs) if mapped_refs else ""
    body = filler if not refs else f"{filler} 특히 {refs} 얘기가 나왔어요."
    return Turn(index=turn.index, speaker=turn.speaker, text=body)


_AGE_TO_INT = {"teen": 16, "20s": 24, "30s": 34, "40plus": 45, "unknown": 28}


def _synthetic_ko_name(row_id: str, name_en: str) -> str:
    surnames = ["김", "이", "박", "최", "정", "강", "조"]
    givens = ["수현", "윤지", "민재", "하늘", "지훈", "서연", "도윤", "예린"]
    s = surnames[sum(ord(c) for c in row_id) % len(surnames)]
    g = givens[sum(ord(c) for c in name_en) % len(givens)]
    return f"{s}{g}"


def synthesize(row: Stage1Output) -> Stage2Output:
    mapped = [(m.term, m.ko) for m in row.mapped_refs]
    offset = _row_offset(row.id)
    en_to_ko_name = {spk.name_en: _synthetic_ko_name(row.id, spk.name_en) for spk in row.speakers}

    draft_turns = [_mock_ko_turn(t, offset) for t in row.source_dialogue]
    final_turns = [
        Turn(
            index=t.index,
            speaker=en_to_ko_name.get(t.speaker, t.speaker),
            text=_mock_ko_rewrite(t, mapped, offset).text,
        )
        for t in row.source_dialogue
    ]

    personas = [
        PersonaEntry(
            speaker_index=i,
            speaker_name_en=spk.name_en,
            retrieved_persona=RetrievedPersona(
                name=en_to_ko_name[spk.name_en],
                age=_AGE_TO_INT.get(spk.age_group_hint, 28),
                age_bucket=_age_hint_to_ko(spk.age_group_hint),
                sex=_gender_hint_to_ko(spk.gender_hint),
                normalized_location="서울-마포구",
                occupation=spk.occupation_hint or "일반",
                persona=f"{en_to_ko_name[spk.name_en]} 씨는 합성 데이터로 생성된 가상 인물입니다.",
                persona_id=f"syn-{row.id}-{spk.name_en}",
                summary_text=f"{spk.role_in_scene} 역할의 {en_to_ko_name[spk.name_en]} 씨 합성 페르소나.",
                hobbies_and_interests=", ".join(spk.interests_hints) or "독서",
                skills_and_expertise=spk.speech_style_notes or "커뮤니케이션",
            ),
            selection_metadata=PersonaSelectionMeta(
                candidate_age_buckets=[spk.age_group_hint] if spk.age_group_hint != "unknown" else [],
                candidate_gender=spk.gender_hint,
                keyword_hints=spk.interests_hints,
                match_score=1.0,
                matched_by_keywords=bool(spk.interests_hints),
            ),
            source_speaker_profile=spk,
        )
        for i, spk in enumerate(row.speakers)
    ]

    return Stage2Output(
        **row.model_dump(),
        final_dialogue=final_turns,
        step3_korean_dialogue=final_turns,
        persona=personas,
        # Keep v3 draft field populated so legacy consumers in the repo
        # still see something while they transition.
        korean_dialogue_draft=draft_turns,
    )


def _inject_edge_cases(rows: list[Stage2Output]) -> list[Stage2Output]:
    """Break one row's turn-count parity + inject a near-duplicate + PII."""
    if len(rows) < 3:
        return rows

    broken = rows[1].model_copy(deep=True)
    broken.final_dialogue = broken.final_dialogue[:-1]
    broken.korean_dialogue = broken.final_dialogue  # keep mirror consistent
    broken.step3_korean_dialogue = broken.final_dialogue
    rows[1] = broken

    dup = rows[0].model_copy(deep=True)
    dup.id = f"{rows[0].id}-dup"
    dup.original_index = rows[0].original_index + 9_000_000
    rows.append(dup)

    unsafe = rows[2].model_copy(deep=True)
    pii_turns = [
        Turn(
            index=t.index,
            speaker=t.speaker,
            text=t.text + " 내 이메일은 test@example.com 이고 전화번호는 010-1234-5678",
        )
        for t in unsafe.final_dialogue
    ]
    unsafe.final_dialogue = pii_turns
    unsafe.step3_korean_dialogue = pii_turns
    unsafe.korean_dialogue = pii_turns
    rows[2] = unsafe
    return rows


def main() -> None:
    src = Path("data/stage1/example_output.jsonl")
    dst = Path("data/stage2/sample_v3.jsonl")
    stage1_rows = [Stage1Output.model_validate(json.loads(line)) for line in src.read_text().splitlines() if line.strip()]
    stage2_rows = [synthesize(r) for r in stage1_rows]
    stage2_rows = _inject_edge_cases(stage2_rows)

    dst.parent.mkdir(parents=True, exist_ok=True)
    with dst.open("w", encoding="utf-8") as f:
        for row in stage2_rows:
            f.write(row.model_dump_json() + "\n")
    print(f"wrote {len(stage2_rows)} synthetic Stage2Output rows to {dst}")


if __name__ == "__main__":
    main()
