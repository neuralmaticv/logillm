import json
import urllib.error
import urllib.request
from dataclasses import dataclass

from logillm.config import LLMConfig, llm_config

Message = dict[str, str]

TIMEOUT_S = 120


@dataclass(frozen=True)
class Usage:
    """Token counts the server reported for one request."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    @property
    def billed_prompt_tokens(self) -> int:
        """Prompt tokens the server had to process, i.e. those not served from cache."""
        return self.prompt_tokens - self.cached_tokens

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            self.prompt_tokens + other.prompt_tokens,
            self.completion_tokens + other.completion_tokens,
            self.cached_tokens + other.cached_tokens,
        )


@dataclass(frozen=True)
class Reply:
    """One assistant reply and the tokens it cost."""

    text: str
    usage: Usage


def _usage(body: dict) -> Usage:
    """Read token counts from a response, tolerating servers that omit them."""
    raw = body.get("usage")
    if not isinstance(raw, dict):
        return Usage()

    details = raw.get("prompt_tokens_details")
    cached = details.get("cached_tokens", 0) if isinstance(details, dict) else 0
    return Usage(
        prompt_tokens=int(raw.get("prompt_tokens", 0)),
        completion_tokens=int(raw.get("completion_tokens", 0)),
        cached_tokens=int(cached or 0),
    )


def chat(
    messages: list[Message],
    config: LLMConfig | None = None,
    temperature: float = 0.0,
) -> Reply:
    """Send a conversation and return the assistant's next reply with its token usage.

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
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            body = json.load(response)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"[{config.provider}] LLM response is not valid JSON.") from error
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"[{config.provider}] HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"[{config.provider}] cannot reach {config.base_url}: {error.reason}") from error
    except TimeoutError as error:
        raise RuntimeError(f"[{config.provider}] no response within {TIMEOUT_S} s.") from error

    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError(f"[{config.provider}] LLM response has an unexpected structure.") from error
    if not isinstance(content, str):
        raise TypeError(f"[{config.provider}] LLM response content is not text.")
    return Reply(content, _usage(body))


def ask(
    system: str,
    user: str,
    config: LLMConfig | None = None,
    temperature: float = 0.0,
) -> Reply:
    """Send a system and a user message and return the assistant's reply."""
    messages: list[Message] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    return chat(messages, config=config, temperature=temperature)
