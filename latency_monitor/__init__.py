"""Latency Monitor application package."""

__all__ = ["App", "app"]


def __getattr__(name: str):
    """Load the application module only when its public objects are requested."""
    if name == "App":
        from .latency_monitor import App

        return App
    if name == "app":
        from .latency_monitor import app

        return app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
