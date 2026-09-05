from __future__ import annotations

import base64
import json
import mimetypes
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ModelConfig:
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    reasoning_model: str = "gpt-4.1-mini"
    vision_model: str = "gpt-4.1-mini"
    temperature: float = 0.2
    timeout_seconds: int = 180

    @property
    def enabled(self) -> bool:
        return bool(self.api_key.strip()) or "localhost" in self.base_url or "127.0.0.1" in self.base_url


class LLMError(RuntimeError):
    pass


class CompatibleLLM:
    """OpenAI Chat Completions 兼容层，可连接云端模型或本地 Ollama/Qwen。"""

    def __init__(self, config: ModelConfig):
        self.config = config
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMError("缺少 openai 依赖，请安装 requirements.txt。") from exc
        self._client = OpenAI(
            api_key=self.config.api_key or "local-model",
            base_url=self.config.base_url,
            timeout=self.config.timeout_seconds,
        )
        return self._client

    @staticmethod
    def _image_data_url(path: str | Path) -> str:
        path = Path(path)
        mime = mimetypes.guess_type(path.name)[0] or "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    def complete(
        self,
        system: str,
        prompt: str,
        *,
        model: str | None = None,
        images: list[tuple[str, str | Path]] | None = None,
        json_mode: bool = False,
        max_tokens: int = 8_000,
    ) -> str:
        client = self._get_client()
        content: str | list[dict[str, Any]]
        if images:
            parts: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
            for label, path in images:
                parts.append({"type": "text", "text": f"下面是{label}的整页图像："})
                parts.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": self._image_data_url(path), "detail": "high"},
                    }
                )
            content = parts
        else:
            content = prompt

        kwargs: dict[str, Any] = {
            "model": model or self.config.reasoning_model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": content},
            ],
            "temperature": self.config.temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        try:
            response = client.chat.completions.create(**kwargs)
        except Exception as first_error:
            if json_mode:
                kwargs.pop("response_format", None)
                try:
                    response = client.chat.completions.create(**kwargs)
                except Exception as second_error:
                    raise LLMError(f"模型调用失败：{second_error}") from second_error
            else:
                raise LLMError(f"模型调用失败：{first_error}") from first_error
        text = response.choices[0].message.content
        if not text:
            raise LLMError("模型返回了空内容。")
        return text


def parse_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        payload = json.loads(cleaned)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start >= 0 and end > start:
        try:
            payload = json.loads(cleaned[start : end + 1])
            if isinstance(payload, dict):
                return payload
        except json.JSONDecodeError as exc:
            raise LLMError("模型输出不是可解析的 JSON，请重试或换用更强的模型。") from exc
    raise LLMError("模型输出不是 JSON 对象。")

