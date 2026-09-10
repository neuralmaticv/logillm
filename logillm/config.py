import os
from dataclasses import dataclass, field
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def load_env(path: Path = ENV_FILE) -> None:
    """Reads KEY=VALUE lines from .env file and sets them in os.environ if not already set"""
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip("\"'")
        if value:
            os.environ.setdefault(key.strip(), value)


@dataclass(frozen=True)
class LLMConfig:
    provider: str
    base_url: str
    model: str
    api_key: str | None = None
    extra_payload: dict[str, object] = field(default_factory=dict)
    send_temperature: bool = True

    @property
    def headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


def _required(name: str, provider: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise ValueError(f"{name} is not set, required by provider '{provider}'. See .env.example.")
    return value


def llm_config(provider: str | None = None) -> LLMConfig:
    """Builds the configuration for one provider: 'local' (vLLM) or 'openai'."""
    load_env()
    provider = (provider or os.environ.get("LOGILLM_LLM_PROVIDER", "local")).lower()

    if provider == "local":
        thinking = os.environ.get("LOGILLM_LOCAL_THINKING", "0") == "1"
        return LLMConfig(
            provider="local",
            base_url=os.environ.get("LOGILLM_LOCAL_URL", "http://127.0.0.1:8111/v1"),
            model=os.environ.get("LOGILLM_LOCAL_MODEL", "Qwen/Qwen3.5-9B"),
            extra_payload={"chat_template_kwargs": {"enable_thinking": thinking}},
        )

    if provider == "openai":
        return LLMConfig(
            provider="openai",
            base_url=os.environ.get("LOGILLM_OPENAI_URL", "https://api.openai.com/v1"),
            model=_required("LOGILLM_OPENAI_MODEL", "openai"),
            api_key=_required("OPENAI_API_KEY", "openai"),
            send_temperature=False,
        )

    raise ValueError(f"Unknown provider '{provider}'. Use 'local' or 'openai'.")
