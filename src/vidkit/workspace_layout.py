"""Copy-only workspace layout migration with checksum verification."""

from __future__ import annotations

import json
import shutil
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .storage import Workspace, sha256_file


def destination(workspace: Workspace, job: dict[str, Any], source: Path) -> Path:
    root = workspace.job_root(job["id"])
    parts = source.relative_to(root).parts
    head, tail = parts[0], Path(*parts[1:])
    shared = {"sources": "shared/sources", "assets": "shared/assets",
              "audio-assets": "shared/sounds", "checkpoints": "history/checkpoints"}
    if head in shared:
        return root / shared[head] / tail
    if head in {"previews", "exports"}:
        matches = [lang for lang in job["languages"] if f".{lang}." in source.name]
        return root / (matches[0] if len(matches) == 1 else "shared") / head / tail
    if head in job["languages"] and len(parts) > 1:
        mapping = {"scripts": "writing/scripts", "briefs": "writing/briefs",
                   "audio": "audio", "transcripts": "audio/transcripts",
                   "storyboard": "edit/storyboard", "subtitles": "edit/subtitles",
                   "visuals": "edit/visuals", "qa": "review/qa",
                   "approvals": "review/approvals", "feedback": "review/feedback"}
        category = parts[1]
        return root / head / mapping.get(category, "review/misc/" + category) / Path(*parts[2:])
    return root / "shared/misc" / Path(*parts)


def snapshots(workspace: Workspace, job_id: str) -> list[tuple[Path, str]]:
    root = workspace.job_root(job_id)
    result = []
    for manifest in root.glob("checkpoints/*/r*/manifest.json"):
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        for entry in payload["files"]:
            result.append((manifest.parent / "files" / entry["path"], entry["sha256"]))
    return result


def audit(workspace: Workspace, *, hashes: bool = False) -> dict[str, Any]:
    jobs = workspace.list_jobs()
    report: dict[str, Any] = {"jobs": len(jobs), "legacyJobs": 0,
                              "artifacts": 0, "checkpointEntries": 0,
                              "problems": [], "manual": []}
    for job in jobs:
        if int(job["storage_layout_version"]) < 2:
            report["legacyJobs"] += 1
        for artifact in workspace.list_artifacts(job["id"]):
            report["artifacts"] += 1
            path = workspace.resolve_path(artifact)
            if not path.is_file() or (hashes and sha256_file(path) != artifact["sha256"]):
                report["problems"].append(f"artifact {artifact['id']}: {artifact['path']}")
        for source, checksum in snapshots(workspace, job["id"]):
            report["checkpointEntries"] += 1
            if not source.is_file() or (hashes and sha256_file(source) != checksum):
                report["problems"].append(f"checkpoint: {source}")
            if int(job["storage_layout_version"]) >= 2:
                blob = workspace.objects_root / checksum[:2] / checksum
                if not blob.is_file() or (hashes and sha256_file(blob) != checksum):
                    report["problems"].append(f"checkpoint blob: {blob}")
        for manifest in workspace.job_root(job["id"]).glob("history/checkpoints/*/r*/manifest.json"):
            payload = json.loads(manifest.read_text(encoding="utf-8"))
            if (workspace.job_root(job["id"]) / "checkpoints" / payload["language"] /
                    f"r{payload['revision']}" / "manifest.json").is_file():
                continue  # Already counted through the retained legacy manifest.
            for entry in payload["files"]:
                report["checkpointEntries"] += 1
                checksum = entry["sha256"]
                blob = workspace.objects_root / checksum[:2] / checksum
                if not blob.is_file() or (hashes and sha256_file(blob) != checksum):
                    report["problems"].append(f"checkpoint blob: {blob}")
    inventory = workspace.workbench_root / "migration-inventory.json"
    if inventory.is_file():
        manual = json.loads(inventory.read_text(encoding="utf-8"))
        report["workbenchFiles"] = len(manual)
        for entry in manual:
            path = workspace.workspace_root / entry["target"]
            if not path.is_file() or (hashes and sha256_file(path) != entry["sha256"]):
                report["problems"].append(f"workbench: {path}")
    report["manual"] = [item.name for item in workspace.workspace_root.iterdir()
                        if item.name not in {"workspace.sqlite3", "workspace.sqlite3-wal",
                                             "workspace.sqlite3-shm", "videos", "cache", "library",
                                             "objects", "workbench", "history"}]
    return report


def copy_verified(source: Path, target: Path, checksum: str) -> None:
    if target.is_file():
        if sha256_file(target) != checksum:
            raise ValueError(f"Migration target conflicts: {target}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".migration-tmp")
    shutil.copy2(source, temporary)
    if sha256_file(temporary) != checksum:
        raise ValueError(f"Migration copy failed verification: {source}")
    temporary.replace(target)


def _manual_files(workspace: Workspace) -> list[tuple[Path, Path, str]]:
    root = workspace.workspace_root
    recognized = {"embeddinggemma-prep": "e5d0a1e52146"}
    astra_id = "e5fb0399b313"
    result = []
    for source in root.iterdir():
        if source.name in {"workspace.sqlite3", "workspace.sqlite3-wal", "workspace.sqlite3-shm",
                           "videos", "cache", "library", "objects", "workbench", "history"}:
            continue
        files = source.rglob("*") if source.is_dir() else [source]
        for path in files:
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            if source.name in recognized:
                target = workspace.workdir(recognized[source.name]) / relative
                reason = "identified-video"
            elif source.name.endswith("astra_vi.py"):
                target = workspace.workdir(astra_id) / "scripts" / path.name
                reason = "identified-video"
            else:
                target = workspace.workbench_root / "inbox" / relative
                reason = "unassigned"
            result.append((path, target, reason))
    cache = workspace.cache_root
    if cache.is_dir():
        for source in cache.iterdir():
            if source.name in {"jobs", "library"}:
                continue
            files = source.rglob("*") if source.is_dir() else [source]
            for path in files:
                if path.is_file():
                    relative = path.relative_to(cache)
                    result.append((path, workspace.workbench_root / "inbox/cache" / relative,
                                   "unassigned-cache"))
    return result


def migrate(workspace: Workspace, *, apply: bool = False) -> dict[str, Any]:
    report = audit(workspace, hashes=apply)
    if report["problems"]:
        raise ValueError("Workspace audit failed: " + "; ".join(report["problems"][:10]))
    if not apply:
        return {**report, "mode": "dry-run"}
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    backup = workspace.workspace_root / "history/migrations" / stamp / "workspace.sqlite3"
    backup.parent.mkdir(parents=True, exist_ok=True)
    with workspace.connect() as source, closing(sqlite3.connect(backup)) as target:
        source.backup(target)
    migrated = {}
    for job in workspace.list_jobs():
        if int(job["storage_layout_version"]) >= 2:
            continue
        root = workspace.job_root(job["id"])
        ordinary = [p for p in root.rglob("*") if p.is_file()
                    and "checkpoints" not in p.relative_to(root).parts
                    and "history" not in p.relative_to(root).parts
                    and p.relative_to(root).parts[0] != "shared"
                    and not (len(p.relative_to(root).parts) > 1
                             and p.relative_to(root).parts[0] in job["languages"]
                             and p.relative_to(root).parts[1] in {"writing", "edit", "review", "previews", "exports"})
                    and p.name != "project.json"]
        manifests = list(root.glob("checkpoints/*/r*/manifest.json"))
        copies = [(p, destination(workspace, job, p), sha256_file(p)) for p in [*ordinary, *manifests]]
        old_artifacts = {a["path"]: a for a in workspace.list_artifacts(job["id"])}
        for source, target, checksum in copies:
            old = source.relative_to(workspace.workspace_root).as_posix()
            if old in old_artifacts and old_artifacts[old]["sha256"] != checksum:
                raise ValueError(f"Artifact changed: {source}")
            if target.is_file() and sha256_file(target) != checksum:
                raise ValueError(f"Migration target conflicts: {target}")
        entries = snapshots(workspace, job["id"])
        for source, checksum in entries:
            if not source.is_file() or sha256_file(source) != checksum:
                raise ValueError(f"Checkpoint content missing or changed: {source}")
        for source, target, checksum in copies:
            copy_verified(source, target, checksum)
        for source, checksum in entries:
            copy_verified(source, workspace.objects_root / checksum[:2] / checksum, checksum)
        project = root / "project.json"
        if project.is_file():
            copy_verified(project, root / "history/migration/project.v1.json", sha256_file(project))
        with workspace.connect() as conn:
            for source, target, _ in copies:
                old = source.relative_to(workspace.workspace_root).as_posix()
                new = target.relative_to(workspace.workspace_root).as_posix()
                conn.execute("INSERT OR REPLACE INTO path_aliases(old_path, new_path) VALUES (?, ?)", (old, new))
                conn.execute("UPDATE artifacts SET path = ? WHERE job_id = ? AND path = ?", (new, job["id"], old))
            conn.execute("UPDATE jobs SET storage_layout_version = 2 WHERE id = ?", (job["id"],))
        workspace.update_project_manifest(job["id"])
        migrated[job["id"]] = {"files": len(copies), "checkpointEntries": len(entries)}
    manual = []
    for source, target, reason in _manual_files(workspace):
        checksum = sha256_file(source)
        copy_verified(source, target, checksum)
        manual.append({"source": source.relative_to(workspace.workspace_root).as_posix(),
                       "target": target.relative_to(workspace.workspace_root).as_posix(),
                       "sha256": checksum, "routing": reason})
    inventory = workspace.workbench_root / "migration-inventory.json"
    inventory.parent.mkdir(parents=True, exist_ok=True)
    inventory.write_text(json.dumps(manual, indent=2, ensure_ascii=False), encoding="utf-8")
    return {**report, "mode": "applied", "backup": str(backup), "migrated": migrated,
            "manualFilesCopied": len(manual), "legacyCopiesRetained": True}
