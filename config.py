"""
Конфигурация AirCode Core.

Это открытая (MIT) часть AirCode — только моковые эндпоинты. Никаких
профилей, хаос-сценариев или лицензий здесь нет: это всё часть AirCode
Pro, которая живёт в закрытом репозитории команды и в этот открытый
экспорт не попадает. Подробности — в README.md этого репозитория.
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
COSTS_FILE = BASE_DIR / "costs.json"

HOST = os.environ.get("AIRCODE_HOST", "0.0.0.0")
PORT = int(os.environ.get("AIRCODE_PORT", "8080"))

# Максимум строк лога, которые держим в памяти (используется общим
# движком — app/state.py, — но нигде не отображается без Pro-панели).
MAX_LOG_ENTRIES = 200

# app/state.py (общий файл с AirCode Pro, копируется без изменений при
# экспорте) ожидает PROFILES с латентностью по хотя бы одному профилю.
# В Core профиль всегда один — без переключения, без хаос-сценариев.
PROFILES: dict[str, dict] = {
    "default": {
        "label": "Обычная работа",
        "latency_ms": 150,
        "default_chaos": "none",
    },
}
