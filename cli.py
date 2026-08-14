#!/usr/bin/env python3
"""
Запуск FauxLM Core из командной строки.

Использование:
    python cli.py                    # запуск с настройками по умолчанию
    python cli.py --port 9000        # свой порт
    python cli.py --host 127.0.0.1   # только локальный доступ
"""
from __future__ import annotations

import argparse

import uvicorn

from app.config import HOST, PORT


def main() -> None:
    parser = argparse.ArgumentParser(description="FauxLM Core — открытый локальный мок-сервер для LLM API")
    parser.add_argument("--host", default=HOST, help=f"Хост (по умолчанию {HOST})")
    parser.add_argument("--port", type=int, default=PORT, help=f"Порт (по умолчанию {PORT})")
    parser.add_argument("--reload", action="store_true", help="Автоперезагрузка при изменении кода (для разработки)")
    args = parser.parse_args()

    print(f"FauxLM Core запускается на http://{args.host}:{args.port}")
    print(f"OpenAI-совместимый эндпоинт: http://localhost:{args.port}/v1/chat/completions")
    print(f"Anthropic-совместимый эндпоинт: http://localhost:{args.port}/v1/messages")

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
