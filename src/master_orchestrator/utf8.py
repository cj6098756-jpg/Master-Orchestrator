"""Windows UTF-8 output fixup."""

import sys
import io


def ensure_utf8():
    """Ensure stdout/stderr use UTF-8 on Windows.

    Prevents encoding errors when printing Unicode characters
    (e.g., thermodynamic symbols, box-drawing characters).
    """
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(
            sys.stdout.buffer, encoding="utf-8", errors="replace"
        )
        sys.stderr = io.TextIOWrapper(
            sys.stderr.buffer, encoding="utf-8", errors="replace"
        )
