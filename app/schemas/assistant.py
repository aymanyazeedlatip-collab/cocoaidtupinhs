from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class AssistantMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=20_000)


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8_000)
    history: list[AssistantMessage] = Field(default_factory=list, max_length=20)
    context: dict[str, Any] | None = None
    document_ids: list[str] = Field(default_factory=list, max_length=3)


class AssistantKeyRequest(BaseModel):
    api_key: str = Field(min_length=20, max_length=300)
