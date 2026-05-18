from __future__ import annotations

import importlib.util
import logging
import time
from datetime import datetime
from pathlib import Path
from types import ModuleType
from typing import Any

from .config import Region

LOGGER = logging.getLogger(__name__)
DEFAULT_ASSETS_DIR = Path(__file__).resolve().parent / "assets"
DEFAULT_DEBUG_SCREENSHOT_DIR = Path(".debug") / "screenshots"


class ImageNotFoundError(RuntimeError):
    """Raised when an image cannot be found on screen before timeout."""


class ScreenshotPermissionError(RuntimeError):
    """Raised when macOS screenshot permissions appear to be missing."""


class ImageMatchingDependencyError(RuntimeError):
    """Raised when confidence-based image matching cannot run."""


class ImageLocator:
    """Locate and click images using PyAutoGUI."""

    def __init__(
        self,
        *,
        assets_dir: Path | str | None = None,
        confidence: float = 0.85,
        timeout: float = 5.0,
        region: Region | None = None,
        debug_screenshot: bool = False,
        debug_screenshot_dir: Path | str = DEFAULT_DEBUG_SCREENSHOT_DIR,
        dry_run: bool = False,
        pyautogui_module: ModuleType | Any | None = None,
        logger: logging.Logger = LOGGER,
    ) -> None:
        self.assets_dir = Path(assets_dir).expanduser() if assets_dir is not None else DEFAULT_ASSETS_DIR
        self.confidence = confidence
        self.timeout = timeout
        self.region = region
        self.debug_screenshot = debug_screenshot
        self.debug_screenshot_dir = Path(debug_screenshot_dir).expanduser()
        self.dry_run = dry_run
        self._pyautogui = pyautogui_module
        self._logger = logger

    @property
    def pyautogui(self) -> ModuleType | Any:
        if self._pyautogui is None:
            import pyautogui

            self._pyautogui = pyautogui
        return self._pyautogui

    def resolve_image_path(self, image_name: str) -> Path:
        path = Path(image_name).expanduser()
        if not path.is_absolute():
            path = self.assets_dir / path
        return path

    def click_image(
        self,
        image_name: str,
        *,
        confidence: float | None = None,
        timeout: float | None = None,
        region: Region | None = None,
    ) -> None:
        image_path = self.resolve_image_path(image_name)
        actual_confidence = self.confidence if confidence is None else confidence
        actual_timeout = self.timeout if timeout is None else timeout
        actual_region = self.region if region is None else region

        if self.dry_run:
            self._logger.info(
                "Dry run: would locate and click %s with confidence %.2f%s%s",
                image_path,
                actual_confidence,
                f" in region {actual_region}" if actual_region else "",
                "" if image_path.exists() else " (asset is not present yet)",
            )
            return

        if not self._opencv_available():
            raise ImageMatchingDependencyError(
                "OpenCV is missing. PyAutoGUI confidence matching requires OpenCV; install the "
                "'opencv-python' dependency with 'uv sync'."
            )

        if not image_path.exists():
            raise ImageNotFoundError(
                self._format_not_found_message(
                    image_path=image_path,
                    confidence=actual_confidence,
                    timeout=actual_timeout,
                    region=actual_region,
                    screenshot_succeeded=None,
                    debug_path=None,
                    detail="Image asset does not exist. Capture this UI element and save it with that name.",
                )
            )

        screenshot = self._take_screenshot()
        deadline = time.monotonic() + actual_timeout
        last_error: Exception | None = None

        while time.monotonic() <= deadline:
            try:
                location = self.pyautogui.locateCenterOnScreen(
                    str(image_path),
                    confidence=actual_confidence,
                    region=actual_region,
                )
            except Exception as exc:
                last_error = exc
                if self._looks_like_screenshot_failure(exc):
                    raise ScreenshotPermissionError(
                        "Screenshot failed. On macOS, grant Screen Recording permission to your terminal, "
                        "IDE, or Python runner, then restart it."
                    ) from exc
                raise

            if location is not None:
                self.pyautogui.click(location)
                return
            time.sleep(0.1)

        debug_path = self._save_debug_screenshot(screenshot, image_path=image_path)
        detail = f"Last locate error: {last_error}" if last_error else "No match found before timeout."
        raise ImageNotFoundError(
            self._format_not_found_message(
                image_path=image_path,
                confidence=actual_confidence,
                timeout=actual_timeout,
                region=actual_region,
                screenshot_succeeded=True,
                debug_path=debug_path,
                detail=detail,
            )
        )

    def _take_screenshot(self) -> Any:
        try:
            return self.pyautogui.screenshot()
        except Exception as exc:
            raise ScreenshotPermissionError(
                "Screenshot failed. On macOS, this often means Screen Recording permission is missing "
                "for the terminal, IDE, or Python runner."
            ) from exc

    def _save_debug_screenshot(self, screenshot: Any, *, image_path: Path) -> Path | None:
        if not self.debug_screenshot:
            return None

        try:
            self.debug_screenshot_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
            safe_stem = "".join(char if char.isalnum() or char in ("-", "_") else "_" for char in image_path.stem)
            path = self.debug_screenshot_dir / f"{timestamp}-{safe_stem}.png"
            screenshot.save(path)
        except Exception as exc:
            self._logger.warning("Could not save debug screenshot: %s", exc)
            return None
        return path

    @staticmethod
    def _format_not_found_message(
        *,
        image_path: Path,
        confidence: float,
        timeout: float,
        region: Region | None,
        screenshot_succeeded: bool | None,
        debug_path: Path | None,
        detail: str,
    ) -> str:
        screenshot_status = "not attempted" if screenshot_succeeded is None else str(screenshot_succeeded)
        lines = [
            "Image matching failed.",
            f"image path: {image_path}",
            f"confidence: {confidence}",
            f"timeout: {timeout}",
            f"region: {region if region else 'full screen'}",
            f"screenshot succeeded: {screenshot_status}",
        ]
        if debug_path is not None:
            lines.append(f"debug screenshot saved: {debug_path}")
        lines.extend(
            [
                detail,
                "Check macOS Screen Recording permission for the terminal, IDE, or Python runner.",
                "Also check the asset crop, UI theme/layout, and display scaling.",
            ]
        )
        return "\n".join(lines)

    @staticmethod
    def _opencv_available() -> bool:
        return importlib.util.find_spec("cv2") is not None

    @staticmethod
    def _looks_like_screenshot_failure(exc: Exception) -> bool:
        message = str(exc).lower()
        return "screenshot" in message or "screen recording" in message or "permission" in message
