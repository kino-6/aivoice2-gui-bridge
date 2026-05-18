from __future__ import annotations

from pathlib import Path

import pytest

from aivoice2_gui_bridge.image_locator import ImageNotFoundError
from aivoice2_gui_bridge.image_locator import ImageLocator


class FakeScreenshot:
    def save(self, path: Path) -> None:
        path.write_bytes(b"fake png")


class FakePyAutoGUI:
    def __init__(self) -> None:
        self.locate_calls: list[dict[str, object]] = []

    def screenshot(self) -> FakeScreenshot:
        return FakeScreenshot()

    def locateCenterOnScreen(self, image_path: str, **kwargs: object) -> None:
        self.locate_calls.append({"image_path": image_path, **kwargs})
        return None

    def click(self, location: object) -> None:  # pragma: no cover - should not be called
        raise AssertionError(f"unexpected click: {location}")


def test_resolve_image_path_uses_assets_dir_for_relative_names(tmp_path: Path) -> None:
    locator = ImageLocator(assets_dir=tmp_path)

    assert locator.resolve_image_path("play_all.png") == tmp_path / "play_all.png"


def test_resolve_image_path_leaves_absolute_paths_unchanged(tmp_path: Path) -> None:
    locator = ImageLocator(assets_dir=tmp_path / "assets")
    image = tmp_path / "custom.png"

    assert locator.resolve_image_path(str(image)) == image


def test_failed_image_matching_includes_diagnostics_and_debug_screenshot(tmp_path: Path) -> None:
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    image = assets_dir / "play_all.png"
    image.write_bytes(b"not a real png, but enough for path resolution")
    fake_pyautogui = FakePyAutoGUI()
    locator = ImageLocator(
        assets_dir=assets_dir,
        confidence=0.7,
        timeout=0.01,
        region=(10, 20, 300, 400),
        debug_screenshot=True,
        debug_screenshot_dir=tmp_path / ".debug" / "screenshots",
        pyautogui_module=fake_pyautogui,
    )

    with pytest.raises(ImageNotFoundError) as exc_info:
        locator.click_image("play_all.png")

    message = str(exc_info.value)
    assert f"image path: {image}" in message
    assert "confidence: 0.7" in message
    assert "timeout: 0.01" in message
    assert "region: (10, 20, 300, 400)" in message
    assert "screenshot succeeded: True" in message
    assert "debug screenshot saved:" in message
    assert "Screen Recording permission" in message
    assert fake_pyautogui.locate_calls[0]["region"] == (10, 20, 300, 400)
    assert list((tmp_path / ".debug" / "screenshots").glob("*.png"))
