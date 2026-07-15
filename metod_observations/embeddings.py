from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class EmbeddingStats:
    created: int
    reused: int
    total: int


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ModelClient:
    """Small provider wrapper; avoids bringing a framework into the MVP."""

    def __init__(
        self,
        embedding_provider: str = "azure",
        chat_provider: str = "azure",
        embedding_deployment: str = "text-embedding-3-small",
        chat_deployment: str = "gpt-4o-mini",
    ) -> None:
        self.embedding_provider = embedding_provider
        self.chat_provider = chat_provider
        self.embedding_deployment = embedding_deployment
        self.chat_deployment = chat_deployment
        self._azure_client = None
        self._databricks_client = None

    def _azure(self):
        if self._azure_client is None:
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
            api_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21").strip()
            if not endpoint or not api_key:
                raise ValueError("Missing AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY.")
            from openai import AzureOpenAI

            self._azure_client = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=api_key,
                api_version=api_version,
            )
        return self._azure_client

    def _databricks(self):
        if self._databricks_client is None:
            import mlflow.deployments

            self._databricks_client = mlflow.deployments.get_deploy_client("databricks")
        return self._databricks_client

    def embed_text(self, text: str) -> list[float]:
        if self.embedding_provider == "azure":
            response = self._azure().embeddings.create(
                model=self.embedding_deployment,
                input=text,
            )
            return response.data[0].embedding

        if self.embedding_provider == "databricks":
            response = self._databricks().predict(
                endpoint=self.embedding_deployment,
                inputs={"input": [text]},
            )
            return response["data"][0]["embedding"]

        raise ValueError(f"Unsupported embedding provider: {self.embedding_provider}")

    def chat_json(
        self,
        prompt: str,
        image_data_urls: list[str] | None = None,
        max_tokens: int = 1800,
        temperature: float = 0.1,
    ) -> str:
        user_content: str | list[dict[str, Any]]
        if image_data_urls:
            user_content = [{"type": "text", "text": prompt}]
            user_content.extend(
                {"type": "image_url", "image_url": {"url": data_url}}
                for data_url in image_data_urls
            )
        else:
            user_content = prompt

        messages = [
            {
                "role": "system",
                "content": "Eres un validador metodologico. Responde solo JSON valido.",
            },
            {"role": "user", "content": user_content},
        ]
        if self.chat_provider == "azure":
            response = self._azure().chat.completions.create(
                model=self.chat_deployment,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content or ""

        if self.chat_provider == "databricks":
            response = self._databricks().predict(
                endpoint=self.chat_deployment,
                inputs={
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            return response["choices"][0]["message"]["content"]

        raise ValueError(f"Unsupported chat provider: {self.chat_provider}")


def embed_rows_with_cache(
    rows: list[dict[str, Any]],
    existing_rows: list[dict[str, Any]],
    embed_fn: Callable[[str], list[float]],
    embedding_model: str,
    id_key: str = "id",
    text_key: str = "text",
) -> tuple[list[dict[str, Any]], EmbeddingStats]:
    existing_by_id = {
        row[id_key]: row
        for row in existing_rows
        if row.get(id_key) and row.get("text_sha256") and row.get("embedding")
    }
    output = []
    created = 0
    reused = 0
    for row in rows:
        row_id = row[id_key]
        text = row[text_key]
        sha = text_hash(text)
        cached = existing_by_id.get(row_id)
        if (
            cached
            and cached.get("text_sha256") == sha
            and cached.get("embedding_model") == embedding_model
        ):
            output.append(cached)
            reused += 1
            continue
        output.append(
            {
                **row,
                "text_sha256": sha,
                "embedding_model": embedding_model,
                "embedding": embed_fn(text),
            }
        )
        created += 1
    return output, EmbeddingStats(created=created, reused=reused, total=len(output))

