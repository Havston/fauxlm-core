"""
Трансляция событий в панель мониторинга через WebSocket.

Раньше здесь рассылались HTML-фрагменты с hx-swap-oob под расширение
htmx-ws. Отказались от этого: расширение подгружается с CDN отдельным
файлом от ядра htmx, и малейшее рассогласование версий (или просто
агрессивное кеширование браузером) тихо ломает обработку сообщений —
без ошибок в консоли, просто ничего не происходит до перезагрузки
страницы. Вместо этого рассылаем простой JSON, а рендерингом на клиенте
занимается десяток строк собственного JS (см. dashboard.html) — меньше
внешних зависимостей, проще диагностировать, если что-то пойдёт не так.
"""
from __future__ import annotations

import json
import logging

from fastapi import WebSocket

logger = logging.getLogger("fauxlm.ws")


class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast_json(self, data: dict) -> None:
        payload = json.dumps(data, ensure_ascii=False)
        dead: list[WebSocket] = []
        for ws in self.active:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
