import json
import urllib.error
import urllib.request

from logillm.config import LLMConfig, llm_config

Message = dict[str, str]


def chat(
    messages: list[Message],
    config: LLMConfig | None = None,
    temperature: float = 0.0,
) -> str:
    """Send a conversation and return the assistant's next reply.

    Works with any OpenAI-compatible endpoint.
    Pass config explicitly to run the same prompt against different models.
    """
    config = config or llm_config()

    payload: dict[str, object] = {
        "model": config.model,
        "messages": messages,
        **config.extra_payload,
    }

    if config.send_temperature:
        payload["temperature"] = temperature

    request = urllib.request.Request(
        f"{config.base_url}/chat/completions",
        data=json.dumps(payload).encode(),
        headers=config.headers,
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = json.load(response)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"[{config.provider}] LLM response is not valid JSON.") from error
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"[{config.provider}] HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"[{config.provider}] cannot reach {config.base_url}: {error.reason}") from error

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError(f"[{config.provider}] LLM response has an unexpected structure.") from error
    if not isinstance(content, str):
        raise TypeError(f"[{config.provider}] LLM response content is not text.")
    return content


def ask(
    system: str,
    user: str,
    config: LLMConfig | None = None,
    temperature: float = 0.0,
) -> str:
    """Send a system and a user message and return the assistant's reply."""
    messages: list[Message] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    return chat(messages, config=config, temperature=temperature)
