# aivoice2-gui-bridge

A local GUI automation bridge for controlling A.I.VOICE2 Editor as a TTS
backend on macOS.

This is not an official A.I.VOICE2 API. It does not reverse engineer
A.I.VOICE2 internals and does not assume an official automation API exists.
It uses local GUI automation only: activate the app, paste text, and click
buttons either by fixed coordinates or screenshot image matching.

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

For personal/local use, window-relative coordinates are usually the easiest
setup. Copy the example config and adjust the offsets for your A.I.VOICE2
window:

```sh
cp aivoice2-gui-bridge.example.yml aivoice2-gui-bridge.yml
```

`aivoice2-gui-bridge.yml` is gitignored because coordinates are specific to
your display, window size, and scaling.

Image matching is still supported, but it requires local screenshots of
A.I.VOICE2 buttons. Those images are not included in this repository because UI
appearance can differ by version, theme, language, display scaling, and monitor.

Quick start checklist:

1. Run `uv sync`.
2. Grant Accessibility and Screen Recording permission to the terminal/IDE that runs `uv run`.
3. Start A.I.VOICE2 Editor and select the voice preset manually.
4. Copy `aivoice2-gui-bridge.example.yml` to `aivoice2-gui-bridge.yml`.
5. Adjust `window.position`, `window.size`, and `click_offset: [x, y]` values for your A.I.VOICE2 window.
6. Run `uv run aivoice2-gui-bridge doctor`.

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

That default sequence uses image matching. If `aivoice2-gui-bridge.yml` exists,
its `actions` replace the default sequence, so you can use fixed coordinates
without any image assets.

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
the PyAutoGUI/OpenCV image locator, absolute `click` actions click screen
coordinates directly, and `click_offset` actions click relative to the
A.I.VOICE2 window's top-left corner.

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

Example coordinate-based config:

```yaml
app_name: "AIVoice2"
activation_delay: 0.5
post_paste_delay: 0.8
select_all_before_paste: true
window:
  position: [0, 25]
  size: [1328, 760]
actions:
  prepare:
    - click_offset: [408, 173]
  play:
    - click_offset: [512, 524]
```

## How To Tune Image Matching

Image matching means the CLI searches the current screenshot for a saved button
crop, then clicks the center of the match. The default workflow uses these
assets:

- `plus.png`: the plus button near the top of the sentence list
- `trash.png`: the trash/delete button near the top of the sentence list
- `play_all.png`: the play button used to start playback

On a default-looking A.I.VOICE2 Editor window, crop only the button icon and a
small amount of surrounding background. Do not capture the whole toolbar or the
whole window.

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

For this local/personal bridge, coordinates are often preferable to image assets
because they are simple text and do not require managing screenshots in git.
The most stable coordinate mode is `click_offset`, which clicks relative to the
A.I.VOICE2 window after optionally moving/resizing it:

```yaml
window:
  position: [0, 25]
  size: [1328, 760]
actions:
  prepare:
    - click_offset: [408, 173]
  play:
    - click_offset: [512, 524]
```

`window.position` and `window.size` make the A.I.VOICE2 window deterministic.
`click_offset` values are measured from the window's top-left corner. Absolute
`click: [x, y]` is still supported, but it is more sensitive to window position,
display arrangement, and scaling.

`post_paste_delay` waits briefly after pasting text before clicking play. This
helps when A.I.VOICE2 needs a moment to update its accent/preview state.
`select_all_before_paste` replaces the current text instead of appending to it
after the input field has focus.

The tradeoff is straightforward: coordinates are easy to version as an example
and easy to keep local, but they depend on your window size/layout. Image
matching is more flexible when the window moves, but the PNG assets are local
binary files and can be awkward to review or share.

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

If the CLI prints normal-looking logs such as `Clicking preparation coordinates`
and `Pasting text into A.I.VOICE2` but nothing changes on screen, the usual
cause is Accessibility permission. Grant it to the exact app running
`uv run`, such as Terminal, Ghostty, VS Code, or Codex, then restart that app.

If clipboard restore fails, the text may still have been pasted. Use
`--no-restore-clipboard` when you prefer simpler clipboard behavior.
