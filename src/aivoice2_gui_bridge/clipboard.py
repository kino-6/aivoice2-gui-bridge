from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from types import ModuleType
from typing import Any

LOGGER = logging.getLogger(__name__)


class ClipboardError(RuntimeError):
    """Raised when clipboard access fails."""


class Clipboard:
    """Small wrapper around pyperclip with preservation support."""

    def __init__(self, pyperclip_module: ModuleType | Any | None = None, logger: logging.Logger = LOGGER) -> None:
        self._pyperclip = pyperclip_module
        self._logger = logger

    @property
    def pyperclip(self) -> ModuleType | Any:
        if self._pyperclip is None:
            import pyperclip

            self._pyperclip = pyperclip
        return self._pyperclip

    def read(self) -> str:
        try:
            value = self.pyperclip.paste()
        except Exception as exc:  # pyperclip raises platform-specific exceptions
            raise ClipboardError(
                "Failed to read the clipboard. Check that clipboard access is available for this session."
            ) from exc
        return "" if value is None else str(value)

    def write(self, text: str) -> None:
        try:
            self.pyperclip.copy(text)
        except Exception as exc:
            raise ClipboardError(
                "Failed to write to the clipboard. Check that clipboard access is available for this session."
            ) from exc

    @contextmanager
    def preserved_text(self, text: str, *, restore: bool = True, dry_run: bool = False) -> Iterator[None]:
        """Copy text for an operation and restore the previous value when possible."""
        previous: str | None = None
        has_previous = False

        if dry_run:
            self._logger.info("Dry run: would copy text to clipboard")
            yield
            return

        if restore:
            try:
                previous = self.read()
                has_previous = True
            except ClipboardError as exc:
                self._logger.warning("Could not read existing clipboard; restore will be skipped: %s", exc)

        self.write(text)
        try:
            yield
        finally:
            if restore and has_previous:
                try:
                    self.write(previous if previous is not None else "")
                except ClipboardError as exc:
                    self._logger.warning(
                        "Text was pasted, but restoring the previous clipboard value failed: %s",
                        exc,
                    )
