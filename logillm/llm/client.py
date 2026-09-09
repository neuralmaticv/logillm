import json
import urllib.request

from logillm.config import BASE_URL, MODEL


def ask(system: str, user: str, temperature: float = 0.0) -> str:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
    }
    request = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        body = json.load(response)
    return body["choices"][0]["message"]["content"]
