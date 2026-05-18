from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import subprocess
import time


class AppActivationError(RuntimeError):
    """Raised when A.I.VOICE2 Editor cannot be activated."""


@dataclass(slots=True)
class MacOSPlatformController:
    """macOS GUI automation primitives."""

    paste_hotkey_keys: Sequence[str] = ("command", "v")
    activation_delay: float = 0.5

    def activate_app(self, app_name: str) -> None:
        script = f'tell application "{app_name}" to activate'
        try:
            subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise AppActivationError("Could not run osascript. This backend currently requires macOS.") from exc
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else "no stderr"
            raise AppActivationError(
                f'Failed to activate app "{app_name}". If the app name differs on your system, pass --app-name. '
                f"AppleScript error: {stderr}"
            ) from exc
        time.sleep(self.activation_delay)

    def paste_hotkey(self) -> tuple[str, ...]:
        return tuple(self.paste_hotkey_keys)

    def default_app_name(self) -> str:
        return "A.I.VOICE2 Editor"

    def permission_guidance(self) -> str:
        return (
            "Grant Accessibility permission to the terminal, IDE, or Python runner that launches this tool.\n"
            "Grant Screen Recording permission to that same app so image matching can inspect the screen.\n"
            "Restart the terminal/IDE after changing permissions."
        )
