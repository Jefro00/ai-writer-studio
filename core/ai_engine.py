"""Provider-neutral AI engine with bounded retries and fallback."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Callable

import requests


class AIEngine:
    def __init__(self, gemini_key: str = "", openrouter_key: str = "", gemini_model: str = "gemini-2.5-flash", openrouter_model: str = "openrouter/free", timeout: tuple[int, int] = (15, 120), retry_delay: float = 1.0):
        self.gemini_key = gemini_key
        self.openrouter_key = openrouter_key
        self.gemini_model = gemini_model
        self.openrouter_model = openrouter_model
        self.timeout = timeout
        self.retry_delay = retry_delay
        self.logs: list[dict] = []
        self.current_provider: str | None = None
        self._gemini_client = None

    @property
    def providers(self) -> list[str]:
        return (["Gemini"] if self.gemini_key else []) + (["OpenRouter"] if self.openrouter_key else [])

    def _ask_gemini(self, prompt: str) -> str:
        if self._gemini_client is None:
            try:
                from google import genai
            except ImportError as exc:
                raise RuntimeError("Установите пакет google-genai для Gemini") from exc
            self._gemini_client = genai.Client(api_key=self.gemini_key)
        response = self._gemini_client.models.generate_content(model=self.gemini_model, contents=prompt)
        text = getattr(response, "text", None)
        if not text or not text.strip():
            raise RuntimeError("Gemini вернул пустой ответ")
        return text.strip()

    def _ask_openrouter(self, prompt: str) -> str:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {self.openrouter_key}", "Content-Type": "application/json", "X-Title": "AI Writer Studio"},
            json={"model": self.openrouter_model,
                  "messages": [{"role": "system", "content": "You are a careful research and editorial assistant. Follow the user task and distinguish evidence from inference."}, {"role": "user", "content": prompt}],
                  "temperature": 0.35},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()
        choices = data.get("choices") or []
        content = (choices[0].get("message") or {}).get("content", "") if choices else ""
        if isinstance(content, list):
            content = "\n".join(part.get("text", "") for part in content if isinstance(part, dict))
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("OpenRouter вернул пустой ответ")
        return content.strip()

    def ask(self, prompt: str, agent_name: str = "AI Agent") -> str:
        if not self.providers:
            raise RuntimeError("Не настроен ни один AI API. Добавьте Gemini или OpenRouter key в Secrets.")
        methods: dict[str, Callable[[str], str]] = {"Gemini": self._ask_gemini, "OpenRouter": self._ask_openrouter}
        errors: list[str] = []
        for provider in self.providers:
            for attempt in range(2):
                started = datetime.now(timezone.utc).isoformat()
                try:
                    result = methods[provider](prompt)
                    self.current_provider = provider
                    self.logs.append({"agent": agent_name, "provider": provider, "status": "success", "time": started})
                    return result
                except Exception as exc:  # provider failures must not prevent fallback
                    errors.append(f"{provider}: {exc}")
                    self.logs.append({"agent": agent_name, "provider": provider, "status": "failed", "error": str(exc)[:250], "time": started})
                    if attempt == 0 and self.retry_delay:
                        time.sleep(self.retry_delay)
        raise RuntimeError("Все AI-провайдеры завершились ошибкой:\n" + "\n".join(errors))
