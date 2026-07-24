from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from pydantic import BaseModel


@dataclass(frozen=True)
class EmbeddingStats:
    created: int
    reused: int
    total: int


def text_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ModelClient:
    """Small Azure OpenAI client for embeddings and structured responses."""

    def __init__(
        self,
        embedding_deployment: str,
        chat_deployment: str,
        reasoning_effort: str = "high",
    ) -> None:
        self.embedding_deployment = embedding_deployment
        self.chat_deployment = chat_deployment
        self.reasoning_effort = reasoning_effort
        self._openai_client = None

    def _client(self):
        if self._openai_client is None:
            endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
            api_key = os.getenv("AZURE_OPENAI_API_KEY", "").strip()
            if not endpoint or not api_key:
                raise ValueError("Missing AZURE_OPENAI_ENDPOINT or AZURE_OPENAI_API_KEY.")

            from openai import OpenAI

            base_url = endpoint.rstrip("/")
            if not base_url.endswith("/openai/v1"):
                base_url = f"{base_url}/openai/v1"
            self._openai_client = OpenAI(
                base_url=f"{base_url}/",
                api_key=api_key,
            )
        return self._openai_client

    def embed_text(self, text: str) -> list[float]:
        if not self.embedding_deployment:
            raise ValueError(
                "Missing embedding deployment. Set AZURE_OPENAI_EMBEDDING_DEPLOYMENT "
                "or DEPLOYMENT_EMB_SMALL in .env."
            )
        response = self._client().embeddings.create(
            model=self.embedding_deployment,
            input=text,
        )
        return response.data[0].embedding

    def upload_input_file(self, path: str) -> tuple[str, str]:
        source = Path(path)
        if source.suffix.lower() == ".sas":
            uploaded_name = f"{source.stem}.txt"
            uploaded = self._client().files.create(
                file=(uploaded_name, source.read_bytes(), "text/plain"),
                purpose="assistants",
            )
        else:
            uploaded_name = source.name
            with source.open("rb") as file:
                uploaded = self._client().files.create(
                    file=file,
                    purpose="assistants",
                )
        return uploaded.id, uploaded_name

    def delete_input_file(self, file_id: str) -> None:
        self._client().files.delete(file_id)

    def parse_response(
        self,
        input_text: str,
        instructions: str,
        text_format: type[BaseModel],
        file_inputs: list[dict[str, Any]] | None = None,
        image_data_urls: list[str] | None = None,
        max_output_tokens: int = 1800,
    ) -> BaseModel:
        if not self.chat_deployment:
            raise ValueError(
                "Missing chat deployment. Set AZURE_OPENAI_CHAT_DEPLOYMENT, "
                "DEPLOYMENT_GPT54 or DEPLOYMENT_AZURE in .env."
            )
        content: list[dict[str, Any]] = list(file_inputs or [])
        content.append({"type": "input_text", "text": input_text})
        content.extend(
            {
                "type": "input_image",
                "image_url": data_url,
                "detail": "auto",
            }
            for data_url in image_data_urls or []
        )

        response = self._client().responses.parse(
            model=self.chat_deployment,
            instructions=instructions,
            input=[{"role": "user", "content": content}],
            reasoning={"effort": self.reasoning_effort},
            text_format=text_format,
            max_output_tokens=max_output_tokens,
            store=False,
        )
        if response.output_parsed is None:
            raise ValueError("Model did not return a structured response.")
        return response.output_parsed


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
