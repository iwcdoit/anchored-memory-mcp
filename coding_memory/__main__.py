"""Service entrypoint and local multi-process orchestrator for Coding Memory MCP."""

import argparse
from collections.abc import Callable
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
from time import monotonic, sleep
from urllib.request import ProxyHandler, build_opener

from .config import CFG, ROOT_DIR


def http_get(url: str, timeout: float = 3.0) -> bytes:
    with build_opener(ProxyHandler({})).open(url, timeout=timeout) as resp:
        return resp.read()


def tcp_ping(host: str, port: int, timeout: float = 3.0) -> None:
    with socket.create_connection((host, port), timeout=timeout):
        pass


def init_sample_notes(notes_dir: Path, config_dir: Path) -> None:
    flag_file = config_dir / ".samples-initialized"
    if os.environ.get("CMEM_INIT_SAMPLES", "1") != "1" or flag_file.exists():
        return
    sample_root = ROOT_DIR / "examples" / "notes"
    for md_file in sorted(sample_root.rglob("*.md")):
        target = notes_dir / md_file.relative_to(sample_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(md_file, target)
    flag_file.touch()


def run_memory_server(host: str, port: int) -> None:
    notes_dir, config_dir = CFG.notes_dir, CFG.config_dir
    notes_dir.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)
    init_sample_notes(notes_dir, config_dir)

    index_md = notes_dir / "index.md"
    if not index_md.exists():
        index_md.write_text(
            "# AI Coding 研发记忆库\n\n通过 MCP 检索与沉淀项目排障经验、架构约束与技术方案。\n",
            encoding="utf-8",
        )

    clean_env = {k: v for k, v in os.environ.items() if not k.startswith("BASIC_MEMORY_")}
    clean_env.update({
        "BASIC_MEMORY_CONFIG_DIR": str(config_dir),
        "BASIC_MEMORY_HOME": str(notes_dir),
        "BASIC_MEMORY_DATABASE_BACKEND": "sqlite",
        "BASIC_MEMORY_SEMANTIC_SEARCH_ENABLED": "true",
        "BASIC_MEMORY_DEFAULT_SEARCH_TYPE": "hybrid",
        "BASIC_MEMORY_SEMANTIC_EMBEDDING_PROVIDER": "litellm",
        "BASIC_MEMORY_SEMANTIC_EMBEDDING_MODEL": f"openai/{CFG.model_alias}",
        "BASIC_MEMORY_SEMANTIC_EMBEDDING_API_BASE": os.environ.get(
            "CMEM_EMBED_URL", f"http://localhost:{CFG.embed_port}/v1"
        ),
        "BASIC_MEMORY_SEMANTIC_EMBEDDING_API_KEY": "local-no-auth",
        "BASIC_MEMORY_SEMANTIC_EMBEDDING_DIMENSIONS": str(CFG.vector_dim),
        "BASIC_MEMORY_SEMANTIC_EMBEDDING_FORWARD_DIMENSIONS": "false",
        "BASIC_MEMORY_SEMANTIC_EMBEDDING_QUERY_PREFIX": CFG.query_instruction,
        "BASIC_MEMORY_SEMANTIC_MIN_SIMILARITY": CFG.similarity_threshold,
        "BASIC_MEMORY_AUTO_UPDATE": "false",
        "BASIC_MEMORY_CLOUD_PROMO_OPT_OUT": "true",
        "BASIC_MEMORY_LOGFIRE_ENABLED": "false",
        "BASIC_MEMORY_LOGFIRE_SEND_TO_LOGFIRE": "false",
        "FASTMCP_CHECK_FOR_UPDATES": "off",
        "LITELLM_LOCAL_MODEL_COST_MAP": "true",
    })
    bm_bin = Path(sys.executable).with_name("bm")
    os.execve(
        bm_bin,
        [str(bm_bin), "mcp", "--transport", "streamable-http", "--host", host, "--port", str(port), "--path", "/mcp"],
        clean_env,
    )


def run_embedding_server(host: str, port: int) -> None:
    cache_dir = CFG.cache_dir
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(cache_dir))
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os.execv(
        sys.executable,
        [sys.executable, "-m", "uvicorn", "coding_memory.encoder:app", "--host", host, "--port", str(port)],
    )


def run_docs_site(host: str, port: int) -> None:
    os.environ["CMEM_DOCS_DIR"] = str(CFG.notes_dir)
    os.execv(
        sys.executable,
        [
            sys.executable,
            "-m",
            "mkdocs",
            "serve",
            "--dev-addr",
            f"{host}:{port}",
            "--config-file",
            str(ROOT_DIR / "mkdocs.yml"),
        ],
    )


def _await_ready(proc: subprocess.Popen, label: str, probe: Callable[[], object], timeout: int) -> None:
    deadline = monotonic() + timeout
    while monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"Service '{label}' exited prematurely with code {proc.returncode}")
        try:
            probe()
            return
        except OSError:
            sleep(0.5)
    raise RuntimeError(f"Service '{label}' did not become ready within {timeout}s")


def _terminate_all(procs: list[subprocess.Popen]) -> None:
    for proc in reversed(procs):
        if proc.poll() is None:
            proc.terminate()
    for proc in reversed(procs):
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def run_all_local(mcp_port: int, embed_port: int, site_port: int, timeout: int) -> None:
    host = "localhost"
    child_env = os.environ | {
        "PYTHONUNBUFFERED": "1",
        "CMEM_EMBED_URL": f"http://{host}:{embed_port}/v1",
    }
    procs: list[subprocess.Popen] = []

    def spawn(role: str, port: int) -> subprocess.Popen:
        proc = subprocess.Popen(
            [sys.executable, "-m", "coding_memory", role, "--host", host, "--port", str(port)],
            cwd=ROOT_DIR,
            env=child_env,
        )
        procs.append(proc)
        return proc

    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt()))
    try:
        p_embed = spawn("embedding", embed_port)
        _await_ready(p_embed, "embedding", lambda: http_get(f"http://{host}:{embed_port}/healthz"), timeout)

        p_mem = spawn("memory", mcp_port)
        _await_ready(p_mem, "memory", lambda: tcp_ping(host, mcp_port), timeout)

        p_site = spawn("site", site_port)
        _await_ready(p_site, "site", lambda: http_get(f"http://{host}:{site_port}/"), timeout)

        print(f"[CodingMemory] MCP Endpoint : http://{host}:{mcp_port}/mcp", flush=True)
        print(f"[CodingMemory] Knowledge UI : http://{host}:{site_port}/", flush=True)
        while True:
            for name, proc in zip(("embedding", "memory", "site"), procs):
                if proc.poll() is not None:
                    raise RuntimeError(f"Process '{name}' stopped unexpectedly ({proc.returncode})")
            sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        _terminate_all(procs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Coding Memory MCP service runner")
    sub = parser.add_subparsers(dest="command", required=True)

    defaults = {"memory": CFG.mcp_port, "embedding": CFG.embed_port, "site": CFG.site_port}
    for role, default_port in defaults.items():
        p = sub.add_parser(role)
        p.add_argument("--host", default="localhost")
        p.add_argument("--port", type=int, default=default_port)

    p_local = sub.add_parser("local", help="Run all three services locally without Docker")
    p_local.add_argument("--mcp-port", type=int, default=CFG.mcp_port)
    p_local.add_argument("--embedding-port", type=int, default=CFG.embed_port)
    p_local.add_argument("--site-port", type=int, default=CFG.site_port)
    p_local.add_argument("--startup-timeout", type=int, default=300)

    p_probe = sub.add_parser("health", help="Container healthcheck helper")
    p_probe.add_argument("kind", choices=["http", "tcp"])
    p_probe.add_argument("target")
    p_probe.add_argument("port", nargs="?", type=int)

    args = parser.parse_args()
    if args.command == "memory":
        run_memory_server(args.host, args.port)
    elif args.command == "embedding":
        run_embedding_server(args.host, args.port)
    elif args.command == "site":
        run_docs_site(args.host, args.port)
    elif args.command == "local":
        run_all_local(args.mcp_port, args.embedding_port, args.site_port, args.startup_timeout)
    elif args.command == "health":
        if args.kind == "http":
            http_get(args.target)
        else:
            tcp_ping(args.target, int(args.port))


if __name__ == "__main__":
    main()
