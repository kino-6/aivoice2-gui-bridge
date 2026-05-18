from __future__ import annotations

from pathlib import Path

from aivoice2_gui_bridge import cli
from aivoice2_gui_bridge.cli import build_parser


def test_parse_speak_arguments() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "--verbose",
            "speak",
            "こんにちは",
            "--dry-run",
            "--platform",
            "macos",
            "--assets-dir",
            "/tmp/assets",
            "--confidence",
            "0.7",
            "--timeout",
            "3",
            "--region",
            "10,20,300,400",
            "--activation-delay",
            "1.5",
            "--debug-screenshot",
            "--no-restore-clipboard",
            "--app-name",
            "Custom App",
        ]
    )

    assert args.verbose is True
    assert args.command == "speak"
    assert args.text == "こんにちは"
    assert args.dry_run is True
    assert args.platform == "macos"
    assert args.assets_dir == Path("/tmp/assets")
    assert args.confidence == 0.7
    assert args.timeout == 3.0
    assert args.region == (10, 20, 300, 400)
    assert args.activation_delay == 1.5
    assert args.debug_screenshot is True
    assert args.no_restore_clipboard is True
    assert args.app_name == "Custom App"


def test_parse_doctor_arguments() -> None:
    parser = build_parser()
    args = parser.parse_args(["doctor", "--assets-dir", "/tmp/assets"])

    assert args.command == "doctor"
    assert args.assets_dir == Path("/tmp/assets")


def test_parse_verbose_after_subcommand() -> None:
    parser = build_parser()
    args = parser.parse_args(["speak", "こんにちは", "--verbose"])

    assert args.verbose is True


def test_parse_region_rejects_invalid_value() -> None:
    parser = build_parser()

    try:
        parser.parse_args(["speak", "こんにちは", "--region", "1,2,3"])
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover
        raise AssertionError("Expected parser to reject invalid region")


def test_cli_args_override_config_values(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "aivoice2-gui-bridge.yml"
    config_path.write_text(
        """
app_name: "Config App"
confidence: 0.85
timeout: 5
activation_delay: 0.5
region: "1,2,300,400"
actions:
  prepare:
    - click: [10, 20]
  play:
    - click: [30, 40]
""",
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    class FakeBridge:
        def __init__(self, **kwargs: object) -> None:
            captured.update(kwargs)

        def speak(self, text: str) -> None:
            captured["text"] = text

    monkeypatch.setattr(cli, "AIVoice2GuiBridge", FakeBridge)
    parser = build_parser()
    args = parser.parse_args(
        [
            "speak",
            "こんにちは",
            "--config",
            str(config_path),
            "--app-name",
            "CLI App",
            "--confidence",
            "0.7",
            "--timeout",
            "2",
            "--activation-delay",
            "1",
            "--region",
            "5,6,700,800",
        ]
    )

    assert cli.run_speak(args) == 0
    assert captured["app_name"] == "CLI App"
    assert captured["confidence"] == 0.7
    assert captured["timeout"] == 2.0
    assert captured["activation_delay"] == 1.0
    assert captured["region"] == (5, 6, 700, 800)
    assert captured["text"] == "こんにちは"
