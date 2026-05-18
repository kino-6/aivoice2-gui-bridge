from __future__ import annotations

import pytest

from aivoice2_gui_bridge.clipboard import Clipboard, ClipboardError


class FakePyperclip:
    def __init__(self, initial: str = "") -> None:
        self.value = initial
        self.copied: list[str] = []
        self.fail_paste = False
        self.fail_copy = False

    def paste(self) -> str:
        if self.fail_paste:
            raise RuntimeError("paste failed")
        return self.value

    def copy(self, text: str) -> None:
        if self.fail_copy:
            raise RuntimeError("copy failed")
        self.value = text
        self.copied.append(text)


def test_preserved_text_restores_previous_clipboard() -> None:
    fake = FakePyperclip("before")
    clipboard = Clipboard(fake)

    with clipboard.preserved_text("target"):
        assert fake.value == "target"

    assert fake.value == "before"
    assert fake.copied == ["target", "before"]


def test_preserved_text_can_skip_restore() -> None:
    fake = FakePyperclip("before")
    clipboard = Clipboard(fake)

    with clipboard.preserved_text("target", restore=False):
        assert fake.value == "target"

    assert fake.value == "target"
    assert fake.copied == ["target"]


def test_preserved_text_raises_when_copy_fails() -> None:
    fake = FakePyperclip("before")
    fake.fail_copy = True
    clipboard = Clipboard(fake)

    with pytest.raises(ClipboardError):
        with clipboard.preserved_text("target"):
            pass


def test_preserved_text_logs_restore_failure_without_raising(caplog) -> None:
    class RestoreFailsPyperclip(FakePyperclip):
        def copy(self, text: str) -> None:
            if self.copied:
                raise RuntimeError("restore failed")
            super().copy(text)

    fake = RestoreFailsPyperclip("before")
    clipboard = Clipboard(fake)

    with clipboard.preserved_text("target"):
        assert fake.value == "target"

    assert "restoring the previous clipboard value failed" in caplog.text
