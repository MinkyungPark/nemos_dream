# Stage owner 구현 가이드

4명이 각 stage 하나씩 담당. 이 문서만 보면 자기 stage를 처음부터 끝까지
혼자 구현할 수 있도록 요약해둔 것. 긴 설명은 `architecture.md`,
`stage-contracts.md`, 각 stage의 `README.md` 참고.

## 0. 공통 준비 (모든 팀원)

```bash
git clone <repo> && cd nemos_dream
cp .env.example .env
# .env 에서 NVIDIA_API_KEY 설정 (https://build.nvidia.com)
uv sync --extra stage<N>          # 내 stage만 설치
uv run pytest tests/test_schemas.py   # 반드시 통과해야 함
```

**Claude 쓸 때:** 커밋 전 `.claude/skills/stage-module`, 스키마 수정이면
`update-schema`, NIM 호출이면 `nvidia-nim-call`, 의존성이면 `uv-workflow`
skill을 참고.

## 1. 절대 규칙 (모든 stage 공통)

1. **Schema 는 곧 계약.** 내 stage 의 input/output 은 `src/nemos_dream/schemas.py`
   의 Pydantic 모델로 고정됨. 필드 이름/타입 바꾸지 말것.
   - 새 필드가 꼭 필요하면 `update-schema` skill 먼저 읽기.
   - Stage 2 는 `RewriteMeta.extra: dict` 라는 자유 슬롯이 있으니 ad-hoc
     metadata 는 여기에 담아도 됨 (스키마 bump 없음).
2. **다른 stage 파일은 건드리지 말 것.** `schemas.py`, `nvidia_clients.py`,
   `io_utils.py` 같은 공용 파일은 그룹 공지 후에만 수정.
3. **OpenAI 클라이언트는 factory 통해서만.** `nvidia_clients.py` 의
   `nim_client()`, `judge_client()` 등을 사용. `OpenAI(...)` 직접 호출 금지.
4. **비밀키 커밋 금지.** `.env` 는 gitignore 되어 있음.
5. **Runner 는 하나.** 각 stage 의 `runner.run(...)` 가 유일한 외부 진입점.
   내부 파일 구조는 자유.

## 2. Stage 별 To-Do

### Stage 1 — `stage1_decompose_map` (사회언어학적 분해 + 문화적 요소 추가)

Input `RawInput` → Output `Stage1Output`.

- `decompose.py::decompose(rows)` 구현 → `Decomposed` 리스트 반환
  (speech_act, register, emotion, internet_markers, cultural_refs, …)
- `cultural_map.py::map_refs(refs)` 구현 → 각 영어 cultural_ref 에 한국어
  equivalent(MappedRef) 붙이기 ("어떤 말이 이 말로 바뀐다")
- `runner.py::run(input_path, output_path)` 에서 두 단계를 엮어 JSONL 출력

참고 구현: `../nemo_dream_step1/` (거의 그대로 가져올 수 있음).
사용 가능 툴: NeMo Data Designer, NIM `nvext.guided_json`, NeMo Retriever,
Tavily, NeMo Agent Toolkit (선택).

### Stage 2 — `stage2_translate_rewrite` (번역 → rewrite post-processing)

Input `Stage1Output` → Output `Stage2Output`.

- `translate.py::translate(row)` 구현 → `row.source_text` 의 한국어 번역
  초안 반환. `Stage2Output.ko_text_draft` 로 저장됨.
- `rewrite.py::rewrite(row, ko_draft, target)` 구현 → stage-1 메타
  (cultural, register, age_group, markers, …) + `RewriteMeta` 를 조건으로
  최종 한국어 SNS 글 생성. `Stage2Output.ko_text` 로 저장됨.
- 새 targeting 메타데이터가 필요하면 `RewriteMeta.extra` dict 에 넣기
  (예: `extra={"tone_hint": "warm"}`). 반복적으로 쓰이면 나중에 정식 필드로
  승격.

참고 구현: `draft_plan.md` 의 step 3, 4 (reference repo 없음 — 새로 짜는 부분).
사용 가능 툴: NIM (Nemotron Nano / Super), HF `Nemotron-Personas-Korea`.

### Stage 3 — `stage3_validate` (품질 검증 + 필터)

Input `Stage2Output` → Output `Stage3Output` (accepted/rejected 두 JSONL).

- `runner.py::run(input_path, output_dir)` 가 유일한 필수 진입점.
  `accepted.jsonl` + `rejected.jsonl` 로 분리 저장, `{"accepted": N,
  "rejected": M}` 반환.
- 내부 구성은 자유 — 6-stage Curator pipeline 으로 가든, 평평한 순차 검증기로
  가든, Hydra-driven graph 로 가든 OK. 스키마 invariants 만 지키면 됨.
- Rejection 은 예외로 던지지 말고 `valid=False` + `RejectReason` 추가로
  표현. 네트워크 같은 인프라 에러만 raise.
- 임계값/모델 이름은 `configs/stage3/filter.yaml` 에 둠. 필드는 자유롭게
  추가/제거.

참고 구현: `../nemotron-test/` (6-stage Curator pipeline 통째로 가져올 수
있음). 사용 가능 툴: NeMo Curator, NeMoGuard, Nemotron-70B judge, NV-Embed,
Nemotron-4-340B-Reward.

### Stage 4 — `stage4_report` (리포트 + SFT 수출)

Input `Stage3Output` × 2 (accepted, rejected) → Output report + `Stage4Sft`.

- `runner.py::run(accepted_path, rejected_path, output_dir)` 가 유일한 필수
  진입점. 리포트(`report.html/json`) 와 `sft.jsonl` 경로를 dict 로 반환.
- `Stage4Sft.messages` 는 system/user/assistant 3개. user=source_text,
  assistant=ko_text, system=`configs/stage4/report.yaml` 에 정의.
- `Stage4Sft.metadata.source_id` = 원본 `Stage3Output.id`.
- 내부 파일 구성 자유 (metrics, viz, export 쪼개든 한 파일에 다 넣든).

참고 구현: 없음 — 새로 짬. 사용 가능 툴: matplotlib/plotly/jinja2/rich
(모두 `pyproject.toml` 에 포함됨). `data/reports/example_sft.json` 이 SFT
row 의 타겟 shape.

## 3. 테스트

- 구현 후 `tests/stage<N>/` 에 본인 테스트 추가.
- `tests/test_schemas.py` 는 스키마 건드린 경우에만 갱신 (fixture 도 같이).
- 전체 돌릴 때:
  ```bash
  uv run pytest tests/
  uv run ruff check src/nemos_dream/stage<N>_*/
  ```

## 4. 커밋 / PR

- 커밋 메시지 prefix: stage 안 바꿈은 `stage<N>: ...`, 공용 파일은
  `shared: ...`, infra/config/scripts 는 `infra: ...`.
- PR 은 stage 단위로 쪼개기. 공용 파일 수정은 별도 PR 로 분리.

## 5. 막히면

- 스키마 관련 → `.claude/skills/update-schema/SKILL.md`
- NIM 호출 관련 → `.claude/skills/nvidia-nim-call/SKILL.md`
- uv / pyproject → `.claude/skills/uv-workflow/SKILL.md`
- NVIDIA 모델/endpoint 표 → `.claude/docs/nvidia-stack.md`
- 원본 기획 문서 → `draft_plan.md`
