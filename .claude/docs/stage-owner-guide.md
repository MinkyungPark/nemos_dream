# Stage owner 가이드

4명이 stage 1개씩 담당. 
이 문서에는 구현할 부분, 각 stage가 합쳐지는 곳 정리

## 공통 부분

| 파일 | 역할 |
|---|---|
| `src/nemos_dream/schemas.py` | 모든 stage 의 input/output 계약 (Pydantic) |
| `src/nemos_dream/nvidia_clients.py` | NIM / 임베딩 / judge / safety / reward 클라이언트 factory |
| `src/nemos_dream/io_utils.py` | JSONL 읽기/쓰기 헬퍼 |
| `pyproject.toml`, `.env.example` | 의존성 + 환경변수 |
| `tests/test_schemas.py` | 스키마 round-trip 테스트 (항상 통과해야 함) |

LLM 호출은 `nvidia_clients.py` 의 factory 만 사용. `OpenAI(...)` 직접 금지.

## 합쳐지는 방식 (파일 경로로 연결)

Stage 간 연결은 **JSONL 파일** 로만 일어남. 각 stage 는 앞 stage 의 JSONL
을 읽어서 자기 JSONL 을 쓴다. 파이썬 import 로는 서로 엮이지 않음.

```
data/raw/*.jsonl                     RawInput
     │  stage1_decompose_map/runner.py::run(input, output)
     ▼
data/stage1/*.jsonl                  Stage1Output
     │  stage2_translate_rewrite/runner.py::run(input, output)
     ▼
data/stage2/*.jsonl                  Stage2Output
     │  stage3_validate/runner.py::run(input, output_dir)
     ▼
data/stage3/{accepted,rejected}.jsonl   Stage3Output
     │  stage4_report/runner.py::run(accepted, rejected, output_dir)
     ▼
data/reports/{report.*, sft.jsonl}   Stage4Sft + 리포트
```

스키마는 **layered** — `Stage2Output` 은 `Stage1Output` 의 subclass. 즉
stage 2 가 stage 1 의 필드를 지워서 쓰면 안 됨 (원본 필드 그대로 통과).

## 각 stage 가 구현할 것

### Stage 1 — `stage1_decompose_map`

파일: `decompose.py`, `cultural_map.py`, `runner.py`

- `decompose.decompose(rows)` → 영문 source_text 를 사회언어학적으로 분해
  (`Decomposed`: speech_act, register, emotion, cultural_refs, 등).
- `cultural_map.map_refs(refs)` → 각 영어 cultural_ref 에 한국어 equivalent
  (`MappedRef`) 붙이기 ("어떤 말이 이 말로 바뀐다").
- `runner.run(input, output)` → 위 둘을 엮어 `Stage1Output` JSONL 작성.

참고: `../nemo_dream_step1/` 에 거의 그대로 쓸 수 있는 구현이 있음.

### Stage 2 — `stage2_translate_rewrite`

파일: `translate.py`, `rewrite.py`, `runner.py`

- `translate.translate(row)` → 한국어 번역 초안 (→ `ko_text_draft`).
- `rewrite.rewrite(row, ko_draft, target)` → stage 1 메타 + `RewriteMeta`
  조건으로 최종 한국어 SNS 글 (→ `ko_text`).
- `runner.run(input, output)` → `Stage2Output` JSONL 작성.

Metadata 가 더 필요하면 `RewriteMeta.extra: dict` 에 자유롭게 넣기
(스키마 bump 없음).

### Stage 3 — `stage3_validate`

파일: `runner.py` (내부 구성 자유)

- `runner.run(input, output_dir)` → `Stage3Output` 을 `accepted.jsonl` /
  `rejected.jsonl` 로 분리 저장, `{"accepted": N, "rejected": M}` 반환.
- 검증 결과는 `quality: QualityScores` + `valid: bool` + `reject_reasons`
  필드로 기록. 룰 위반은 예외로 던지지 말고 `valid=False` + RejectReason
  추가.

참고: `../nemotron-test/` 의 6-stage Curator 파이프라인이 그대로 참고 가능.
파일 구조(1 파일 / 6 파일 / Hydra 등)는 owner 자유.

### Stage 4 — `stage4_report`

파일: `runner.py` (내부 구성 자유)

- `runner.run(accepted, rejected, output_dir)` → 리포트(html/json/…) +
  `sft.jsonl` (OAI-chat shape `Stage4Sft`) 생성, 경로 dict 반환.
- SFT row 는 `messages = [system, user=source_text, assistant=ko_text]`,
  `metadata.source_id == Stage3Output.id`.

참고: `data/reports/example_sft.json` 이 타겟 shape 1개 row.

## 돌리는 법

```bash
cp .env.example .env    # NVIDIA_API_KEY 채우기
uv sync
uv run pytest tests/test_schemas.py     # 반드시 통과

# stage 1개 돌리기
uv run python scripts/run_stage.py --stage 1 \
    --input data/raw/sample_input.jsonl \
    --output data/stage1/out.jsonl
```
