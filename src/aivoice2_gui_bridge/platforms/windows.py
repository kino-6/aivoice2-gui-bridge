from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .base import UnsupportedPlatformError


@dataclass(slots=True)
class WindowsPlatformController:
    """Windows placeholder backend."""

    paste_hotkey_keys: Sequence[str] = ("ctrl", "v")

    def activate_app(self, app_name: str) -> None:
        raise UnsupportedPlatformError(
            f'Windows app activation is not implemented yet for "{app_name}". '
            "Windows support is planned/experimental; use the macOS backend for current automation."
        )

    def paste_hotkey(self) -> tuple[str, ...]:
        return tuple(self.paste_hotkey_keys)

    def default_app_name(self) -> str:
        return "A.I.VOICE2 Editor"

    def permission_guidance(self) -> str:
        return (
            "Windows support is planned/experimental.\n"
            "The placeholder backend uses Ctrl+V as the paste hotkey, but app activation is not implemented yet."
        )

    def set_window_bounds(
        self,
        app_name: str,
        *,
        position: tuple[int, int] | None = None,
        size: tuple[int, int] | None = None,
    ) -> None:
        raise UnsupportedPlatformError(
            f'Windows window positioning is not implemented yet for "{app_name}".'
        )

    def get_window_origin(self, app_name: str) -> tuple[int, int]:
        raise UnsupportedPlatformError(
            f'Windows window origin lookup is not implemented yet for "{app_name}".'
        )
