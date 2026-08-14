"""
Тарифы на токены и расчёт "спасённого бюджета".

Реализует стратегию минимизации риска устаревания цен из п. 5.1 манифеста:
1. costs.json в корне — базовые тарифы на момент релиза.
2. При старте пытаемся асинхронно обновить их из внешнего источника.
3. Если сети нет — бесшовно работаем на локальной копии и показываем
   в UI дату, на которую актуальны тарифы.

REMOTE_COSTS_URL — заглушка на будущий репозиторий/зеркало проекта.
Замените на реальный URL, когда он появится; до тех пор обновление
будет мягко проваливаться и приложение продолжит работать на
локальном costs.json — это ожидаемое поведение, а не баг.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from app.config import COSTS_FILE

logger = logging.getLogger("fauxlm.costs")

# TODO: заменить на реальный адрес зеркала цен проекта, когда он будет развёрнут.
REMOTE_COSTS_URL: str | None = None

_costs_cache: dict = {}


def load_costs() -> dict:
    global _costs_cache
    try:
        with open(COSTS_FILE, "r", encoding="utf-8") as f:
            _costs_cache = json.load(f)
    except Exception as exc:
        logger.warning("Не удалось прочитать %s (%s) — использую пустые тарифы.", COSTS_FILE, exc)
        _costs_cache = {"_meta": {"updated_at": "unknown", "source": "empty"}, "models": {},
                         "default_model_fallback": {"input_per_1m": 3.0, "output_per_1m": 15.0}}
    return _costs_cache


async def refresh_costs_from_remote() -> None:
    """Фоновая попытка обновить тарифы. Вызывается на старте приложения.
    Любая ошибка (нет сети, нет URL, таймаут) — не критична."""
    if not REMOTE_COSTS_URL:
        return
    try:
        import httpx
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(REMOTE_COSTS_URL)
            resp.raise_for_status()
            data = resp.json()
        global _costs_cache
        _costs_cache = data
        with open(COSTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("Тарифы обновлены из %s", REMOTE_COSTS_URL)
    except Exception as exc:
        logger.info("Обновление тарифов пропущено (офлайн-режим): %s", exc)


def get_rates(model: str) -> dict:
    models = _costs_cache.get("models", {})
    return models.get(model, _costs_cache.get(
        "default_model_fallback", {"input_per_1m": 3.0, "output_per_1m": 15.0}
    ))


def calc_saved_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Считает, сколько денег НЕ было потрачено, потому что запрос ушёл
    в FauxLM, а не к реальному провайдеру."""
    rates = get_rates(model)
    cost = (
        prompt_tokens / 1_000_000 * rates.get("input_per_1m", 0)
        + completion_tokens / 1_000_000 * rates.get("output_per_1m", 0)
    )
    return round(cost, 6)


def costs_meta() -> dict:
    return _costs_cache.get("_meta", {"updated_at": "unknown", "source": "unknown"})
