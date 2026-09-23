"""Safe provider check: never prints keys, request headers, or provider error bodies."""
import asyncio
from app.core.config import get_settings
from app.services.ai import AIRouter


async def main():
    settings = get_settings()
    router = AIRouter(settings)
    print("OpenAI model:", settings.openai_model)
    try:
        result = await router._dispatch("openai", settings.openai_model, [{"role": "user", "content": "Reply with exactly: Connection verified"}])
        print("OpenAI completion:", "verified" if result.strip() else "empty response")
    except Exception as exc:
        code = getattr(exc, "code", "unknown")
        safe_code = code if code in {"insufficient_quota", "rate_limit_exceeded", "model_not_found", "invalid_api_key"} else "unclassified"
        print("OpenAI status:", type(exc).__name__, "HTTP", getattr(exc, "status_code", "unavailable"), "reason:", safe_code)
    scans = await router.scan_local_models()
    for scan in scans:
        print(scan["provider"], "reachable:", scan["reachable"], "models:", scan["models"])


if __name__ == "__main__":
    asyncio.run(main())
