"""Factories for NVIDIA-hosted clients (NIM, Retriever, judge, safety, reward).

Every stage should call these factories instead of instantiating ``OpenAI()``
ad-hoc — so auth / proxy / base-url changes happen in one place.

All endpoints are OpenAI-compatible and routed through
``https://integrate.api.nvidia.com/v1`` by default.
"""

from __future__ import annotations

from typing import Any

from openai import AsyncOpenAI, OpenAI


def nim_client(*, model_env: str = "NEMOTRON_MODEL") -> tuple[OpenAI, str]:
    """Return ``(client, model_id)`` for a synchronous NIM endpoint."""
    raise NotImplementedError("shared owner: implement")


def nim_async_client(*, model_env: str = "NEMOTRON_MODEL") -> tuple[AsyncOpenAI, str]:
    """Async variant of :func:`nim_client` — used by stage 3 judge/safety calls."""
    raise NotImplementedError("shared owner: implement")


def retriever_client() -> Any:
    """Return a NeMo Retriever embedding client (Korean-capable)."""
    raise NotImplementedError("shared owner: implement")


def judge_client() -> tuple[AsyncOpenAI, str]:
    """LLM-judge client. Uses ``NEMOTRON_JUDGE_MODEL`` (70B by default)."""
    raise NotImplementedError("shared owner: implement")


def safety_client() -> tuple[AsyncOpenAI, str]:
    """NeMoGuard content-safety client. Uses ``NEMOTRON_SAFETY_MODEL``."""
    raise NotImplementedError("shared owner: implement")


def reward_client() -> tuple[AsyncOpenAI, str]:
    """Nemotron-4-340B-Reward client for stage-3 final ranking."""
    raise NotImplementedError("shared owner: implement")
