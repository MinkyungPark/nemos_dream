"""Stage-3 NIM client subclasses.

Each class subclasses ``nvidia_clients.NvidiaAsyncClient`` with a stage-
specific ``call(...)`` coroutine. When ``NVIDIA_API_KEY`` is not set, the
stage runner skips constructing these and falls back to the offline
deterministic stubs in each phase module — that way ``uv run pytest`` and
``scripts/run_stage3_example.py`` work with zero credentials while live
runs exercise the same code paths the hackathon submission is judged on.

Model defaults (override via env or explicit ctor arg):

- ``SAFETY_MODEL``   — ``nvidia/llama-3.1-nemoguard-8b-content-safety``
- ``JUDGE_MODEL``    — ``nvidia/nemotron-3-nano-30b-a3b``
- ``REWARD_MODEL``   — ``nvidia/nemotron-3-nano-30b-a3b``
- ``EMBED_MODEL``    — ``nvidia/llama-3.2-nv-embedqa-1b-v2``

Judge + reward were originally 120B super; stage 3 only needs 1-5 integer
scoring so we downshift to 30B nano for ~3× throughput per scoring pass
while keeping the heavy 120B super reserved for stage 1/2 generation.

The embed client uses ``langchain_nvidia_ai_endpoints.NVIDIAEmbeddings``
(Curator's reference embedder) instead of raw OpenAI — NIM's embedding
endpoint is accessed through a slightly different surface than chat.
"""

from __future__ import annotations

import json
import os
from typing import Any

from nemos_dream.nvidia_clients import NvidiaAsyncClient, NvidiaSyncClient

_JUDGE_PROMPT = """You are a senior Korean-localisation reviewer for a SODA-style dialogue dataset.
This is a **cultural rewrite**, not a translation — exact semantic equivalence with the
English source is NOT required and MUST NOT be rewarded. Score against the stage-1/2
metadata below as the ground truth.

[English source — provided only as loose context, not as the target]
{en}

[Korean rewrite — the artefact under review]
{ko}

[Ground-truth meta produced by stage 1]
register={register}  emotion={emotion}(intensity {intensity}/5)  speech_acts={speech_acts}

[Expected cultural substitutions (term → ko, from stage-1/2 mapped_refs — treat as the answer key)]
{refs}

[Assigned KR personas (from stage-2 retrieval — each speaker must sound like their persona)]
{persona}

Axes (integers 1-5, where 1 = broken, 5 = flawless). Score each axis **against the
ground-truth meta/refs/persona above**, not against the English source:

- property_preservation: the rewrite honours the given register, emotion type and
  intensity, and the listed speech_acts. If the meta says register=polite/emotion=anger
  intensity 4, a calm casual rewrite fails even if it reads well.
- naturalness: reads like natural Korean for the platform/age bracket implied by the
  persona block (e.g. campus-thread casual, office-messenger polite).
- cultural_appropriateness: every term in the expected-substitutions list appears
  idiomatically in the KR; no hallucinated refs were introduced that aren't on the list;
  the substitutions listed are themselves appropriate for KR (penalise an obviously wrong
  mapping such as a US holiday mapped to an unrelated KR term).
- register_consistency: honorific level (해요체/합쇼체/반말) stays consistent within each
  speaker's turns AND matches that speaker's persona register.
- persona_style_consistency: each speaker's lines match the age/occupation/summary of
  their assigned persona — not a generic KR voice.

Return ONLY a JSON object in this shape (no prose outside JSON):
{{"property_preservation": X,
  "naturalness": X,
  "cultural_appropriateness": X,
  "register_consistency": X,
  "persona_style_consistency": X,
  "reasoning": {{"property_preservation": "...", "naturalness": "...",
                 "cultural_appropriateness": "...", "register_consistency": "...",
                 "persona_style_consistency": "..."}}}}
"""


_JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "property_preservation": {"type": "integer", "minimum": 1, "maximum": 5},
        "naturalness": {"type": "integer", "minimum": 1, "maximum": 5},
        "cultural_appropriateness": {"type": "integer", "minimum": 1, "maximum": 5},
        "register_consistency": {"type": "integer", "minimum": 1, "maximum": 5},
        "persona_style_consistency": {"type": "integer", "minimum": 1, "maximum": 5},
        "reasoning": {"type": "object", "additionalProperties": {"type": "string"}},
    },
    "required": [
        "property_preservation",
        "naturalness",
        "cultural_appropriateness",
        "register_consistency",
        "persona_style_consistency",
    ],
}


_PER_MODEL_KEYS = ("NEMO_GUARD", "NEMO_3_SUPER", "NEMO_REWARD", "NEMO_EMBED")


def nvidia_api_key_available() -> bool:
    """True when either the blanket key or all four per-model keys are present."""
    if os.environ.get("NVIDIA_API_KEY"):
        return True
    return all(os.environ.get(k) for k in _PER_MODEL_KEYS)


class SafetyClient(NvidiaAsyncClient):
    """NeMoGuard content-safety screen.

    The hosted NIM endpoint returns a JSON envelope with categorical flags
    (``S1``–``S14`` etc. per MLCommons taxonomy). ``call`` returns ``True``
    when the payload is clean, ``False`` when any category fires.
    """

    model_env = "SAFETY_MODEL"
    api_key_env = "NEMO_GUARD"

    def __init__(self, *, model: str | None = None, **kwargs: Any) -> None:
        super().__init__(
            model=model or "nvidia/llama-3.1-nemoguard-8b-content-safety",
            **kwargs,
        )

    async def call(self, text: str) -> bool:  # type: ignore[override]
        resp = await self.openai.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": text}],
            temperature=0.0,
        )
        raw = resp.choices[0].message.content or ""
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            # NIM sometimes wraps the JSON in a code fence when refused
            return False
        for k, v in payload.items():
            if k.startswith("S") and str(v).lower() == "yes":
                return False
        return True


class JudgeClient(NvidiaAsyncClient):
    """Nemotron judge — 5 axes + per-axis reasoning via ``guided_json``."""

    model_env = "JUDGE_MODEL"
    api_key_env = "NEMO_3_SUPER"

    def __init__(self, *, model: str | None = None, **kwargs: Any) -> None:
        super().__init__(
            model=model or "nvidia/nemotron-3-nano-30b-a3b",
            **kwargs,
        )

    async def call(  # type: ignore[override]
        self,
        *,
        en: str,
        ko: str,
        register: str,
        emotion: str,
        intensity: int,
        speech_acts: list[str],
        refs: str,
        persona: str,
    ) -> dict[str, Any]:
        prompt = _JUDGE_PROMPT.format(
            en=en,
            ko=ko,
            register=register,
            emotion=emotion,
            intensity=intensity,
            speech_acts=",".join(speech_acts),
            refs=refs,
            persona=persona,
        )
        resp = await self.openai.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            extra_body={"nvext": {"guided_json": _JUDGE_SCHEMA}},
        )
        return json.loads(resp.choices[0].message.content or "{}")


_REWARD_PROMPT = """You are a reward model for a Korean cultural-rewrite pipeline.
This task is NOT translation — the Korean rewrite intentionally swaps English-culture
references for Korean-culture ones, so surface meaning with the English source will
diverge. Do NOT score on EN↔KR semantic equivalence. Score against the stage-1/2
metadata below, which is the answer key.

[English source — loose context only]
{en}

[Korean rewrite under review]
{ko}

[Ground-truth meta from stage 1]
register={register}  emotion={emotion}(intensity {intensity}/5)  speech_acts={speech_acts}

[Expected cultural substitutions (term → ko, from mapped_refs — this is the answer key)]
{refs}

[Assigned KR personas (from stage-2 retrieval)]
{persona}

Return ONLY a JSON object with two integer fields on a 1-5 scale (1 = terrible, 5 = excellent):

- correctness: How well does the KR rewrite follow the ground truth? Specifically:
  (1) every expected substitution (term → ko) is applied — and applied appropriately for
      Korean context (penalise both missing substitutions AND nonsensical/unidiomatic
      pairings in the list itself);
  (2) no cultural refs are invented that aren't on the list;
  (3) the given register, emotion type, intensity, and speech_acts are preserved;
  (4) each speaker's lines match the voice of their assigned persona (age, occupation,
      summary).
  A rewrite that preserves the English facts but ignores the substitution list or
  persona voice is WRONG for this task and must score low on correctness.

- coherence: Does the Korean dialogue read as a single coherent exchange — turn flow,
  reference resolution, tone continuity across turns — independent of the English source?

Reply with:
{{"correctness": X, "coherence": X}}
"""


_REWARD_SCHEMA = {
    "type": "object",
    "properties": {
        "correctness": {"type": "integer", "minimum": 1, "maximum": 5},
        "coherence": {"type": "integer", "minimum": 1, "maximum": 5},
    },
    "required": ["correctness", "coherence"],
}


class RewardClient(NvidiaAsyncClient):
    """Nemotron-3-Nano-30B reward-style scorer.

    History: ``nvidia/nemotron-4-340b-reward`` (original reward model) and
    the 70B-reward sibling both reached EOL in NIM's managed catalog. We
    briefly bounced to ``nemotron-3-super-120b-a12b`` as a judge-style
    replacement, but the 1-5 integer output shape doesn't benefit from
    120B — the 30B ``nemotron-3-nano-30b-a3b`` produces indistinguishable
    correctness/coherence scores at ~3× throughput, so stage 3 runs nano.
    The public return shape (``dict[str, float]``) stays unchanged.
    """

    model_env = "REWARD_MODEL"
    api_key_env = "NEMO_REWARD"

    def __init__(self, *, model: str | None = None, **kwargs: Any) -> None:
        super().__init__(
            model=model or "nvidia/nemotron-3-nano-30b-a3b",
            **kwargs,
        )

    async def call(  # type: ignore[override]
        self,
        *,
        en: str,
        ko: str,
        register: str,
        emotion: str,
        intensity: int,
        speech_acts: list[str],
        refs: str,
        persona: str,
    ) -> dict[str, float]:
        prompt = _REWARD_PROMPT.format(
            en=en,
            ko=ko,
            register=register,
            emotion=emotion,
            intensity=intensity,
            speech_acts=",".join(speech_acts),
            refs=refs,
            persona=persona,
        )
        resp = await self.openai.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            extra_body={"nvext": {"guided_json": _REWARD_SCHEMA}},
        )
        payload = json.loads(resp.choices[0].message.content or "{}")
        scores: dict[str, float] = {}
        for k in ("correctness", "coherence"):
            v = payload.get(k)
            if isinstance(v, int):
                scores[k] = float(v)
        return scores


class EmbedClient(NvidiaSyncClient):
    """NV-Embed wrapper using ``langchain_nvidia_ai_endpoints.NVIDIAEmbeddings``.

    Sync on purpose — Curator's embedder call patterns are sync and phase
    4 (intra-KR coherence) batches per-row, so the async surface would only
    add overhead. Raises at import-time only when ``embed`` is invoked
    without the NV AI endpoints package installed.
    """

    model_env = "EMBED_MODEL"
    api_key_env = "NEMO_EMBED"

    def __init__(self, *, model: str | None = None, **kwargs: Any) -> None:
        super().__init__(
            model=model or "nvidia/llama-3.2-nv-embedqa-1b-v2",
            **kwargs,
        )
        self._lc_embed: Any = None

    @property
    def langchain(self) -> Any:
        if self._lc_embed is None:
            from langchain_nvidia_ai_endpoints import NVIDIAEmbeddings

            self._lc_embed = NVIDIAEmbeddings(
                model=self.model,
                api_key=self._api_key(),
                base_url=self.base_url,
            )
        return self._lc_embed

    def call(self, texts: list[str]) -> list[list[float]]:  # type: ignore[override]
        return [list(v) for v in self.langchain.embed_documents(texts)]

    def embed_fn(self):
        """Return a plain ``Callable[[list[str]], list[list[float]]]``.

        Each phase module expects a naked callable, not a client instance,
        so they can stay decoupled from NVIDIA plumbing and unit-test with a
        lambda.
        """

        return lambda texts: self.call(texts)


def build_default_clients() -> dict[str, Any]:
    """Lazy-construct every stage-3 NIM client when ``NVIDIA_API_KEY`` is set.

    Returns a dict suitable for splatting into ``runner.run_async``::

        runner.run_async(input_path, out_dir, **build_default_clients())

    When the key is missing, returns ``{}`` so the runner's offline stubs
    kick in transparently.
    """

    if not nvidia_api_key_available():
        return {}

    safety = SafetyClient()
    judge = JudgeClient()
    reward = RewardClient()
    embed = EmbedClient()

    async def safety_fn(text: str) -> bool:
        return await safety.call(text)

    async def judge_fn(**kw: Any) -> dict[str, Any]:
        return await judge.call(**kw)

    async def reward_fn(**kw: Any) -> dict[str, float]:
        return await reward.call(**kw)

    return {
        "safety_fn": safety_fn,
        "judge_fn": judge_fn,
        "reward_fn": reward_fn,
        "embed_fn": embed.embed_fn(),
    }
