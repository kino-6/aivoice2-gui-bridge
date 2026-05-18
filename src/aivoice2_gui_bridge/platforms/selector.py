from __future__ import annotations

import platform as platform_module

from .base import PlatformController, UnsupportedPlatformError
from .macos import MacOSPlatformController
from .windows import WindowsPlatformController

PlatformName = str


def create_platform_controller(
    platform_name: PlatformName = "auto",
    *,
    activation_delay: float = 0.5,
    paste_hotkey_keys: tuple[str, ...] | None = None,
    system_name: str | None = None,
) -> PlatformController:
    """Create a platform controller from a CLI/config platform name."""
    normalized = platform_name.lower()
    if normalized == "auto":
        normalized = platform_name_for_system(system_name)

    if normalized == "macos":
        return MacOSPlatformController(
            paste_hotkey_keys=paste_hotkey_keys or ("command", "v"),
            activation_delay=activation_delay,
        )
    if normalized == "windows":
        return WindowsPlatformController(paste_hotkey_keys=paste_hotkey_keys or ("ctrl", "v"))

    raise UnsupportedPlatformError(
        f"Unsupported platform '{platform_name}'. Use one of: auto, macos, windows."
    )


def platform_name_for_system(system_name: str | None = None) -> str:
    system = system_name if system_name is not None else platform_module.system()
    if system == "Darwin":
        return "macos"
    if system == "Windows":
        return "windows"
    raise UnsupportedPlatformError(
        f"Unsupported operating system '{system}'. Use --platform macos or --platform windows explicitly."
    )
