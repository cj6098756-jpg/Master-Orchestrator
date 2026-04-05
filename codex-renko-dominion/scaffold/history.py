from __future__ import annotations


def format_history(messages: list, n: int = 20) -> str:
    """Format recent session history into a compact multiline string."""
    recent = messages[-n:] if len(messages) > n else messages
    lines = [
        f"  [{i+1:03d}] {m['role']:10s} | {m['content'][:80].replace(chr(10), ' ')}..."
        for i, m in enumerate(recent)
    ]
    return "\n".join(lines) if lines else "  (empty history)"
