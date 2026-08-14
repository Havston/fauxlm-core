"""
Подсчёт токенов.

Важный нюанс: tiktoken при первом обращении к encoding_for_model() может
попытаться скачать BPE-таблицы из сети (если их ещё нет в локальном кэше
~/.tiktoken_cache). Это противоречит заявленному в манифесте принципу
"FauxLM работает на 100% автономно, без интернета".

Поэтому здесь тот же паттерн graceful degradation, что описан в манифесте
для costs.json (п. 5.1): пробуем точный BPE-подсчёт, и если это по любой
причине не удаётся (нет сети при первом запуске, нет кэша, установлен не
tiktoken) — бесшовно откатываемся на приближённый счётчик и один раз
логируем предупреждение, не роняя сервер.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("fauxlm.tokenizer")

_tiktoken_available = True
_warned_fallback = False

try:
    import tiktoken
    _encoding_cache: dict[str, "tiktoken.Encoding"] = {}
except ImportError:
    _tiktoken_available = False
    _encoding_cache = {}


def _get_encoding(model: str):
    if model in _encoding_cache:
        return _encoding_cache[model]
    try:
        enc = tiktoken.encoding_for_model(model)
    except Exception:
        # Модель незнакома tiktoken (напр. deepseek-chat, claude-*) —
        # используем универсальную кодировку, применяемую в GPT-4o.
        enc = tiktoken.get_encoding("cl100k_base")
    _encoding_cache[model] = enc
    return enc


def _approx_token_count(text: str) -> int:
    """Грубая офлайн-оценка: ~4 символа на токен для английского текста,
    с поправкой на количество слов, чтобы не давать слишком заниженный
    результат на коротких строках."""
    if not text:
        return 0
    by_chars = max(1, len(text) // 4)
    by_words = max(1, len(text.split()))
    return max(by_chars, by_words)


def count_tokens(text: str, model: str = "gpt-4o") -> int:
    """Считает токены для произвольного текста.

    Используется и для OpenAI-, и для Anthropic-совместимых эндпоинтов:
    у Claude нет публично распространяемого офлайн-токенизатора, поэтому
    для него тоже применяется cl100k_base как разумное приближение —
    этого достаточно для целей мокинга и ROI-калькулятора, не для
    выставления счетов.
    """
    global _warned_fallback
    if not text:
        return 0

    if _tiktoken_available:
        try:
            enc = _get_encoding(model)
            return len(enc.encode(text, disallowed_special=()))
        except Exception as exc:
            if not _warned_fallback:
                logger.warning(
                    "tiktoken недоступен (%s) — переключаюсь на приближённый "
                    "офлайн-подсчёт токенов. Работа сервера не прерывается.",
                    exc,
                )
                _warned_fallback = True

    return _approx_token_count(text)


def count_messages_tokens(messages: list[dict], model: str = "gpt-4o") -> int:
    """Считает токены для массива сообщений формата [{role, content}, ...]
    плюс небольшая служебная надбавка за форматирование роли/разделители,
    аналогично тому, как это делает OpenAI."""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            # content может быть массивом блоков {type: text/image, ...}
            text_parts = [
                block.get("text", "") for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            content = " ".join(text_parts)
        total += count_tokens(str(content), model)
        total += 4  # служебная надбавка на сообщение (роль, разделители)
    total += 2  # надбавка на весь массив
    return total
