from __future__ import annotations

import argparse
import importlib.util
import logging
import platform as platform_module
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from .bridge import AIVoice2BridgeError, AIVoice2GuiBridge
from .clipboard import ClipboardError
from .config import (
    DEFAULT_PLAY_ACTIONS,
    DEFAULT_PREPARE_ACTIONS,
    ConfigError,
    GuiAction,
    load_config,
    parse_region,
)
from .image_locator import (
    DEFAULT_ASSETS_DIR,
    ImageMatchingDependencyError,
    ImageNotFoundError,
    ScreenshotPermissionError,
)
from .platforms.macos import AppActivationError
from .platforms.base import UnsupportedPlatformError
from .platforms.selector import create_platform_controller, platform_name_for_system

LOGGER = logging.getLogger("aivoice2_gui_bridge")
REQUIRED_ASSETS = ("plus.png", "trash.png", "play_all.png")
DEFAULT_CONFIDENCE = 0.85
DEFAULT_TIMEOUT = 5.0
DEFAULT_ACTIVATION_DELAY = 0.5
DEFAULT_POST_PASTE_DELAY = 0.8
DEFAULT_SELECT_ALL_BEFORE_PASTE = False
PLATFORM_CHOICES = ("auto", "macos", "windows")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aivoice2-gui-bridge",
        description="Control A.I.VOICE2 Editor through local GUI automation.",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    speak = subparsers.add_parser("speak", help="Paste text into A.I.VOICE2 and click play.")
    speak.add_argument("text", help="Text to speak.")
    speak.add_argument("--platform", choices=PLATFORM_CHOICES, default="auto", help="Automation platform backend.")
    speak.add_argument("--config", type=Path, default=None, help="Path to a YAML config file.")
    speak.add_argument("--dry-run", action="store_true", help="Log actions without moving the mouse or clipboard.")
    speak.add_argument("--assets-dir", type=Path, default=None, help="Directory containing image assets.")
    speak.add_argument("--confidence", type=float, default=None, help="Image matching confidence.")
    speak.add_argument("--timeout", type=float, default=None, help="Image matching timeout in seconds.")
    speak.add_argument("--region", type=_parse_region_arg, default=None, help="Limit image search to left,top,width,height.")
    speak.add_argument(
        "--debug-screenshot",
        action="store_true",
        help="Save a screenshot under .debug/screenshots/ when image matching fails.",
    )
    speak.add_argument(
        "--activation-delay",
        type=float,
        default=None,
        help="Seconds to wait after activating A.I.VOICE2.",
    )
    speak.add_argument(
        "--no-restore-clipboard",
        action="store_true",
        help="Leave spoken text on the clipboard instead of restoring the previous value.",
    )
    speak.add_argument("--app-name", default=None, help="macOS application name to activate.")
    speak.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Enable verbose logging.",
    )

    doctor = subparsers.add_parser("doctor", help="Check local environment and permissions guidance.")
    doctor.add_argument("--platform", choices=PLATFORM_CHOICES, default="auto", help="Automation platform backend.")
    doctor.add_argument("--config", type=Path, default=None, help="Path to a YAML config file.")
    doctor.add_argument("--assets-dir", type=Path, default=None, help="Directory containing image assets.")
    doctor.add_argument("--app-name", default=None, help="Application name to mention in guidance.")
    doctor.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=argparse.SUPPRESS,
        help="Enable verbose logging.",
    )

    return parser


def configure_logging(verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)

    if args.command == "doctor":
        return run_doctor(args)
    if args.command == "speak":
        return run_speak(args)

    parser.error("Unknown command.")
    return 2


def run_speak(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    confidence = args.confidence if args.confidence is not None else config.confidence
    timeout = args.timeout if args.timeout is not None else config.timeout
    activation_delay = args.activation_delay if args.activation_delay is not None else config.activation_delay
    post_paste_delay = config.post_paste_delay
    select_all_before_paste = config.select_all_before_paste
    region = args.region if args.region is not None else config.region
    prepare_actions = tuple(config.prepare_actions) if config.prepare_actions else DEFAULT_PREPARE_ACTIONS
    play_actions = tuple(config.play_actions) if config.play_actions else DEFAULT_PLAY_ACTIONS
    actual_activation_delay = activation_delay if activation_delay is not None else DEFAULT_ACTIVATION_DELAY

    try:
        platform_controller = create_platform_controller(args.platform, activation_delay=actual_activation_delay)
    except UnsupportedPlatformError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    bridge = AIVoice2GuiBridge(
        app_name=args.app_name or config.app_name or platform_controller.default_app_name(),
        assets_dir=args.assets_dir or config.assets_dir,
        confidence=confidence if confidence is not None else DEFAULT_CONFIDENCE,
        timeout=timeout if timeout is not None else DEFAULT_TIMEOUT,
        region=region,
        debug_screenshot=args.debug_screenshot,
        activation_delay=actual_activation_delay,
        post_paste_delay=post_paste_delay if post_paste_delay is not None else DEFAULT_POST_PASTE_DELAY,
        select_all_before_paste=(
            select_all_before_paste
            if select_all_before_paste is not None
            else DEFAULT_SELECT_ALL_BEFORE_PASTE
        ),
        window_position=config.window_position,
        window_size=config.window_size,
        restore_clipboard=not args.no_restore_clipboard,
        dry_run=args.dry_run,
        prepare_actions=prepare_actions,
        play_actions=play_actions,
        platform=platform_controller,
        logger=LOGGER,
    )

    try:
        bridge.speak(args.text)
    except (
        AppActivationError,
        ClipboardError,
        ImageMatchingDependencyError,
        ImageNotFoundError,
        ScreenshotPermissionError,
        UnsupportedPlatformError,
        AIVoice2BridgeError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def run_doctor(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    try:
        selected_platform = args.platform if args.platform != "auto" else platform_name_for_system()
        platform_controller = create_platform_controller(args.platform)
    except UnsupportedPlatformError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    assets_dir = args.assets_dir or config.assets_dir or DEFAULT_ASSETS_DIR
    app_name = args.app_name or config.app_name or platform_controller.default_app_name()
    ok = True

    if selected_platform == "macos":
        ok &= _report("OS is macOS", platform_module.system() == "Darwin", platform_module.system())
    elif selected_platform == "windows":
        ok &= _report("OS is Windows", platform_module.system() == "Windows", platform_module.system())

    for module_name in ("pyautogui", "pyperclip", "cv2"):
        module_ok = importlib.util.find_spec(module_name) is not None
        ok &= _report(f"{module_name} importable", module_ok)
        if module_name == "cv2" and not module_ok:
            print("  PyAutoGUI confidence matching requires OpenCV. Run: uv sync")

    required_image_assets = _required_image_assets(
        tuple(config.prepare_actions) if config.prepare_actions else DEFAULT_PREPARE_ACTIONS,
        tuple(config.play_actions) if config.play_actions else DEFAULT_PLAY_ACTIONS,
    )

    missing_assets: list[Path] = []
    for asset_name in required_image_assets:
        path = assets_dir / asset_name
        asset_exists = path.exists()
        ok &= _report(f"asset exists: {asset_name}", asset_exists, str(path))
        if not asset_exists:
            missing_assets.append(path)

    if missing_assets:
        _print_asset_guidance(assets_dir)
    elif not required_image_assets:
        print("[ok] image assets not required by configured coordinate actions")

    screenshot_ok = _check_screenshot()
    ok &= screenshot_ok

    if selected_platform == "macos":
        ok &= _check_macos_accessibility()

    print()
    print(f"{selected_platform} permissions guidance:")
    for line in platform_controller.permission_guidance().splitlines():
        print(f"- {line}")
    print(f"- A.I.VOICE2 should be running or activatable as: {app_name}")

    return 0 if ok else 1


def _report(label: str, passed: bool, detail: str | None = None) -> bool:
    status = "ok" if passed else "missing"
    suffix = f" ({detail})" if detail else ""
    print(f"[{status}] {label}{suffix}")
    return passed


def _check_screenshot() -> bool:
    try:
        import pyautogui

        pyautogui.screenshot()
    except Exception as exc:
        print(
            "[missing] screenshot can be taken "
            f"({exc}; Screen Recording permission may be missing on macOS)"
        )
        return False
    print("[ok] screenshot can be taken")
    return True


def _check_macos_accessibility() -> bool:
    try:
        result = subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to get UI elements enabled'],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception as exc:
        print(
            "[missing] accessibility automation check "
            f"({exc}; grant Accessibility permission to the terminal/IDE/Python runner)"
        )
        return False

    enabled = result.stdout.strip().lower() == "true"
    if enabled:
        print("[ok] accessibility automation enabled")
        return True
    print("[missing] accessibility automation enabled (System Events returned false)")
    return False


def _print_asset_guidance(assets_dir: Path) -> None:
    print()
    print("image asset guidance:")
    print("- This tool does not ship A.I.VOICE2 button screenshots.")
    print("- Capture small screenshots from your own A.I.VOICE2 Editor window and save them as:")
    print(f"  - {assets_dir / 'plus.png'}")
    print(f"  - {assets_dir / 'trash.png'}")
    print(f"  - {assets_dir / 'play_all.png'}")
    print("- These files are used by PyAutoGUI/OpenCV to find and click the matching buttons.")
    print("- For local/personal use, fixed click coordinates are often easier to manage in git.")
    print("- Copy aivoice2-gui-bridge.example.yml to aivoice2-gui-bridge.yml and adjust coordinates.")


def _required_image_assets(prepare_actions: Sequence[GuiAction], play_actions: Sequence[GuiAction]) -> tuple[str, ...]:
    image_names: list[str] = []
    for action in (*prepare_actions, *play_actions):
        if action.image is not None:
            image_names.append(action.image)
    return tuple(dict.fromkeys(image_names))


def _parse_region_arg(value: str) -> tuple[int, int, int, int]:
    try:
        return parse_region(value)
    except ConfigError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


if __name__ == "__main__":
    raise SystemExit(main())
