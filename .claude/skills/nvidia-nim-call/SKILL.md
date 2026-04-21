---
name: nvidia-nim-call
description: Use this skill when code needs to call a NVIDIA NIM endpoint — LLM chat, embedding, judge, safety, or reward model. Covers the OpenAI-compatible client pattern, `nvext.guided_json` structured output, async usage for stage 3, and temperature conventions.
---

# Calling NVIDIA NIM from nemos_dream code

All NIM endpoints are OpenAI-compatible and reached through
`https://integrate.api.nvidia.com/v1`. Auth is `NVIDIA_API_KEY`.

## Always use the factory

```python
# ✅ do
from nemos_dream.nvidia_clients import nim_client, nim_async_client
client, model = nim_client()
response = client.chat.completions.create(model=model, messages=[...])

# ❌ don't
from openai import OpenAI
client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=...)
```

Factories encapsulate base URL, API key loading, and sensible defaults
(retries, timeouts). One place to fix it when NVIDIA changes an endpoint.

## Models cheat sheet

| Need | Model | Factory |
|---|---|---|
| General chat / extraction | `nvidia/nemotron-3-nano-30b-a3b` | `nim_client()` / `nim_async_client()` |
| Final rewrite pass (quality) | `nvidia/nemotron-3-super-120b-a12b` | `nim_client(model_env='NEMOTRON_SUPER_MODEL')` |
| LLM judge | `nvidia/llama-3.1-nemotron-70b-instruct` | `judge_client()` |
| Content safety | `nvidia/llama-3.1-nemoguard-8b-content-safety` | `safety_client()` |
| Reward ranking | `nvidia/nemotron-4-340b-reward` | `reward_client()` |
| Embeddings | `nvidia/llama-3.2-nv-embedqa-1b-v2` (KR-capable) | `retriever_client()` |

## Structured output (guided JSON)

When you need JSON that matches a Pydantic model:

```python
from nemos_dream.schemas import Decomposed

schema = Decomposed.model_json_schema()
resp = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": prompt}],
    temperature=0.2,
    extra_body={"nvext": {"guided_json": schema}},
)
raw = resp.choices[0].message.content
# Enum enforcement is SOFT — always normalize before validating.
normalized = _normalize_aliases(json.loads(raw))
decomposed = Decomposed.model_validate(normalized)
```

Look at `../nemo_dream_step1/src/part1_decompose/nim_guided_json.py::_normalize`
for the reference alias-map + range-clamp logic.

## Async for stage 3

Stage 3's judge / safety / reward calls fan out row-by-row. Use
`nim_async_client()` + `asyncio.gather` with a concurrency cap:

```python
import asyncio
sem = asyncio.Semaphore(16)
async def score_one(row):
    async with sem:
        return await judge.score(row)
results = await asyncio.gather(*(score_one(r) for r in rows))
```

## Temperature

| Use case | Temperature |
|---|---|
| Structured extraction | 0.2 |
| Creative rewrite | 0.9 |
| Judge / safety / reward | 0.0 |

## Rate limits & retries

NVIDIA Build throttles on bursts. The factory sets `max_retries=3,
timeout=60` by default. If you hit 429s in production, prefer lowering the
`asyncio.Semaphore` cap before bumping `max_retries`.
