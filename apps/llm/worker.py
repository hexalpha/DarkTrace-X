"""One loaded GGUF per service, serialized inference, bounded queue, cooperative cancellation."""
import asyncio
import json
import secrets
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    local_llm_enabled: bool = False
    local_llm_model_path: str = ""
    local_llm_context_size: int = Field(4096, ge=512, le=32768)
    local_llm_threads: int = Field(4, ge=1, le=64)
    local_llm_gpu_layers: int = Field(-1, ge=-1, le=256)
    local_llm_temperature: float = Field(0.2, ge=0, le=2)
    local_llm_max_tokens: int = Field(512, ge=16, le=4096)
    local_llm_chat_format: str = ''
    copilot_worker_key: str = ""


config = Config()
state = {"state": "OFFLINE", "model": Path(config.local_llm_model_path).name or "Not selected", "backend": "CPU", "load_failures": 0, "loaded_at": None}
model = None
lock = threading.Lock()


def load():
    global model
    if not config.local_llm_enabled:
        state["detail"] = "Local model disabled"
        return
    if not Path(config.local_llm_model_path).is_file():
        state.update(state="OFFLINE", detail="Configured GGUF file is missing")
        return
    state["state"] = "LOADING"
    try:
        from llama_cpp import Llama, llama_supports_gpu_offload
        gpu = bool(llama_supports_gpu_offload()) and config.local_llm_gpu_layers != 0
        args = dict(model_path=config.local_llm_model_path, n_ctx=config.local_llm_context_size,
                    n_threads=config.local_llm_threads, verbose=False)
        if config.local_llm_chat_format:
            args['chat_format'] = config.local_llm_chat_format
        try:
            model = Llama(**args, n_gpu_layers=config.local_llm_gpu_layers if gpu else 0)
            state["backend"] = "GPU" if gpu else "CPU"
        except Exception:
            if not gpu:
                raise
            state["load_failures"] += 1
            model = Llama(**args, n_gpu_layers=0)
            state["detail"] = "GPU load failed; CPU fallback active"
        # Some GGUF exports omit the chat template. llama-cpp's generic fallback
        # is unsuitable for Qwen; use its ChatML protocol without reloading weights.
        if not config.local_llm_chat_format and not model.metadata.get('tokenizer.chat_template') and str(model.metadata.get('general.architecture','')).startswith('qwen'):
            model.chat_format = 'chatml'
        state.update(state="ONLINE", model=model.metadata.get("general.name", state["model"]), loaded_at=time.time(), chat_format=model.chat_format)
    except Exception as exc:
        state.update(state="ERROR", detail=f"Model load failed ({type(exc).__name__})", load_failures=state["load_failures"] + 1)


@asynccontextmanager
async def lifespan(app):
    thread = threading.Thread(target=load, daemon=True)
    thread.start()
    yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None)


def authorize(token):
    if not config.copilot_worker_key or not secrets.compare_digest(token or "", config.copilot_worker_key):
        raise HTTPException(401, "Worker authentication required")


@app.get("/health")
async def health(x_worker_key: str | None = Header(None)):
    authorize(x_worker_key)
    return {**state, "busy": lock.locked(), "context_size": config.local_llm_context_size}


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(max_length=24000)


class Generate(BaseModel):
    messages: list[Message] = Field(min_length=1, max_length=24)
    temperature: float | None = Field(None, ge=0, le=2)
    max_tokens: int | None = Field(None, ge=16, le=4096)


@app.post("/generate")
async def generate(body: Generate, request: Request, x_worker_key: str | None = Header(None)):
    authorize(x_worker_key)
    if state["state"] != "ONLINE" or model is None:
        raise HTTPException(503, state["state"])
    if sum(len(m.content) for m in body.messages) > 32000:
        raise HTTPException(413, "Context too large")
    if not lock.acquire(blocking=False):
        raise HTTPException(429, "Model busy; retry shortly")
    loop = asyncio.get_running_loop()
    queue = asyncio.Queue(maxsize=32)
    stopped = threading.Event()

    def push(item):
        future = asyncio.run_coroutine_threadsafe(queue.put(item), loop)
        while not stopped.is_set():
            try:
                future.result(timeout=0.2)
                return
            except TimeoutError:
                continue
        future.cancel()

    def infer():
        started = time.monotonic()
        try:
            # Clear KV state between requests; conversation history is explicitly scoped by API.
            model.reset()
            count = 0
            iterator = model.create_chat_completion(messages=[m.model_dump() for m in body.messages],
                stream=True, temperature=body.temperature if body.temperature is not None else config.local_llm_temperature,
                max_tokens=min(body.max_tokens or config.local_llm_max_tokens, config.local_llm_max_tokens))
            for chunk in iterator:
                if stopped.is_set():
                    break
                choice = chunk["choices"][0]
                delta = choice.get("delta", {}).get("content", "")
                if delta:
                    count += 1
                    push({"type": "delta", "text": delta})
                if choice.get("finish_reason"):
                    push({"type": "usage", "finish_reason": choice["finish_reason"], "latency_ms": round((time.monotonic()-started)*1000), "output_chunks": count})
            push({"type": "done"})
        except Exception as exc:
            push({"type": "error", "message": f"Inference failed ({type(exc).__name__}); check context size and runtime"})
        finally:
            lock.release()

    async def stream():
        threading.Thread(target=infer, daemon=True).start()
        try:
            while True:
                try:
                    item = await asyncio.wait_for(queue.get(), timeout=10)
                except TimeoutError:
                    if await request.is_disconnected():
                        break
                    yield json.dumps({"type": "heartbeat"}) + "\n"
                    continue
                yield json.dumps(item) + "\n"
                if item["type"] in {"done", "error"}:
                    break
        finally:
            stopped.set()
    return StreamingResponse(stream(), media_type="application/x-ndjson")
