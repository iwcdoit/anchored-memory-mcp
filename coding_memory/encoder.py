"""Local BGE Chinese embedding service with OpenAI-compatible /v1/embeddings API."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import os
from pathlib import Path
from threading import Lock
from typing import Annotated, Literal

from fastapi import FastAPI, HTTPException, Request
from huggingface_hub import snapshot_download
from pydantic import BaseModel, Field, StringConstraints
import torch
from transformers import AutoModel, AutoTokenizer

from .config import CFG

NonEmptyText = Annotated[str, StringConstraints(min_length=1, max_length=32_768)]
TextBatch = Annotated[list[NonEmptyText], Field(min_length=1, max_length=32)]


class EmbedPayload(BaseModel):
    model: str = CFG.model_alias
    input: NonEmptyText | TextBatch
    encoding_format: Literal["float"] = "float"
    dimensions: Literal[512] | None = None


class BgeEmbeddingEngine:
    """Thread-safe wrapper around BAAI/bge-small-zh-v1.5 with CLS pooling and L2 normalization."""

    def __init__(self, model_dir: Path) -> None:
        threads = int(os.environ.get("CMEM_THREADS", "2"))
        torch.set_num_threads(threads)
        self._tokenizer = AutoTokenizer.from_pretrained(
            model_dir, trust_remote_code=False, local_files_only=True
        )
        self._model = AutoModel.from_pretrained(
            model_dir, trust_remote_code=False, local_files_only=True, use_safetensors=True
        ).eval()
        if self._model.config.hidden_size != CFG.vector_dim:
            raise ValueError(f"Model hidden_size mismatch: expected {CFG.vector_dim}")
        self._lock = Lock()

    def embed_texts(self, texts: list[str]) -> tuple[list[list[float]], int]:
        with self._lock, torch.inference_mode():
            encoded = self._tokenizer(
                texts, padding=True, truncation=True, max_length=512, return_tensors="pt"
            )
            hidden_state = self._model(**encoded).last_hidden_state
            normalized = torch.nn.functional.normalize(hidden_state[:, 0], p=2, dim=1)
            token_count = int(encoded["attention_mask"].sum().item())
            return normalized.tolist(), token_count


def _resolve_model_path() -> Path:
    override = os.environ.get("CMEM_MODEL_PATH")
    if override:
        return Path(override).expanduser().resolve()
    downloaded = snapshot_download(
        CFG.model_repo,
        revision=CFG.model_revision,
        allow_patterns=[
            "config.json",
            "model.safetensors",
            "tokenizer.json",
            "tokenizer_config.json",
            "special_tokens_map.json",
            "vocab.txt",
        ],
        max_workers=2,
    )
    return Path(downloaded)


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.engine = BgeEmbeddingEngine(_resolve_model_path())
    yield


app = FastAPI(title="Coding Memory Chinese Embedding Service", lifespan=_lifespan)


@app.get("/healthz")
def healthz() -> dict[str, str | int]:
    return {"status": "ok", "model": CFG.model_alias, "dimensions": CFG.vector_dim}


@app.get("/v1/models")
def list_models() -> dict:
    return {
        "object": "list",
        "data": [{"id": CFG.model_alias, "object": "model", "owned_by": "BAAI"}],
    }


@app.post("/v1/embeddings")
def create_embeddings(payload: EmbedPayload, request: Request) -> dict:
    if payload.model not in {CFG.model_alias, CFG.model_repo}:
        raise HTTPException(status_code=404, detail=f"Unsupported model: {payload.model}")
    batch = [payload.input] if isinstance(payload.input, str) else payload.input
    vectors, total_tokens = request.app.state.engine.embed_texts(batch)
    return {
        "object": "list",
        "data": [
            {"object": "embedding", "index": idx, "embedding": vec}
            for idx, vec in enumerate(vectors)
        ],
        "model": CFG.model_alias,
        "usage": {"prompt_tokens": total_tokens, "total_tokens": total_tokens},
    }
