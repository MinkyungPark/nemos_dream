"""Adapter between our ``Stage`` ABC and NeMo Curator ``ProcessingStage``.

Lifted-in-spirit from ``../nemotron-test/pipeline/curator_bridge.py``. The
adapter wraps each stage so the whole pipeline can run under Curator's
``RayActorPoolExecutor`` for parallelism, while still being unit-testable
via the lightweight ``Pipeline`` runner in :mod:`.runner`.
"""

from __future__ import annotations

from typing import Any


def to_curator_stage(stage: Any) -> Any:
    """Wrap a :class:`stages.base.Stage` instance as a Curator ProcessingStage."""
    raise NotImplementedError("stage 3 owner: implement")
