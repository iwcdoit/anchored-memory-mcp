"""Code-anchor drift detector and executable Playbook parser for living memory notes."""

import argparse
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
import subprocess
from typing import Literal

from .config import CFG, ROOT_DIR

DriftLevel = Literal["CLEAN", "MODIFIED_SAFE", "DRIFTED", "UNANCHORED"]

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_PLAYBOOK_SECTION_RE = re.compile(r"^##\s+Playbook\s*\n(.*?)(?=^##\s+|\Z)", re.DOTALL | re.MULTILINE)
_PLAYBOOK_ITEM_RE = re.compile(r"^\s*-\s*\[(probe|verify)\]\s*(.+)$", re.MULTILINE)


@dataclass
class NoteContract:
    file_path: str
    title: str = ""
    repository: str = ""
    memory_type: str = ""
    status: str = ""
    commit: str = ""
    code_paths: list[str] = field(default_factory=list)
    code_symbols: list[str] = field(default_factory=list)
    probes: list[str] = field(default_factory=list)
    verifications: list[str] = field(default_factory=list)


@dataclass
class DriftReport:
    note_path: str
    title: str
    repository: str
    status: str
    drift_level: DriftLevel
    recommended_status: str
    missing_paths: list[str] = field(default_factory=list)
    missing_symbols: list[str] = field(default_factory=list)
    modified_paths: list[str] = field(default_factory=list)
    probes: list[str] = field(default_factory=list)
    verifications: list[str] = field(default_factory=list)


def _parse_yaml_list(raw: str) -> list[str]:
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        items = raw[1:-1].split(",")
        return [item.strip().strip("'\"") for item in items if item.strip().strip("'\"")]
    return [raw.strip("'\"")] if raw else []


def parse_note_contract(md_path: Path) -> NoteContract:
    text = md_path.read_text(encoding="utf-8")
    contract = NoteContract(file_path=str(md_path))

    fm_match = _FRONTMATTER_RE.match(text)
    if fm_match:
        lines = fm_match.group(1).splitlines()
        current_list_key: str | None = None
        for line in lines:
            if line.strip().startswith("- ") and current_list_key in {"code_paths", "code_symbols"}:
                val = line.strip()[2:].strip().strip("'\"")
                if val:
                    getattr(contract, current_list_key).append(val)
                continue
            if ":" not in line:
                continue
            key, val = line.split(":", 1)
            key, val = key.strip(), val.strip()
            current_list_key = None
            if key in {"title", "repository", "memory_type", "status", "commit"}:
                setattr(contract, key, val.strip("'\""))
            elif key in {"code_paths", "code_symbols"}:
                if val:
                    setattr(contract, key, _parse_yaml_list(val))
                else:
                    current_list_key = key

    pb_match = _PLAYBOOK_SECTION_RE.search(text)
    if pb_match:
        for kind, cmd in _PLAYBOOK_ITEM_RE.findall(pb_match.group(1)):
            if kind == "probe":
                contract.probes.append(cmd.strip())
            elif kind == "verify":
                contract.verifications.append(cmd.strip())

    return contract


def _git_changed_files(repo_dir: Path, base_commit: str, rel_paths: list[str]) -> list[str] | None:
    if not base_commit or not (repo_dir / ".git").exists():
        return None
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_dir), "diff", "--name-only", f"{base_commit}..HEAD", "--", *rel_paths],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    except (subprocess.SubprocessError, OSError):
        return None


def _symbol_exists_in_files(repo_dir: Path, rel_paths: list[str], symbol_expr: str) -> bool:
    tokens = [tok.strip() for tok in symbol_expr.split("#") if tok.strip()]
    existing_files = [repo_dir / p for p in rel_paths if (repo_dir / p).is_file()]
    if not existing_files:
        return False
    for file_path in existing_files:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        if all(tok in content for tok in tokens):
            return True
    return False


def evaluate_note_drift(contract: NoteContract, repo_dir: Path | None = None) -> DriftReport:
    if not contract.code_paths and not contract.code_symbols:
        return DriftReport(
            note_path=contract.file_path,
            title=contract.title,
            repository=contract.repository,
            status=contract.status,
            drift_level="UNANCHORED",
            recommended_status=contract.status or "draft",
            probes=contract.probes,
            verifications=contract.verifications,
        )

    if repo_dir is None or not repo_dir.exists():
        return DriftReport(
            note_path=contract.file_path,
            title=contract.title,
            repository=contract.repository,
            status=contract.status,
            drift_level="CLEAN",
            recommended_status=contract.status or "verified",
            probes=contract.probes,
            verifications=contract.verifications,
        )

    missing_paths = [p for p in contract.code_paths if not (repo_dir / p).is_file()]
    missing_symbols = [
        sym for sym in contract.code_symbols if not _symbol_exists_in_files(repo_dir, contract.code_paths, sym)
    ]
    git_modified = _git_changed_files(repo_dir, contract.commit, contract.code_paths) or []

    if missing_paths or missing_symbols:
        level: DriftLevel = "DRIFTED"
        rec_status = "stale"
    elif git_modified:
        level = "MODIFIED_SAFE"
        rec_status = contract.status or "verified"
    else:
        level = "CLEAN"
        rec_status = contract.status or "verified"

    return DriftReport(
        note_path=contract.file_path,
        title=contract.title,
        repository=contract.repository,
        status=contract.status,
        drift_level=level,
        recommended_status=rec_status,
        missing_paths=missing_paths,
        missing_symbols=missing_symbols,
        modified_paths=git_modified,
        probes=contract.probes,
        verifications=contract.verifications,
    )


def scan_notes_contracts(notes_root: Path, repo_dir: Path | None = None) -> list[DriftReport]:
    reports: list[DriftReport] = []
    for md_file in sorted(notes_root.rglob("*.md")):
        if md_file.name == "index.md":
            continue
        contract = parse_note_contract(md_file)
        reports.append(evaluate_note_drift(contract, repo_dir))
    return reports


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--notes-dir",
        type=Path,
        default=ROOT_DIR / "examples" / "notes",
        help="Root directory of Markdown memory notes",
    )
    parser.add_argument(
        "--repo-dir",
        type=Path,
        default=None,
        help="Optional target business Git repository path to verify code_paths and code_symbols against",
    )
    parser.add_argument("--require-contract", action="store_true", help="Fail if any note lacks anchors or playbook")
    args = parser.parse_args()

    notes_root = args.notes_dir if args.notes_dir.exists() else CFG.notes_dir
    reports = scan_notes_contracts(notes_root, args.repo_dir)

    for rep in reports:
        if args.require_contract and (rep.drift_level == "UNANCHORED" or not (rep.probes or rep.verifications)):
            raise SystemExit(f"[FAIL] Note '{rep.title}' ({rep.note_path}) is missing code anchors or Playbook")

    print(json.dumps([asdict(r) for r in reports], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
