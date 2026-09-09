import json
import urllib.error
import urllib.request

from logillm.config import LLMConfig, llm_config


def ask(
    system: str,
    user: str,
    config: LLMConfig | None = None,
    temperature: float = 0.0,
) -> str:
    """Sends one chat request and returns the assistant's reply.

    Works with any OpenAI-compatible endpoint.
    Pass config explicitly to run the same prompt against different models.
    """
    config = config or llm_config()

    payload = {
        "model": config.model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        **config.extra_payload,
    }
    request = urllib.request.Request(
        f"{config.base_url}/chat/completions",
        data=json.dumps(payload).encode(),
        headers=config.headers,
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.load(response)
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"[{config.provider}] HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"[{config.provider}] cannot reach {config.base_url}: {error.reason}") from error

    return body["choices"][0]["message"]["content"]
