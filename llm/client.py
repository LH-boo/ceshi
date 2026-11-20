"""统一的 LLM 调用入口。

- 默认读取环境变量 OPENAI_API_KEY / OPENAI_BASE_URL / OPENAI_MODEL。
- 任何异常都会回退到调用方提供的兜底内容，保证 Demo 无模型也能完整演示。
"""
from __future__ import annotations

import json
import os
import re
from typing import Any

import requests

DEFAULT_BASE_URL = "https://api.openai.com/v1"
DEFAULT_MODEL = "gpt-4o-mini"


class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: int = 40,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.model = model or os.getenv("OPENAI_MODEL") or DEFAULT_MODEL
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def complete(
        self,
        prompt: str,
        system: str = "你是一名严谨的 B2B 海外营销顾问。",
        json_mode: bool = False,
        temperature: float = 0.6,
    ) -> str | None:
        """调用模型返回文本；未配置或调用失败时返回 None。"""
        if not self.configured:
            return None
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except Exception:
            return None

    def complete_json(self, prompt: str, system: str = "你是一名严谨的 B2B 海外营销顾问。") -> dict | None:
        text = self.complete(prompt, system=system, json_mode=True, temperature=0.4)
        return extract_json(text) if text else None


def extract_json(text: str) -> dict | None:
    """尽量从模型输出中解析 JSON 对象。"""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def build_client(api_key: str = "", base_url: str = "", model: str = "") -> LLMClient:
    return LLMClient(api_key=api_key.strip(), base_url=base_url.strip() or None, model=model.strip() or None)
