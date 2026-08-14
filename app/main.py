from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.costs import load_costs, refresh_costs_from_remote
from app.routers import anthropic_routes, openai_routes

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
logger = logging.getLogger("fauxlm")

app = FastAPI(title="FauxLM Core", description="Открытый локальный мок-сервер для LLM API")

app.include_router(openai_routes.router)
app.include_router(anthropic_routes.router)

_ROOT_PAGE = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<title>FauxLM Core</title>
<style>
  body { font-family: -apple-system, Segoe UI, Roboto, sans-serif; background:#0f1117;
         color:#e6e8ec; max-width:640px; margin:60px auto; padding:0 20px; line-height:1.6; }
  h1 { font-size:22px; }
  code { background:#1e2230; padding:2px 6px; border-radius:4px; }
  a { color:#5b8cff; }
</style>
</head>
<body>
  <h1>FauxLM Core</h1>
  <p>Сервер запущен и обрабатывает запросы к OpenAI- и Anthropic-совместимым эндпоинтам:</p>
  <ul>
    <li><code>POST /v1/chat/completions</code></li>
    <li><code>POST /v1/messages</code></li>
  </ul>
  <p>Панель мониторинга, конструктор ИИ-катастроф и ROI-калькулятор —
  часть FauxLM Pro. Подробности: <a href="https://github.com/">страница проекта</a>.</p>
  <!-- TODO: заменить ссылку выше на реальную страницу продукта/продаж, когда она будет готова -->
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def root():
    return _ROOT_PAGE


@app.on_event("startup")
async def startup() -> None:
    load_costs()
    try:
        await refresh_costs_from_remote()
    except Exception:
        pass
