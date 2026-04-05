from __future__ import annotations

from dataclasses import dataclass, field

from scaffold.models import estimate_tokens


@dataclass(frozen=True)
class ContextMessage:
    role: str
    content: str


@dataclass
class ContextManager:
    """Conversation context with token-aware trimming and typed messages."""

    messages: list[ContextMessage] = field(default_factory=list)

    def add_user(self, content: str) -> None:
        self.messages.append(ContextMessage(role="user", content=content))

    def add_assistant(self, content: str) -> None:
        self.messages.append(ContextMessage(role="assistant", content=content))

    def add_system(self, content: str) -> None:
        self.messages.append(ContextMessage(role="system", content=content))

    def total_tokens(self) -> int:
        return sum(estimate_tokens(m.content) for m in self.messages)

    def trim_to_fit(self, max_tokens: int) -> None:
        while self.total_tokens() > max_tokens:
            idx = next((i for i, m in enumerate(self.messages) if m.role != "system"), None)
            if idx is None:
                break
            self.messages.pop(idx)

    def to_api_messages(self) -> list[dict[str, str]]:
        return [{"role": m.role, "content": m.content} for m in self.messages if m.role != "system"]

    def system_prompt(self) -> str | None:
        for m in self.messages:
            if m.role == "system":
                return m.content
        return None

    def as_dicts(self) -> list[dict[str, str]]:
        """Compatibility helper for callers expecting dict messages."""
        return [{"role": m.role, "content": m.content} for m in self.messages]
