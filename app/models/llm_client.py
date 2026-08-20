import json
import re

import httpx

from app.config import settings
from app.utils.prompts import SYSTEM_JSON_SUFFIX


class LLMClient:
    def __init__(
        self,
        provider: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
    ):
        self.provider = (provider or settings.llm_provider).lower()
        self.api_key = api_key or settings.llm_api_key
        self.model = model or settings.llm_model
        self.base_url = base_url or settings.ollama_base_url

    async def call_text(self, prompt: str) -> str:
        if self.provider == "ollama":
            return await self._call_ollama(prompt)
        if self.provider == "gemini":
            return await self._call_gemini(prompt)
        return await self._call_openrouter(prompt)

    async def call_json(self, prompt: str) -> dict:
        text = await self.call_text(prompt + SYSTEM_JSON_SUFFIX)
        return self._parse_json(text)

    async def _call_openrouter(self, prompt: str) -> str:
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        return data["choices"][0]["message"]["content"]

    async def _call_ollama(self, prompt: str) -> str:
        url = f"{self.base_url.rstrip('/')}/api/generate"
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        return data["response"]

    async def _call_gemini(self, prompt: str) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    @staticmethod
    def _parse_json(text: str) -> dict:
        text = text.strip()
        fence_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1).strip()
        else:
            object_match = re.search(r"\{.*\}", text, re.DOTALL)
            if object_match:
                text = object_match.group(0)

        try:
            return json.loads(text, strict=False)
        except json.JSONDecodeError:
            cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
            return json.loads(cleaned, strict=False)
