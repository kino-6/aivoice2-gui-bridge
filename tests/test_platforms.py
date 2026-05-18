from __future__ import annotations

import pytest

from aivoice2_gui_bridge.platforms.base import UnsupportedPlatformError
from aivoice2_gui_bridge.platforms.macos import MacOSPlatformController
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
    assert controller.default_app_name() == "A.I.VOICE2 Editor"
    assert "Accessibility" in controller.permission_guidance()
    assert "Screen Recording" in controller.permission_guidance()


def test_windows_placeholder_hotkey_and_activation_error() -> None:
    controller = WindowsPlatformController()

    assert controller.paste_hotkey() == ("ctrl", "v")
    assert "experimental" in controller.permission_guidance()
    with pytest.raises(UnsupportedPlatformError, match="not implemented"):
        controller.activate_app("A.I.VOICE2 Editor")
