# FauxLM Core

Открытый (MIT) локальный синтетический мок-сервер для разработчиков
ИИ-агентов и LLM-приложений. Эмулирует OpenAI- и Anthropic-совместимые
эндпоинты полностью офлайн — без единого реального запроса к
провайдерам, без ключей API, без сетевой зависимости.

## Быстрый старт

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python cli.py
```

Сервер поднимется на `http://localhost:8080`.

## Подключение SDK

```bash
export OPENAI_BASE_URL="http://localhost:8080/v1"
export ANTHROPIC_BASE_URL="http://localhost:8080/v1"
```

Ключ API может быть любой непустой строкой — FauxLM его не проверяет.

⚠️ У Anthropic SDK другая конвенция `base_url`, чем у OpenAI: без `/v1`
на конце (SDK сам его добавляет). У OpenAI SDK — с `/v1`. Подробности и
матрица совместимости с LangChain/LlamaIndex — в документации проекта.

## Что умеет Core

- `POST /v1/chat/completions` — OpenAI-совместимый эндпоинт, включая SSE-стриминг
- `POST /v1/messages` — Anthropic-совместимый эндпоинт, включая SSE-стриминг
- Подсчёт токенов (offline-friendly, с graceful fallback, если недоступен tiktoken)
- Structured Outputs (генерация валидных данных по переданной JSON Schema)

## FauxLM Pro

Панель мониторинга в реальном времени, конструктор ИИ-катастроф
(429 / 401 / 500 / 503 / timeout / обрыв стрима / повреждённые
structured outputs, включая вероятностный режим срабатывания) и
ROI-калькулятор сэкономленного бюджета — часть FauxLM Pro.

## Лицензия

MIT — см. [LICENSE](LICENSE).
