import os

BASE_URL = os.environ.get("LOGILLM_LLM_URL", "http://127.0.0.1:8000/v1")
MODEL = os.environ.get("LOGILLM_LLM_MODEL", "Qwen/Qwen3.5-9B")
