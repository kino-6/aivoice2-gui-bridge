from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeAlias

Region: TypeAlias = tuple[int, int, int, int]
ClickPoint: TypeAlias = tuple[int, int]


class ConfigError(ValueError):
    """Raised when a configuration file is invalid."""


@dataclass(frozen=True, slots=True)
class GuiAction:
    """One GUI action, either image-based or fixed-coordinate."""

    image: str | None = None
    click: ClickPoint | None = None
    click_offset: ClickPoint | None = None

    def __post_init__(self) -> None:
        defined = sum(value is not None for value in (self.image, self.click, self.click_offset))
        if defined != 1:
            raise ConfigError("Each action must define exactly one of 'image', 'click', or 'click_offset'.")


@dataclass(frozen=True, slots=True)
class BridgeConfig:
    app_name: str | None = None
    assets_dir: Path | None = None
    confidence: float | None = None
    timeout: float | None = None
    activation_delay: float | None = None
    post_paste_delay: float | None = None
    select_all_before_paste: bool | None = None
    region: Region | None = None
    window_position: ClickPoint | None = None
    window_size: ClickPoint | None = None
    prepare_actions: Sequence[GuiAction] = field(default_factory=tuple)
    play_actions: Sequence[GuiAction] = field(default_factory=tuple)


DEFAULT_CONFIG_PATH = Path("aivoice2-gui-bridge.yml")
DEFAULT_PREPARE_ACTIONS: tuple[GuiAction, ...] = (
    GuiAction(image="plus.png"),
    GuiAction(image="trash.png"),
)
DEFAULT_PLAY_ACTIONS: tuple[GuiAction, ...] = (GuiAction(image="play_all.png"),)


def load_config(path: Path | str | None) -> BridgeConfig:
    """Load a YAML config file, returning an empty config when no default exists."""
    if path is None:
        config_path = DEFAULT_CONFIG_PATH
        if not config_path.exists():
            return BridgeConfig()
    else:
        config_path = Path(path).expanduser()
        if not config_path.exists():
            raise ConfigError(f"Config file not found: {config_path}")

    try:
        import yaml
    except ImportError as exc:
        raise ConfigError("PyYAML is required to read aivoice2-gui-bridge.yml config files.") from exc

    try:
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ConfigError(f"Failed to read config file {config_path}: {exc}") from exc

    if raw is None:
        return BridgeConfig()
    if not isinstance(raw, Mapping):
        raise ConfigError("Config file root must be a mapping.")

    return parse_config(raw, base_dir=config_path.parent)


def parse_config(raw: Mapping[str, Any], *, base_dir: Path | None = None) -> BridgeConfig:
    base_dir = Path(".") if base_dir is None else base_dir
    actions = raw.get("actions", {})
    if actions is None:
        actions = {}
    if not isinstance(actions, Mapping):
        raise ConfigError("'actions' must be a mapping.")
    window = raw.get("window", {})
    if window is None:
        window = {}
    if not isinstance(window, Mapping):
        raise ConfigError("'window' must be a mapping.")

    assets_dir = _optional_path(raw.get("assets_dir"), base_dir=base_dir)
    return BridgeConfig(
        app_name=_optional_str(raw.get("app_name"), "app_name"),
        assets_dir=assets_dir,
        confidence=_optional_float(raw.get("confidence"), "confidence"),
        timeout=_optional_float(raw.get("timeout"), "timeout"),
        activation_delay=_optional_float(raw.get("activation_delay"), "activation_delay"),
        post_paste_delay=_optional_float(raw.get("post_paste_delay"), "post_paste_delay"),
        select_all_before_paste=_optional_bool(raw.get("select_all_before_paste"), "select_all_before_paste"),
        region=parse_region(raw["region"]) if "region" in raw and raw["region"] is not None else None,
        window_position=_parse_optional_point(window.get("position"), "window.position"),
        window_size=_parse_optional_size(window.get("size"), "window.size"),
        prepare_actions=tuple(_parse_actions(actions.get("prepare", ()), "actions.prepare")),
        play_actions=tuple(_parse_actions(actions.get("play", ()), "actions.play")),
    )


def parse_region(value: str | Sequence[int] | Sequence[str]) -> Region:
    if isinstance(value, str):
        parts: Sequence[str] = [part.strip() for part in value.split(",")]
    else:
        parts = value

    if len(parts) != 4:
        raise ConfigError("Region must have four values: left,top,width,height.")

    try:
        left, top, width, height = (int(part) for part in parts)
    except (TypeError, ValueError) as exc:
        raise ConfigError("Region must contain integer values: left,top,width,height.") from exc

    if left < 0 or top < 0:
        raise ConfigError("Region left and top must be non-negative.")
    if width <= 0 or height <= 0:
        raise ConfigError("Region width and height must be positive.")
    return (left, top, width, height)


def _parse_actions(value: Any, label: str) -> Sequence[GuiAction]:
    if value is None:
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ConfigError(f"'{label}' must be a list.")

    actions: list[GuiAction] = []
    for index, item in enumerate(value):
        item_label = f"{label}[{index}]"
        if not isinstance(item, Mapping):
            raise ConfigError(f"'{item_label}' must be a mapping.")
        has_image = "image" in item
        has_click = "click" in item
        has_click_offset = "click_offset" in item
        if sum((has_image, has_click, has_click_offset)) != 1:
            raise ConfigError(f"'{item_label}' must define exactly one of 'image', 'click', or 'click_offset'.")

        if has_image:
            actions.append(GuiAction(image=_required_str(item["image"], f"{item_label}.image")))
        elif has_click:
            actions.append(GuiAction(click=_parse_click(item["click"], f"{item_label}.click")))
        else:
            actions.append(GuiAction(click_offset=_parse_click(item["click_offset"], f"{item_label}.click_offset")))
    return actions


def _parse_click(value: Any, label: str) -> ClickPoint:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) != 2:
        raise ConfigError(f"'{label}' must be [x, y].")
    try:
        x, y = (int(part) for part in value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"'{label}' must contain integer coordinates.") from exc
    return (x, y)


def _parse_optional_point(value: Any, label: str) -> ClickPoint | None:
    if value is None:
        return None
    return _parse_click(value, label)


def _parse_optional_size(value: Any, label: str) -> ClickPoint | None:
    if value is None:
        return None
    width, height = _parse_click(value, label)
    if width <= 0 or height <= 0:
        raise ConfigError(f"'{label}' width and height must be positive.")
    return (width, height)


def _optional_path(value: Any, *, base_dir: Path) -> Path | None:
    if value is None:
        return None
    path = Path(_required_str(value, "assets_dir")).expanduser()
    if not path.is_absolute():
        path = base_dir / path
    return path


def _optional_float(value: Any, label: str) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigError(f"'{label}' must be a number.") from exc


def _optional_str(value: Any, label: str) -> str | None:
    if value is None:
        return None
    return _required_str(value, label)


def _optional_bool(value: Any, label: str) -> bool | None:
    if value is None:
        return None
    if not isinstance(value, bool):
        raise ConfigError(f"'{label}' must be true or false.")
    return value


def _required_str(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ConfigError(f"'{label}' must be a non-empty string.")
    return value
