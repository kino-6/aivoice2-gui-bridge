from __future__ import annotations

from pathlib import Path

import pytest

from aivoice2_gui_bridge.config import ConfigError, load_config, parse_config, parse_region


def test_load_config_parses_image_actions(tmp_path: Path) -> None:
    config_path = tmp_path / "aivoice2-gui-bridge.yml"
    config_path.write_text(
        """
app_name: "A.I.VOICE2 Editor"
confidence: 0.8
timeout: 4
activation_delay: 1.2
region: "10,20,300,400"
actions:
  prepare:
    - image: plus.png
    - image: trash.png
  play:
    - image: play_all.png
""",
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.app_name == "A.I.VOICE2 Editor"
    assert config.confidence == 0.8
    assert config.timeout == 4.0
    assert config.activation_delay == 1.2
    assert config.region == (10, 20, 300, 400)
    assert [action.image for action in config.prepare_actions] == ["plus.png", "trash.png"]
    assert config.play_actions[0].image == "play_all.png"


def test_parse_config_parses_coordinate_actions() -> None:
    config = parse_config(
        {
            "actions": {
                "prepare": [{"click": [100, 200]}, {"click": [140, 200]}],
                "play": [{"click": [500, 800]}],
            }
        }
    )

    assert [action.click for action in config.prepare_actions] == [(100, 200), (140, 200)]
    assert config.play_actions[0].click == (500, 800)


def test_parse_region_accepts_comma_string() -> None:
    assert parse_region("1,2,300,400") == (1, 2, 300, 400)


def test_parse_region_rejects_bad_format() -> None:
    with pytest.raises(ConfigError, match="four values"):
        parse_region("1,2,3")

    with pytest.raises(ConfigError, match="positive"):
        parse_region("1,2,0,400")


def test_parse_config_rejects_action_with_image_and_click() -> None:
    with pytest.raises(ConfigError, match="exactly one"):
        parse_config({"actions": {"prepare": [{"image": "plus.png", "click": [1, 2]}]}})
