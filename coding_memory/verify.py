"""End-to-end verification suite for MCP Streamable HTTP, hybrid retrieval, and MkDocs publishing."""

import argparse
import json
from pathlib import PurePosixPath
from time import monotonic, sleep
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import ProxyHandler, Request, build_opener
from uuid import uuid4

from .__main__ import http_get
from .config import ROOT_DIR
from .drift import scan_notes_contracts


class McpStreamClient:
    """Minimal JSON-RPC client for MCP Streamable HTTP transport."""

    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint
        self._opener = build_opener(ProxyHandler({}))
        self._session_id: str | None = None
        self._protocol_version = "2025-03-26"
        self._seq = 0

    def _headers(self) -> dict[str, str]:
        hdrs = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
            "MCP-Protocol-Version": self._protocol_version,
        }
        if self._session_id:
            hdrs["Mcp-Session-Id"] = self._session_id
        return hdrs

    def request(self, method: str, params: dict | None = None, *, is_notification: bool = False) -> dict:
        self._seq += 1
        payload: dict = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        if not is_notification:
            payload["id"] = self._seq

        req = Request(self.endpoint, data=json.dumps(payload).encode("utf-8"), headers=self._headers())
        with self._opener.open(req, timeout=15) as resp:
            self._session_id = resp.headers.get("Mcp-Session-Id") or self._session_id
            if is_notification:
                return {}
            if resp.headers.get_content_type() == "text/event-stream":
                for raw_line in resp:
                    if raw_line.startswith(b"data:"):
                        envelope = json.loads(raw_line[5:])
                        if envelope.get("id") == self._seq:
                            break
                else:
                    raise RuntimeError(f"Empty SSE stream for {method}")
            else:
                envelope = json.load(resp)

        if "error" in envelope:
            raise RuntimeError(f"RPC error on {method}: {envelope['error']}")
        return envelope["result"]

    def __enter__(self) -> "McpStreamClient":
        init_res = self.request(
            "initialize",
            {
                "protocolVersion": self._protocol_version,
                "capabilities": {},
                "clientInfo": {"name": "anchored-memory-mcp-verifier", "version": "0.1.0"},
            },
        )
        self._protocol_version = init_res["protocolVersion"]
        self.request("notifications/initialized", is_notification=True)
        return self

    def __exit__(self, *_exc) -> None:
        if self._session_id:
            req = Request(self.endpoint, headers=self._headers(), method="DELETE")
            try:
                with self._opener.open(req, timeout=5):
                    pass
            except OSError:
                pass

    def call_tool(self, tool_name: str, **kwargs):
        res = self.request("tools/call", {"name": tool_name, "arguments": kwargs})
        if res.get("isError"):
            raise RuntimeError(f"Tool {tool_name} returned error: {res.get('content')}")
        if "structuredContent" in res:
            data = res["structuredContent"]
            return data.get("result", data) if isinstance(data, dict) else data
        text_chunk = next((item["text"] for item in res["content"] if item["type"] == "text"), "")
        try:
            return json.loads(text_chunk)
        except ValueError:
            return text_chunk


def verify_hybrid_retrieval(client: McpStreamClient) -> None:
    test_cases = {
        "text": ("ERR_ACCOUNT_LOCK_TIMEOUT", "热点账户行锁超时排查"),
        "vector": ("高并发下单个归集账户行锁排队阻塞连接池怎么拆分优化？", "热点账户行锁超时排查"),
        "hybrid": ("热点账户 行锁超时 Hash 分片归集", "热点账户行锁超时排查"),
    }
    for mode, (query_text, expected_title) in test_cases.items():
        deadline = monotonic() + 30
        while True:
            res = client.call_tool(
                "search_notes",
                project="main",
                query=query_text,
                search_type=mode,
                metadata_filters={"repository": "pay-ledger"},
                output_format="json",
            )
            hits = res.get("results", []) if isinstance(res, dict) else []
            if any(item.get("title") == expected_title for item in hits):
                print(f"[PASS] search_notes ({mode}): matched '{expected_title}'")
                break
            if monotonic() >= deadline:
                raise RuntimeError(f"Retrieval check timed out in mode={mode} for query={query_text!r}")
            sleep(1.0)


def verify_write_and_publish(client: McpStreamClient, site_url: str) -> None:
    note_title = f"Verify Note {uuid4().hex[:8]}"
    token = f"verify-token-{uuid4().hex}"
    folder = "projects/pay-ledger/verify"
    identifier = note_title
    try:
        created = client.call_tool(
            "write_note",
            project="main",
            title=note_title,
            content=f"# {note_title}\n\n{token}\n",
            directory=folder,
            metadata={"repository": "pay-ledger", "memory_type": "verify"},
            output_format="json",
        )
        if not isinstance(created, dict) or not created.get("permalink"):
            raise RuntimeError("write_note did not return a valid permalink")
        identifier = created["permalink"]
        read_back = client.call_tool("read_note", project="main", identifier=identifier)
        if token not in json.dumps(read_back, ensure_ascii=False):
            raise RuntimeError("read_note content did not match written token")
        print("[PASS] write_note -> read_note roundtrip")

        rel_path = PurePosixPath(created["file_path"]).with_suffix("").as_posix()
        page_url = f"{site_url.rstrip('/')}/{quote(rel_path)}/"
        deadline = monotonic() + 30
        while True:
            try:
                if token.encode("utf-8") in http_get(page_url):
                    print("[PASS] MkDocs live page rendering verified")
                    break
            except HTTPError as err:
                if err.code != 404:
                    raise
            if monotonic() >= deadline:
                raise RuntimeError("MkDocs failed to render newly created note within 30s")
            sleep(0.5)
    finally:
        client.call_tool("delete_note", project="main", identifier=identifier, output_format="json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mcp-url", default="http://localhost:8000/mcp")
    parser.add_argument("--site-url", default="http://localhost:8088")
    parser.add_argument("--write-check", action="store_true", help="Verify write/read/publish lifecycle")
    args = parser.parse_args()

    reports = scan_notes_contracts(ROOT_DIR / "examples" / "notes")
    for rep in reports:
        if rep.drift_level == "UNANCHORED" or not (rep.probes or rep.verifications):
            raise SystemExit(f"Missing Code Anchors or Playbook in sample note: {rep.title}")
    print(f"[PASS] Code Anchors & Playbook contract check ({len(reports)} notes)")

    with McpStreamClient(args.mcp_url) as client:
        available = {t["name"] for t in client.request("tools/list")["tools"]}
        required = {"search_notes", "read_note", "write_note", "delete_note"}
        if not (required <= available):
            raise SystemExit(f"Missing required MCP tools: {required - available}")
        print("[PASS] MCP Streamable HTTP handshake & tool discovery")
        verify_hybrid_retrieval(client)
        if args.write_check:
            verify_write_and_publish(client, args.site_url)


if __name__ == "__main__":
    main()
