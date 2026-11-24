"""Core configuration and runtime paths for Coding Memory MCP."""

from dataclasses import dataclass
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class RuntimeConfig:
    model_repo: str = "BAAI/bge-small-zh-v1.5"
    model_revision: str = "7999e1d3359715c523056ef9478215996d62a620"
    model_alias: str = "bge-small-zh-v1.5"
    vector_dim: int = 512
    query_instruction: str = "为这个句子生成表示以用于检索相关文章："
    similarity_threshold: str = "0.45"
    mcp_port: int = 8000
    embed_port: int = 8001
    site_port: int = 8088

    @property
    def data_root(self) -> Path:
        raw = os.environ.get("CMEM_DATA_DIR", str(ROOT_DIR / "var"))
        return Path(raw).expanduser().resolve()

    @property
    def notes_dir(self) -> Path:
        return self.data_root / "notes"

    @property
    def config_dir(self) -> Path:
        return self.data_root / "config"

    @property
    def cache_dir(self) -> Path:
        return self.data_root / "cache" / "huggingface"


CFG = RuntimeConfig()
