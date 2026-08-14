"""
Общее состояние процесса.

Это локальный dev-инструмент для одной рабочей станции, поэтому простое
in-memory состояние в виде одного объекта — осознанное упрощение,
а не заглушка "на потом". Если понадобится персистентность между
перезапусками — см. app/costs.py как пример паттерна с graceful fallback.
"""
from __future__ import annotations

import itertools
import random
import time
from dataclasses import dataclass, field

from app.config import MAX_LOG_ENTRIES, PROFILES


@dataclass
class LogEntry:
    id: int
    timestamp: str
    provider: str          # "openai" | "anthropic"
    model: str
    endpoint: str
    status: str            # "ok" | "429" | "overflow" | "invalid_json" | "stream_interrupted" | ...
    prompt_tokens: int
    completion_tokens: int
    saved_usd: float


class AppState:
    def __init__(self) -> None:
        self.chaos_mode: str = "none"
        # Шанс срабатывания хаос-режима на конкретный запрос, 1-100.
        # 100 (по умолчанию) — прежнее поведение: хаос гарантирован,
        # пока включён. Меньшие значения имитируют нестабильный сервис,
        # где сбои случаются не каждый раз — ближе к поведению реальных
        # провайдеров под нагрузкой.
        self.chaos_probability: int = 100
        self.active_profile: str = "default"
        self.logs: list[LogEntry] = []
        self._log_id_counter = itertools.count(1)

        # ROI-статистика с момента старта процесса
        self.total_requests: int = 0
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_saved_usd: float = 0.0

    def current_latency_ms(self) -> int:
        return PROFILES.get(self.active_profile, PROFILES["default"])["latency_ms"]

    def roll_chaos_mode(self) -> str:
        """Бросок монетки на один запрос: если хаос выключен — всегда
        "none". Если включён — срабатывает с вероятностью
        chaos_probability процентов, иначе тоже "none" (запрос
        обрабатывается как обычно). Вызывается ровно один раз в начале
        обработки запроса — результат используется для ВСЕЙ дальнейшей
        логики этого запроса (и мгновенных ошибок, и invalid_json,
        и обрыва стрима), чтобы сценарий был цельным, а не "наполовину
        сработавшим"."""
        if self.chaos_mode == "none":
            return "none"
        if self.chaos_probability >= 100:
            return self.chaos_mode
        return self.chaos_mode if random.randint(1, 100) <= self.chaos_probability else "none"

    def add_log(
        self,
        provider: str,
        model: str,
        endpoint: str,
        status: str,
        prompt_tokens: int,
        completion_tokens: int,
        saved_usd: float,
    ) -> LogEntry:
        entry = LogEntry(
            id=next(self._log_id_counter),
            timestamp=time.strftime("%H:%M:%S"),
            provider=provider,
            model=model,
            endpoint=endpoint,
            status=status,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            saved_usd=saved_usd,
        )
        self.logs.append(entry)
        if len(self.logs) > MAX_LOG_ENTRIES:
            self.logs.pop(0)

        self.total_requests += 1
        self.total_prompt_tokens += prompt_tokens
        self.total_completion_tokens += completion_tokens
        self.total_saved_usd += saved_usd
        return entry


# Единственный экземпляр состояния на процесс
state = AppState()
