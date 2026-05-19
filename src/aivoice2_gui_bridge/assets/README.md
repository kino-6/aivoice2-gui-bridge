# Image Assets

This directory intentionally does not include A.I.VOICE2 UI screenshots.

The default CLI workflow uses PyAutoGUI/OpenCV image matching. That means it
looks for small button screenshots on the current screen and clicks the center
of the match.

Capture small, stable crops from your own A.I.VOICE2 Editor UI and save them here:

- `plus.png`: the button used to add or prepare a text row
- `trash.png`: the button used to clear the current text row
- `play_all.png`: the play-all button

Without these files, `aivoice2-gui-bridge speak ...` cannot use the default
image-based actions. For local/personal use, window-relative `click_offset`
coordinates through `aivoice2-gui-bridge.yml` are often easier and avoid
managing PNG files in git.

Tips:

- Keep each crop tight around the button, but include enough surrounding pixels to make it unique.
- Capture the images using the same macOS display scaling, A.I.VOICE2 theme, and UI layout you will use while running the tool.
- If matching fails, recapture the image or lower `--confidence` slightly.
