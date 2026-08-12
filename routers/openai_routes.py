from __future__ import annotations

import asyncio
import json
import time
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.costs import calc_saved_usd
from app.generator import chunk_text, generate_from_json_schema, generate_reply_text
from app.schemas import OpenAIChatRequest
from app.state import state
from app.tokenizer import count_messages_tokens, count_tokens
from app.ws_manager import manager

router = APIRouter()


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


def _log_event_payload(entry) -> dict:
    return {
        "id": entry.id,
        "timestamp": entry.timestamp,
        "provider": entry.provider,
        "model": entry.model,
        "endpoint": entry.endpoint,
        "status": entry.status,
        "prompt_tokens": entry.prompt_tokens,
        "completion_tokens": entry.completion_tokens,
        "saved_usd": entry.saved_usd,
        "total_requests": state.total_requests,
        "total_saved_usd": state.total_saved_usd,
        "total_tokens": state.total_prompt_tokens + state.total_completion_tokens,
    }


@router.post("/v1/chat/completions")
async def chat_completions(payload: OpenAIChatRequest):
    messages = [m.model_dump() for m in payload.messages]
    prompt_tokens = count_messages_tokens(messages, payload.model)

    latency = state.current_latency_ms() / 1000
    await asyncio.sleep(latency)

    wants_json_schema = (
        payload.response_format and payload.response_format.type == "json_schema"
        and payload.response_format.json_schema
    )
    if wants_json_schema:
        reply_text = json.dumps(
            generate_from_json_schema(payload.response_format.json_schema),
            ensure_ascii=False,
        )
    else:
        reply_text = generate_reply_text(messages, max_words=payload.max_tokens)

    completion_tokens = count_tokens(reply_text, payload.model)
    saved = calc_saved_usd(payload.model, prompt_tokens, completion_tokens)
    status_label = "ok"

    if payload.stream:
        return StreamingResponse(
            _stream_openai(payload.model, reply_text, prompt_tokens, completion_tokens, saved, status_label),
            media_type="text/event-stream",
        )

    entry = state.add_log(
        "openai", payload.model, "/v1/chat/completions",
        status_label, prompt_tokens, completion_tokens, saved,
    )
    await manager.broadcast_json(_log_event_payload(entry))

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:24]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": payload.model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": reply_text},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


async def _stream_openai(model, reply_text, prompt_tokens, completion_tokens, saved, status_label):
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:24]}"
    created = int(time.time())

    yield _sse({
        "id": completion_id, "object": "chat.completion.chunk", "created": created,
        "model": model, "choices": [{"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}],
    })

    for piece in chunk_text(reply_text):
        yield _sse({
            "id": completion_id, "object": "chat.completion.chunk", "created": created,
            "model": model, "choices": [{"index": 0, "delta": {"content": piece}, "finish_reason": None}],
        })
        await asyncio.sleep(0.02)

    yield _sse({
        "id": completion_id, "object": "chat.completion.chunk", "created": created,
        "model": model, "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    })
    yield "data: [DONE]\n\n"

    entry = state.add_log(
        "openai", model, "/v1/chat/completions",
        status_label, prompt_tokens, completion_tokens, saved,
    )
    await manager.broadcast_json(_log_event_payload(entry))
