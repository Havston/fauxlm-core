from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------- OpenAI-совместимый формат ----------

class OpenAIMessage(BaseModel):
    role: str
    content: Any = None


class OpenAIResponseFormat(BaseModel):
    type: str = "text"                       # "text" | "json_object" | "json_schema"
    json_schema: Optional[dict] = None


class OpenAIChatRequest(BaseModel):
    model: str = "gpt-4o"
    messages: list[OpenAIMessage] = Field(default_factory=list)
    stream: bool = False
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    response_format: Optional[OpenAIResponseFormat] = None
    tools: Optional[list[dict]] = None


# ---------- Anthropic-совместимый формат ----------

class AnthropicMessage(BaseModel):
    role: str
    content: Any = None


class AnthropicRequest(BaseModel):
    model: str = "claude-sonnet-5"
    messages: list[AnthropicMessage] = Field(default_factory=list)
    system: Optional[str] = None
    max_tokens: int = 1024
    stream: bool = False
    temperature: Optional[float] = 1.0
