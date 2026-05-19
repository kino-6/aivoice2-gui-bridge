from __future__ import annotations

from typing import Protocol


class UnsupportedPlatformError(RuntimeError):
    """Raised when the requested platform backend is not available."""


class PlatformController(Protocol):
    """Platform-specific GUI operations."""

    def activate_app(self, app_name: str) -> None:
        """Bring an application to the foreground."""

    def paste_hotkey(self) -> tuple[str, ...]:
        """Return the platform paste hotkey."""

    def default_app_name(self) -> str:
        """Return the default application name for this platform."""

    def permission_guidance(self) -> str:
        """Return platform-specific setup and permission guidance."""

    def set_window_bounds(
        self,
        app_name: str,
        *,
        position: tuple[int, int] | None = None,
        size: tuple[int, int] | None = None,
    ) -> None:
        """Set the app window position and/or size."""

    def get_window_origin(self, app_name: str) -> tuple[int, int]:
        """Return the app window's top-left screen position."""
