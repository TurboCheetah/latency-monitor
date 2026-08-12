"""Access to the process-wide application instance.

The task and route modules need the same configured App without importing the
module that registers those modules while it is still being initialised.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .latency_monitor import App

_app: App | None = None


def set_app(app: App) -> None:
    """Register the application instance created during package startup."""
    global _app
    _app = app


def get_app() -> App:
    """Return the process-wide application instance."""
    global _app
    if _app is None:
        from .latency_monitor import app

        _app = app
    return _app
