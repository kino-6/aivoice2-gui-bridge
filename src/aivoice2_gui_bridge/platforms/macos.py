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
    app_bundle_id: str | None = "jp.ai-j.AIVoice2"

    def activate_app(self, app_name: str) -> None:
        script = f'tell application "{app_name}" to activate'
        applescript_error: str | None = None
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
            applescript_error = exc.stderr.strip() if exc.stderr else "no stderr"

        if self.app_bundle_id:
            try:
                subprocess.run(
                    ["open", "-b", self.app_bundle_id],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as exc:
                stderr = exc.stderr.strip() if exc.stderr else "no stderr"
                if applescript_error is not None:
                    raise AppActivationError(
                        f'Failed to activate app "{app_name}". If the app name differs on your system, pass '
                        f"--app-name. AppleScript error: {applescript_error}. open -b {self.app_bundle_id} "
                        f"error: {stderr}"
                    ) from exc
                raise AppActivationError(
                    f'Failed to activate app bundle "{self.app_bundle_id}". open error: {stderr}'
                ) from exc
        elif applescript_error is not None:
            raise AppActivationError(
                f'Failed to activate app "{app_name}". If the app name differs on your system, pass --app-name. '
                f"AppleScript error: {applescript_error}"
            )
        time.sleep(self.activation_delay)

    def paste_hotkey(self) -> tuple[str, ...]:
        return tuple(self.paste_hotkey_keys)

    def default_app_name(self) -> str:
        return "AIVoice2"

    def permission_guidance(self) -> str:
        return (
            "Grant Accessibility permission to the terminal, IDE, or Python runner that launches this tool.\n"
            "Grant Screen Recording permission to that same app so image matching can inspect the screen.\n"
            "Restart the terminal/IDE after changing permissions."
        )

    def set_window_bounds(
        self,
        app_name: str,
        *,
        position: tuple[int, int] | None = None,
        size: tuple[int, int] | None = None,
    ) -> None:
        if position is None and size is None:
            return

        commands: list[str] = []
        if position is not None:
            left, top = position
            commands.append(f"set position of front window to {{{left}, {top}}}")
        if size is not None:
            width, height = size
            commands.append(f"set size of front window to {{{width}, {height}}}")

        script = self._system_events_window_script("\n".join(commands), app_name)
        self._run_system_events_script(script, f'Failed to resize or move app "{app_name}".')
        time.sleep(self.activation_delay)

    def get_window_origin(self, app_name: str) -> tuple[int, int]:
        script = self._system_events_window_script("get position of front window", app_name)
        result = self._run_system_events_script(script, f'Failed to read window position for app "{app_name}".')
        parts = [part.strip() for part in result.stdout.strip().split(",")]
        if len(parts) != 2:
            raise AppActivationError(f"Unexpected window position response: {result.stdout.strip()!r}")
        try:
            return (int(parts[0]), int(parts[1]))
        except ValueError as exc:
            raise AppActivationError(f"Unexpected window position response: {result.stdout.strip()!r}") from exc

    def _system_events_window_script(self, command: str, app_name: str) -> str:
        if self.app_bundle_id:
            process_selector = f'first application process whose bundle identifier is "{self.app_bundle_id}"'
        else:
            process_selector = f'application process "{app_name}"'
        return "\n".join(
            [
                'tell application "System Events"',
                f"  tell {process_selector}",
                f"    {command}",
                "  end tell",
                "end tell",
            ]
        )

    @staticmethod
    def _run_system_events_script(script: str, error_prefix: str) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            stderr = exc.stderr.strip() if exc.stderr else "no stderr"
            raise AppActivationError(f"{error_prefix} System Events error: {stderr}") from exc
