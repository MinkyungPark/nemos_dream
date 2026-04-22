"""Stage 3 runner import smoke test."""

from __future__ import annotations

import inspect

from nemos_dream.stage3_validate import runner


def test_runner_public_api():
    """``runner.run_async`` is async, accepts the documented kwargs."""
    sig = inspect.signature(runner.run_async)
    params = set(sig.parameters)
    assert {
        "input_path",
        "output_dir",
        "embed_fn",
        "judge_fn",
        "reward_fn",
        "safety_fn",
        "pii_fn",
        "run_self_verify",
    } <= params
    assert inspect.iscoroutinefunction(runner.run_async)
