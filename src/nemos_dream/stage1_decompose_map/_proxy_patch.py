"""Make ``httpx`` with a custom transport (as Data Designer builds it) honour
``HTTP_PROXY`` / ``HTTPS_PROXY`` environment variables.

When ``httpx.Client`` is constructed with an explicit ``transport=`` argument,
httpx skips its automatic proxy discovery from env vars. Data Designer builds
its own ``HTTPTransport`` so it can attach a retry wrapper, so without this
patch DD cannot reach external endpoints from inside networks that require a
proxy (e.g. the SK Telecom internal corp network at ``10.40.21.71:3128``).

Direct ``openai`` SDK usage is unaffected because its default client has no
custom transport and httpx picks up the env vars normally.

The patch is idempotent and a no-op when no proxy env var is set, so it is
safe to call on every stage-1 entrypoint regardless of environment.
"""

from __future__ import annotations

import os

_APPLIED = False


def _proxy_url() -> str | None:
    return (
        os.environ.get("HTTPS_PROXY")
        or os.environ.get("https_proxy")
        or os.environ.get("HTTP_PROXY")
        or os.environ.get("http_proxy")
    )


def _patch_httpx() -> None:
    try:
        import httpx
    except ImportError:
        return
    proxy = _proxy_url()
    if not proxy:
        return

    for cls_name in ("AsyncHTTPTransport", "HTTPTransport"):
        cls = getattr(httpx, cls_name, None)
        if cls is None:
            continue
        orig = cls.__init__
        if getattr(orig, "__nemos_dream_patched__", False):
            continue

        def _make_wrapper(_orig):  # noqa: ANN001 — wrapper over arbitrary __init__
            def _wrapped(self, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
                if "proxy" not in kwargs and "mounts" not in kwargs:
                    kwargs["proxy"] = proxy
                return _orig(self, *args, **kwargs)

            _wrapped.__nemos_dream_patched__ = True  # type: ignore[attr-defined]
            return _wrapped

        cls.__init__ = _make_wrapper(orig)  # type: ignore[assignment]


def apply_proxy_patches() -> None:
    """Patch ``httpx.HTTPTransport`` / ``AsyncHTTPTransport`` once per process."""
    global _APPLIED
    if _APPLIED:
        return
    _patch_httpx()
    _APPLIED = True
