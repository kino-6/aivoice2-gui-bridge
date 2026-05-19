from __future__ import annotations

import pytest

from aivoice2_gui_bridge.platforms.base import UnsupportedPlatformError
from aivoice2_gui_bridge.platforms.macos import AppActivationError, MacOSPlatformController
from aivoice2_gui_bridge.platforms.selector import create_platform_controller, platform_name_for_system
from aivoice2_gui_bridge.platforms.windows import WindowsPlatformController


def test_platform_auto_selects_macos_for_darwin() -> None:
    controller = create_platform_controller("auto", system_name="Darwin")

    assert isinstance(controller, MacOSPlatformController)


def test_platform_auto_selects_windows_for_windows() -> None:
    controller = create_platform_controller("auto", system_name="Windows")

    assert isinstance(controller, WindowsPlatformController)


def test_platform_auto_rejects_unsupported_system() -> None:
    with pytest.raises(UnsupportedPlatformError, match="Unsupported operating system"):
        platform_name_for_system("Linux")


def test_macos_paste_hotkey_and_guidance() -> None:
    controller = MacOSPlatformController()

    assert controller.paste_hotkey() == ("command", "v")
    assert controller.default_app_name() == "AIVoice2"
    assert "Accessibility" in controller.permission_guidance()
    assert "Screen Recording" in controller.permission_guidance()


def test_macos_activation_uses_applescript_and_bundle_fallback(monkeypatch) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> object:
        calls.append(cmd)
        return object()

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr("time.sleep", lambda delay: None)

    MacOSPlatformController().activate_app("AIVoice2")

    assert calls == [
        ["osascript", "-e", 'tell application "AIVoice2" to activate'],
        ["open", "-b", "jp.ai-j.AIVoice2"],
    ]


def test_macos_activation_raises_when_all_methods_fail(monkeypatch) -> None:
    def fake_run(cmd: list[str], **kwargs: object) -> object:
        import subprocess

        raise subprocess.CalledProcessError(1, cmd, stderr="nope")

    monkeypatch.setattr("subprocess.run", fake_run)

    with pytest.raises(AppActivationError, match="Failed to activate"):
        MacOSPlatformController().activate_app("Missing App")


def test_windows_placeholder_hotkey_and_activation_error() -> None:
    controller = WindowsPlatformController()

    assert controller.paste_hotkey() == ("ctrl", "v")
    assert "experimental" in controller.permission_guidance()
    with pytest.raises(UnsupportedPlatformError, match="not implemented"):
        controller.activate_app("A.I.VOICE2 Editor")

    with pytest.raises(UnsupportedPlatformError, match="window positioning"):
        controller.set_window_bounds("A.I.VOICE2 Editor", position=(0, 0))

    with pytest.raises(UnsupportedPlatformError, match="window origin"):
        controller.get_window_origin("A.I.VOICE2 Editor")
