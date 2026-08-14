"""
Генерация синтетического контента ответов.

Ничего не уходит к реальным провайдерам — весь текст и все структуры
данных генерируются локально, детерминированно достаточно, чтобы быть
предсказуемыми в тестах, но с лёгкой вариативностью на основе последнего
сообщения пользователя.
"""
from __future__ import annotations

import random

_CANNED_SENTENCES = [
    "Это синтетический ответ, сгенерированный локально движком FauxLM.",
    "Реальный запрос к внешнему провайдеру не выполнялся.",
    "Вы можете настроить хаос-сценарии в панели, чтобы проверить обработку ошибок.",
    "Этот текст создан исключительно для целей локальной разработки и тестирования.",
    "FauxLM эмулирует потоковую генерацию токен за токеном через SSE.",
]


def last_user_message(messages: list[dict]) -> str:
    for msg in reversed(messages):
        role = msg.get("role")
        if role == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                parts = [b.get("text", "") for b in content if isinstance(b, dict)]
                return " ".join(parts)
            return str(content)
    return ""


def generate_reply_text(messages: list[dict], max_words: int | None = None) -> str:
    """Формирует связный синтетический ответ на основе последнего сообщения
    пользователя — не имитирует "интеллект", а честно даёт понятный
    заглушечный текст подходящей длины."""
    user_text = last_user_message(messages).strip()
    intro = (
        f'Синтетический мок-ответ на сообщение: "{user_text[:120]}"'
        if user_text else "Синтетический мок-ответ FauxLM."
    )
    body = " ".join(random.sample(_CANNED_SENTENCES, k=min(3, len(_CANNED_SENTENCES))))
    full = f"{intro} {body}"

    if max_tokens_hint := max_words:
        words = full.split()
        full = " ".join(words[:max_tokens_hint])

    return full


def chunk_text(text: str) -> list[str]:
    """Разбивает текст на маленькие куски для имитации SSE-стриминга
    посимвольно/пословно, как это делают реальные провайдеры."""
    words = text.split(" ")
    chunks = []
    for i, w in enumerate(words):
        chunks.append(w + (" " if i < len(words) - 1 else ""))
    return chunks


# ---------- Генерация фейковых данных по JSON Schema (Structured Outputs) ----------

def _fake_value_for_schema(schema: dict, key_hint: str = "") -> object:
    schema_type = schema.get("type", "string")

    if "enum" in schema and schema["enum"]:
        return random.choice(schema["enum"])

    if schema_type == "object":
        props = schema.get("properties", {})
        return {k: _fake_value_for_schema(v, key_hint=k) for k, v in props.items()}

    if schema_type == "array":
        item_schema = schema.get("items", {"type": "string"})
        return [_fake_value_for_schema(item_schema, key_hint=key_hint) for _ in range(2)]

    if schema_type == "integer":
        return random.randint(1, 100)

    if schema_type == "number":
        return round(random.uniform(1, 100), 2)

    if schema_type == "boolean":
        return random.choice([True, False])

    # string по умолчанию
    return f"mock_{key_hint or 'value'}"


def generate_from_json_schema(json_schema: dict) -> dict:
    """Генерирует валидный (по структуре) объект под переданную
    JSON Schema. Покрывает базовые типы — этого достаточно для
    тестирования кода, который парсит structured outputs."""
    # OpenAI присылает схему как {"name": ..., "schema": {...}, "strict": ...}
    inner = json_schema.get("schema", json_schema)
    return _fake_value_for_schema(inner)
