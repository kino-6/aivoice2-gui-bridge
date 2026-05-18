# aivoice2-gui-bridge

A local GUI automation bridge for controlling A.I.VOICE2 Editor as a TTS
backend on macOS.

This is not an official A.I.VOICE2 API. It does not reverse engineer
A.I.VOICE2 internals and does not assume an official automation API exists.
It uses local GUI automation only: activate the app, paste text, and click
buttons found by screenshot image matching.

The intended workflow is personal/local:

1. Start A.I.VOICE2 Editor manually.
2. Select the desired voice preset manually, for example Kotonoha Akane.
3. Run this bridge from a terminal.

macOS is the supported target today. Windows support is planned/experimental:
the Windows backend currently exposes defaults such as `ctrl+v`, but app
activation is not implemented yet.

## Requirements

- Python 3.11+
- `uv`
- macOS
- A.I.VOICE2 Editor installed
- A.I.VOICE2 Editor running or activatable
- Desired voice preset already selected in A.I.VOICE2 Editor

The macOS terminal, IDE, or Python runner that launches this tool needs:

- Accessibility permission, so PyAutoGUI can control the UI
- Screen Recording permission, so image matching can inspect the screen

After granting permissions in System Settings, restart the terminal or IDE.

## Setup

```sh
uv sync
```

Capture the required image assets from your own A.I.VOICE2 Editor UI and place
them in `src/aivoice2_gui_bridge/assets`:

- `plus.png`
- `trash.png`
- `play_all.png`

Keep crops tight and stable. Use the same display scaling, theme, and layout
you will use when running the bridge.

## Usage

Check the local environment:

```sh
uv run aivoice2-gui-bridge doctor
```

Speak text:

```sh
uv run aivoice2-gui-bridge speak "こんにちは"
```

With a custom app name or assets directory:

```sh
uv run aivoice2-gui-bridge speak "こんにちは、茜ちゃんやで" \
  --app-name "A.I.VOICE2 Editor" \
  --assets-dir ./my-assets
```

With a limited image-search region and debug screenshot capture:

```sh
uv run aivoice2-gui-bridge speak "こんにちは" \
  --region 0,120,1200,800 \
  --debug-screenshot \
  --verbose
```

Useful debug options:

- `--platform auto|macos|windows`
- `--dry-run`
- `--assets-dir`
- `--confidence`
- `--timeout`
- `--region left,top,width,height`
- `--debug-screenshot`
- `--activation-delay`
- `--no-restore-clipboard`
- `--app-name`
- `--config`
- `--verbose`

## CLI

```sh
aivoice2-gui-bridge speak "text"
aivoice2-gui-bridge doctor
```

The default `speak` sequence is:

1. Activate `A.I.VOICE2 Editor` with AppleScript.
2. Click `plus.png`.
3. Click `trash.png`.
4. Preserve the current clipboard when possible.
5. Copy the target text.
6. Paste with the selected platform hotkey, `command+v` on macOS.
7. Restore the old clipboard unless `--no-restore-clipboard` is set.
8. Click `play_all.png`.

`--platform auto` is the default. It selects macOS on Darwin and Windows on
Windows:

```sh
uv run aivoice2-gui-bridge doctor --platform auto
uv run aivoice2-gui-bridge speak "こんにちは" --platform macos
```

## Architecture

The common bridge layer is `AIVoice2GuiBridge`. It owns the high-level workflow:
activate the app, run preparation actions, preserve and paste clipboard text,
then run play actions.

The platform controller layer handles OS-specific choices through
`PlatformController`: app activation, default app name, paste hotkey, and
permission guidance. `MacOSPlatformController` uses AppleScript activation and
returns `("command", "v")`; `WindowsPlatformController` is a small placeholder
that returns `("ctrl", "v")` and raises a clear unsupported error for activation.

The action execution layer runs configured actions. Image actions go through
the PyAutoGUI/OpenCV image locator, while coordinate fallback actions click
absolute screen coordinates.

## Config File

By default, the CLI reads `aivoice2-gui-bridge.yml` from the current directory
when it exists. You can also pass a path explicitly:

```sh
uv run aivoice2-gui-bridge speak "こんにちは" --config ./my-bridge.yml
```

Example image-based config:

```yaml
app_name: "A.I.VOICE2 Editor"
confidence: 0.85
timeout: 5.0
activation_delay: 0.5
region: "0,120,1200,800"
actions:
  prepare:
    - image: plus.png
    - image: trash.png
  play:
    - image: play_all.png
```

CLI arguments override config values. For example, `--confidence 0.75` wins over
`confidence: 0.85` in the file.

## How To Tune Image Matching

Start with the default `--confidence 0.85`. If matching fails but the button is
visible, try `--debug-screenshot` and inspect the saved screenshot to confirm
the UI looks like your asset crop.

Useful tuning steps:

- Recapture assets after changing A.I.VOICE2 theme, layout, language, display scaling, or monitor.
- Use tight crops with enough unique button detail.
- Try a slightly lower value such as `--confidence 0.75`.
- Use `--region left,top,width,height` to search only the A.I.VOICE2 toolbar or editor area.
- Keep OpenCV installed through `uv sync`; PyAutoGUI confidence matching requires `opencv-python`.

The region values are screen coordinates in pixels. `--region 0,120,1200,800`
means left `0`, top `120`, width `1200`, height `800`.

## Debug Screenshots

Pass `--debug-screenshot` to save the current screenshot when image matching
times out:

```sh
uv run aivoice2-gui-bridge speak "こんにちは" --debug-screenshot
```

Screenshots are written under `.debug/screenshots/`, and `.debug/` is ignored by
git. Failure messages print the saved path, image path, confidence, timeout,
region, and whether screenshot capture succeeded.

If screenshot capture fails, macOS Screen Recording permission is the usual
place to check. Grant it to the terminal, IDE, or Python runner that launches
the command, then restart that app.

## Using Fixed Coordinates As A Fallback

If image matching is unstable on your setup, define fixed coordinates in
`aivoice2-gui-bridge.yml`:

```yaml
actions:
  prepare:
    - click: [100, 200]
    - click: [140, 200]
  play:
    - click: [500, 800]
```

Coordinates are absolute screen pixels, so they are sensitive to window
position, display arrangement, and scaling. Keep the A.I.VOICE2 window in a
consistent location when using this fallback.

## Python API

```python
from aivoice2_gui_bridge import AIVoice2GuiBridge

bridge = AIVoice2GuiBridge()
bridge.speak("こんにちは")
```

## Limitations

- A.I.VOICE2 must be installed.
- A.I.VOICE2 must be running or activatable.
- The desired voice preset must be selected manually.
- UI layout, theme, language, display scaling, or app updates can break image matching.
- This is for local/personal automation, not a supported production API.
- Initial platform support is macOS; Windows support is planned/experimental.

## Troubleshooting

If app activation fails, confirm the exact macOS application name and pass it
with `--app-name`.

If image matching fails, run `doctor`, confirm the assets exist, recapture the
button images, or try a slightly lower confidence such as `--confidence 0.75`.
Use `--debug-screenshot` to see what the matcher actually saw.

If screenshots fail or all images are never found, grant Screen Recording
permission to the terminal, IDE, or Python runner and restart it.

If clicks or paste do not happen, grant Accessibility permission to the same
launcher app and restart it.

If clipboard restore fails, the text may still have been pasted. Use
`--no-restore-clipboard` when you prefer simpler clipboard behavior.
