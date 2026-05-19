from __future__ import annotations

from aivoice2_gui_bridge.bridge import AIVoice2GuiBridge
from aivoice2_gui_bridge.config import GuiAction


class FakePlatform:
    def activate_app(self, app_name: str) -> None:
        pass

    def paste_hotkey(self) -> tuple[str, ...]:
        return ("command", "v")

    def default_app_name(self) -> str:
        return "AIVoice2"

    def permission_guidance(self) -> str:
        return ""

    def set_window_bounds(
        self,
        app_name: str,
        *,
        position: tuple[int, int] | None = None,
        size: tuple[int, int] | None = None,
    ) -> None:
        pass

    def get_window_origin(self, app_name: str) -> tuple[int, int]:
        return (100, 200)


def test_window_offset_action_clicks_relative_to_window_origin(monkeypatch) -> None:
    clicked: list[tuple[int, int]] = []
    monkeypatch.setattr(
        AIVoice2GuiBridge,
        "_click_coordinates",
        staticmethod(lambda x, y: clicked.append((x, y))),
    )
    bridge = AIVoice2GuiBridge(
        platform=FakePlatform(),
        image_locator=object(),  # type: ignore[arg-type]
        prepare_actions=(),
        play_actions=(),
    )

    bridge._run_actions((GuiAction(click_offset=(10, 20)),), "test")

    assert clicked == [(110, 220)]
