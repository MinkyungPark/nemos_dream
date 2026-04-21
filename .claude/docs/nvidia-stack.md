# NVIDIA stack reference

Every component is OpenAI-compatible and reached through
`https://integrate.api.nvidia.com/v1` (aka build.nvidia.com). Auth is
`NVIDIA_API_KEY`.

## Per-stage tool map

| Stage | Tool | Model ID | Env var | Purpose |
|---|---|---|---|---|
| 1 | **NIM** (primary via Data Designer; fallback direct) | `nvidia/nemotron-3-nano-30b-a3b` | `NEMOTRON_MODEL` | Sociolinguistic decomposition |
| 1 | **NeMo Data Designer** (`data-designer` pip pkg) | same | — | Structured batch generation with Pydantic schema |
| 1 | **NeMo Retriever** | `nvidia/llama-3.2-nv-embedqa-1b-v2` | `RETRIEVER_MODEL` | Korean-capable embedding for dict fuzzy-match |
| 1 | **NeMo Agent Toolkit** (`nvidia-nat[langchain]`, opt-in) | same as above | `MAP_REFS_USE_NAT=1` | ReAct agent for cultural mapping |
| 1 | Tavily (web search) | — | `TAVILY_API_KEY` | Web-grounded cultural fallback |
| 2 | **NIM** | `nvidia/nemotron-3-nano-30b-a3b` (or super-120b final pass) | `NEMOTRON_MODEL` | Korean rewriting |
| 2 | HF dataset | `nvidia/Nemotron-Personas-Korea` | — | Persona-based style scale-up |
| 3 | **NeMo Curator** (`nemo-curator`) | — | — | Pipeline / Ray executor / dedup modules |
| 3 | **NeMoGuard** (via NIM) | `nvidia/llama-3.1-nemoguard-8b-content-safety` | `NEMOTRON_SAFETY_MODEL` | Content safety |
| 3 | NeMoGuard Jailbreak (via NIM) | `nemoguard-jailbreak-detect` | — | Seed-prompt classifier |
| 3 | Presidio | — | — | PII regex (KR_RRN, KR_PHONE, CARD) |
| 3 | **NIM** (LLM judge) | `nvidia/llama-3.1-nemotron-70b-instruct` | `NEMOTRON_JUDGE_MODEL` | 4-axis rubric score |
| 3 | NV-Embed | `nvidia/nv-embedqa-e5-v5` | — | Semantic dedup cosine |
| 3 | **NIM** (reward) | `nvidia/nemotron-4-340b-reward` | `NEMOTRON_REWARD_MODEL` | Final ranking |
| 4 | — | — | — | Pure analysis / rendering |

## Client factories

Always call factories from `src/nemos_dream/nvidia_clients.py` rather than
constructing `OpenAI()` / `AsyncOpenAI()` directly:

| Factory | Returns |
|---|---|
| `nim_client(model_env=...)` | `(OpenAI, model_id)` |
| `nim_async_client(model_env=...)` | `(AsyncOpenAI, model_id)` |
| `retriever_client()` | Retriever embedding client |
| `judge_client()` | `(AsyncOpenAI, judge_model_id)` |
| `safety_client()` | `(AsyncOpenAI, safety_model_id)` |
| `reward_client()` | `(AsyncOpenAI, reward_model_id)` |

## Temperature conventions

| Use case | Temperature |
|---|---|
| Structured extraction (stage 1 decompose) | 0.2 |
| Rewriting (stage 2) | 0.9 |
| Judge (stage 3 S4) | 0.0 |
| Safety / PII classifier | 0.0 |

## Structured output

Stage 1 fallback and any direct NIM call that needs JSON use
`extra_body={"nvext": {"guided_json": <json_schema>}}` (XGrammar). Enum
enforcement is soft — always normalise the output with an alias-map pass
before `model_validate`. See the reference logic in
`../nemo_dream_step1/src/part1_decompose/nim_guided_json.py` under `_normalize()`.

## Hackathon deliverable hints

From the Track C brief (hackathon materials):

* Nano (30B / 3B active) for resource-constrained; Super (120B / 12B active)
  for production. Default: Nano for dev, Super for the final judged run.
* Temperature 0.9 for creative generation, 0.1 for precise reasoning.
* Inference either local vLLM or NVIDIA Build endpoints — this repo uses the
  endpoints exclusively (no local GPU assumed).
* Required outputs: functional pipeline (YAML + Python), generated dataset
  with quality scores, validation metrics, schema/methodology docs.
