"""Corporate-proxy monkey-patch for aiohttp / httpx.

Call :func:`apply_proxy_patches` once at the top of any entrypoint that talks
to ``build.nvidia.com`` from inside a corporate network. Safe no-op if no
``HTTPS_PROXY`` env var is set.

Adapted from ``../nemo_dream_step1/src/proxy_patch.py``.
"""

from __future__ import annotations


def apply_proxy_patches() -> bool:
    """Monkey-patch aiohttp + httpx to honour ``HTTPS_PROXY``.

    Returns ``True`` if a patch was applied, ``False`` if no proxy env was set.
    """
    raise NotImplementedError("shared owner: implement")
