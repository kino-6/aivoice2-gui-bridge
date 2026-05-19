from __future__ import annotations

import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from .clipboard import Clipboard, ClipboardError
from .config import DEFAULT_PLAY_ACTIONS, DEFAULT_PREPARE_ACTIONS, GuiAction, Region
from .image_locator import ImageLocator
from .platforms.base import PlatformController
from .platforms.selector import create_platform_controller

LOGGER = logging.getLogger(__name__)


class AIVoice2BridgeError(RuntimeError):
    """Base exception for bridge failures."""


class UnsupportedPlatformError(AIVoice2BridgeError):
    """Raised when no platform automation backend is available."""


@dataclass(slots=True)
class AIVoice2GuiBridge:
    """Control A.I.VOICE2 Editor through local GUI automation."""

    app_name: str = "A.I.VOICE2 Editor"
    assets_dir: Path | None = None
    confidence: float = 0.85
    timeout: float = 5.0
    region: Region | None = None
    debug_screenshot: bool = False
    activation_delay: float = 0.5
    post_paste_delay: float = 0.8
    select_all_before_paste: bool = False
    window_position: tuple[int, int] | None = None
    window_size: tuple[int, int] | None = None
    restore_clipboard: bool = True
    dry_run: bool = False
    platform_name: str = "auto"
    paste_hotkey_keys: Sequence[str] | None = None
    prepare_steps: Sequence[str] = field(default_factory=lambda: ("plus.png", "trash.png"))
    prepare_actions: Sequence[GuiAction] | None = None
    play_button_image: str = "play_all.png"
    play_actions: Sequence[GuiAction] | None = None
    platform: PlatformController | None = None
    clipboard: Clipboard | None = None
    image_locator: ImageLocator | None = None
    logger: logging.Logger = LOGGER

    def __post_init__(self) -> None:
        if self.platform is None:
            self.platform = create_platform_controller(
                self.platform_name,
                activation_delay=self.activation_delay,
                paste_hotkey_keys=tuple(self.paste_hotkey_keys) if self.paste_hotkey_keys is not None else None,
            )
        if self.clipboard is None:
            self.clipboard = Clipboard(logger=self.logger)
        if self.image_locator is None:
            self.image_locator = ImageLocator(
                assets_dir=self.assets_dir,
                confidence=self.confidence,
                timeout=self.timeout,
                region=self.region,
                debug_screenshot=self.debug_screenshot,
                dry_run=self.dry_run,
                logger=self.logger,
            )

    def speak(self, text: str) -> None:
        """Paste text into A.I.VOICE2 Editor and start playback."""
        if not text:
            raise ValueError("Text must not be empty.")

        assert self.platform is not None
        assert self.clipboard is not None
        assert self.image_locator is not None

        self.logger.info("Activating A.I.VOICE2 app: %s", self.app_name)
        if self.dry_run:
            self.logger.info("Dry run: would activate app")
            if self.window_position is not None or self.window_size is not None:
                self.logger.info(
                    "Dry run: would prepare window position=%s size=%s",
                    self.window_position,
                    self.window_size,
                )
        else:
            self.platform.activate_app(self.app_name)
            self._prepare_window()

        self._run_actions(self._prepare_actions(), "preparation")

        self.logger.info("Pasting text into A.I.VOICE2")
        try:
            with self.clipboard.preserved_text(text, restore=self.restore_clipboard, dry_run=self.dry_run):
                if self.dry_run:
                    if self.select_all_before_paste:
                        self.logger.info("Dry run: would press select-all hotkey before paste")
                    self.logger.info("Dry run: would press paste hotkey %s", self.platform.paste_hotkey())
                else:
                    if self.select_all_before_paste:
                        paste_hotkey = self.platform.paste_hotkey()
                        self._press_hotkey((paste_hotkey[0], "a"))
                    self._press_paste_hotkey()
        except ClipboardError:
            raise
        except Exception as exc:  # pragma: no cover - defensive wrapper
            raise AIVoice2BridgeError("Failed while pasting text into A.I.VOICE2.") from exc

        if self.post_paste_delay > 0:
            if self.dry_run:
                self.logger.info("Dry run: would wait %.2fs after paste", self.post_paste_delay)
            else:
                time.sleep(self.post_paste_delay)

        self._run_actions(self._play_actions(), "play")

    def _prepare_actions(self) -> Sequence[GuiAction]:
        if self.prepare_actions is not None:
            return self.prepare_actions
        if self.prepare_steps:
            return tuple(GuiAction(image=image_name) for image_name in self.prepare_steps)
        return DEFAULT_PREPARE_ACTIONS

    def _play_actions(self) -> Sequence[GuiAction]:
        if self.play_actions is not None:
            return self.play_actions
        if self.play_button_image:
            return (GuiAction(image=self.play_button_image),)
        return DEFAULT_PLAY_ACTIONS

    def _run_actions(self, actions: Sequence[GuiAction], label: str) -> None:
        assert self.platform is not None
        assert self.image_locator is not None

        for action in actions:
            if action.image is not None:
                self.logger.info("Clicking %s image: %s", label, action.image)
                self.image_locator.click_image(
                    action.image,
                    confidence=self.confidence,
                    timeout=self.timeout,
                    region=self.region,
                )
                continue

            if action.click_offset is not None:
                offset_x, offset_y = action.click_offset
                if self.dry_run:
                    self.logger.info("Dry run: would click %s window offset %s,%s", label, offset_x, offset_y)
                    continue
                origin_x, origin_y = self.platform.get_window_origin(self.app_name)
                x, y = origin_x + offset_x, origin_y + offset_y
                self.logger.info(
                    "Clicking %s window offset: %s,%s -> %s,%s",
                    label,
                    offset_x,
                    offset_y,
                    x,
                    y,
                )
            else:
                assert action.click is not None
                x, y = action.click
                self.logger.info("Clicking %s coordinates: %s,%s", label, x, y)
            if self.dry_run:
                self.logger.info("Dry run: would click coordinates %s,%s", x, y)
            else:
                self._click_coordinates(x, y)

    def _prepare_window(self) -> None:
        assert self.platform is not None
        if self.window_position is None and self.window_size is None:
            return
        self.logger.info(
            "Preparing A.I.VOICE2 window: position=%s size=%s",
            self.window_position,
            self.window_size,
        )
        self.platform.set_window_bounds(
            self.app_name,
            position=self.window_position,
            size=self.window_size,
        )

    def _press_paste_hotkey(self) -> None:
        assert self.platform is not None
        self._press_hotkey(self.platform.paste_hotkey())

    @staticmethod
    def _press_hotkey(keys: Sequence[str]) -> None:
        import pyautogui

        pyautogui.hotkey(*keys)

    @staticmethod
    def _click_coordinates(x: int, y: int) -> None:
        import pyautogui

        pyautogui.click(x, y)
