"""Lightweight compatibility wrappers for optional third‑party libraries.

The full roadmap references *pydantic* and *fastapi*.  These libraries may not
be available in the execution environment.  Importing them unconditionally
would crash the program and the test‑suite.  Instead we try to import the real
package and, if that fails, fall back to **tiny in‑house stubs** that provide
just enough behaviour for our uses.
"""

from __future__ import annotations

import types
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, Generic, TypeVar

T = TypeVar("T")


# ---------------------------------------------------------------------------
# Pydantic fallback
# ---------------------------------------------------------------------------


try:
    import pydantic  # type: ignore  # noqa: F401

    BaseModel = pydantic.BaseModel  # noqa: N806 – mimic pydantic naming
except ModuleNotFoundError:  # pragma: no cover – executed in slim envs only.

    class _BaseModelMeta(type):
        """Meta‑class that adds `.model_dump()` and `.model_validate()`."""

        def __new__(mcls, name, bases, namespace):  # noqa: D401
            cls = super().__new__(mcls, name, bases, namespace)
            return dataclass(cls)  # type: ignore[arg-type]

    class BaseModel(metaclass=_BaseModelMeta):  # type: ignore[misc]
        """Very small subset of *pydantic*'s :class:`BaseModel`."""

        def model_dump(self) -> Dict[str, Any]:  # noqa: D401
            """Return a ``dict`` representation akin to *pydantic*."""

            return asdict(self)  # type: ignore[arg-type]

        @classmethod
        def model_validate(cls, obj: Any) -> "BaseModel":  # noqa: D401
            """Create an instance from *anything* reasonably dict‑like."""

            if isinstance(obj, cls):
                return obj
            if isinstance(obj, dict):
                return cls(**obj)  # type: ignore[arg-type]
            raise TypeError("Unsupported type for model_validate")

        # Parity helper with real Pydantic v2 API
        @classmethod
        def model_construct(cls, **kwargs: Any):  # noqa: D401
            return cls(**kwargs)


# ---------------------------------------------------------------------------
# FastAPI fallback
# ---------------------------------------------------------------------------


try:
    import fastapi as fastapi_module  # type: ignore  # noqa: F401

except ModuleNotFoundError:  # pragma: no cover – executed in slim envs only.

    class _Route(Generic[T]):
        def __init__(self, func: Callable[..., T]):
            self.func = func

        def __call__(self, *args: Any, **kwargs: Any) -> T:  # noqa: D401
            return self.func(*args, **kwargs)

    class FastAPI:  # noqa: D101 – lightweight stub only
        def __init__(self):
            self.routes: Dict[tuple[str, str], Callable[..., Any]] = {}

        def get(self, path: str) -> Callable[[Callable[..., T]], Callable[..., T]]:  # noqa: D401
            return self._register("GET", path)

        def post(self, path: str) -> Callable[[Callable[..., T]], Callable[..., T]]:  # noqa: D401
            return self._register("POST", path)

        def _register(self, method: str, path: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
            def decorator(func: Callable[..., T]) -> Callable[..., T]:
                self.routes[(method, path)] = func
                return func

            return decorator

    # create a dummy fastapi module with FastAPI inside so that ``import
    # fastapi`` works even though a real install is not present.
    fastapi_module = types.ModuleType("fastapi")  # type: ignore[assignment]
    fastapi_module.FastAPI = FastAPI  # type: ignore[attr-defined]
    import sys

    sys.modules["fastapi"] = fastapi_module

# Re‑export FastAPI so that downstream code can ``from qmag_nav._compat import
# FastAPI`` regardless of whether the real package is installed.

from fastapi import FastAPI  # type: ignore  # noqa: E402  pylint: disable=wrong-import-position

__all__ = [
    "BaseModel",
    "FastAPI",
]
