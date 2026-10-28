"""Debug flags ported from vscode-textmate's ``src/debug.ts``."""

from __future__ import annotations

import os

__all__ = ["DebugFlags", "UseOnigurumaFindOptions"]


class DebugFlags:
    """Flags controlling optional debug behavior."""

    InDebugMode = bool(os.environ.get("VSCODE_TEXTMATE_DEBUG"))

    @staticmethod
    def is_in_debug_mode() -> bool:
        """Read the flag at a module reload boundary, as the parser does."""
        return bool(os.environ.get("VSCODE_TEXTMATE_DEBUG"))


# vscode-textmate currently delegates find-option handling to its Oniguruma layer.
UseOnigurumaFindOptions = False
