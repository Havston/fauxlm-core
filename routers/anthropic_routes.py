from __future__ import annotations

import asyncio
import json
import time
import uuid

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.costs import calc_saved_usd
from app.generator import chunk_text, generate_reply_text
from app.schemas import AnthropicRequest
from app.state import state
from app.tokenizer import count_messages_tokens, count_tokens
from app.ws_manager import manager

router = APIRouter()


def _sse_event(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


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


@router.post("/v1/messages")
async def messages(payload: AnthropicRequest):
    msgs = [m.model_dump() for m in payload.messages]
    if payload.system:
        msgs = [{"role": "system", "content": payload.system}] + msgs
    prompt_tokens = count_messages_tokens(msgs, payload.model)

    latency = state.current_latency_ms() / 1000
    await asyncio.sleep(latency)

    reply_text = generate_reply_text(msgs, max_words=payload.max_tokens)
    completion_tokens = count_tokens(reply_text, payload.model)
    saved = calc_saved_usd(payload.model, prompt_tokens, completion_tokens)
    status_label = "ok"

    if payload.stream:
        return StreamingResponse(
            _stream_anthropic(payload.model, reply_text, prompt_tokens, completion_tokens, saved),
            media_type="text/event-stream",
        )

    entry = state.add_log(
        "anthropic", payload.model, "/v1/messages",
        status_label, prompt_tokens, completion_tokens, saved,
    )
    await manager.broadcast_json(_log_event_payload(entry))

    return {
        "id": f"msg_{uuid.uuid4().hex[:24]}",
        "type": "message",
        "role": "assistant",
        "model": payload.model,
        "content": [{"type": "text", "text": reply_text}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": prompt_tokens, "output_tokens": completion_tokens},
    }


async def _stream_anthropic(model, reply_text, prompt_tokens, completion_tokens, saved):
    message_id = f"msg_{uuid.uuid4().hex[:24]}"
    status_label = "ok"
    chunks = chunk_text(reply_text)

    yield _sse_event("message_start", {
        "type": "message_start",
        "message": {
            "id": message_id, "type": "message", "role": "assistant", "content": [],
            "model": model, "stop_reason": None, "stop_sequence": None,
            "usage": {"input_tokens": prompt_tokens, "output_tokens": 0},
        },
    })
    yield _sse_event("content_block_start", {
        "type": "content_block_start", "index": 0,
        "content_block": {"type": "text", "text": ""},
    })

    for piece in chunks:
        yield _sse_event("content_block_delta", {
            "type": "content_block_delta", "index": 0,
            "delta": {"type": "text_delta", "text": piece},
        })
        await asyncio.sleep(0.02)

    yield _sse_event("content_block_stop", {"type": "content_block_stop", "index": 0})
    yield _sse_event("message_delta", {
        "type": "message_delta",
        "delta": {"stop_reason": "end_turn", "stop_sequence": None},
        "usage": {"output_tokens": completion_tokens},
    })
    yield _sse_event("message_stop", {"type": "message_stop"})

    entry = state.add_log(
        "anthropic", model, "/v1/messages",
        status_label, prompt_tokens, completion_tokens, saved,
    )
    await manager.broadcast_json(_log_event_payload(entry))
