from __future__ import annotations

import difflib
import json
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Any

from .storage import Workspace, sha256_file, utc_now


IMPORT = re.compile(r"(?:\bfrom\s*|\bimport\s*(?:\(\s*)?)['\"](\.[^'\"]+)['\"]")
EXTENSIONS = (".tsx", ".ts", ".jsx", ".js", ".css", ".json")


def _imports(path: Path) -> list[Path]:
    if path.suffix not in {".tsx", ".ts", ".jsx", ".js", ".css"}:
        return []
    paths = []
    content = path.read_text(encoding="utf-8")
    references = IMPORT.findall(content)
    if path.suffix == ".css":
        references += re.findall(r"(?:url\(\s*|@import\s*)['\"]?([^'\"\s)]+)", content)
    for relative in references:
        if relative.startswith(("data:", "http:", "https:", "/")):
            continue
        base = (path.parent / relative).resolve()
        matches = [base, *(base.with_suffix(ext) for ext in EXTENSIONS),
                   *(base / ("index" + ext) for ext in EXTENSIONS)]
        paths.extend(candidate for candidate in matches if candidate.is_file())
    renderer = next((parent for parent in path.parents if parent.name == "renderer"), None)
    if renderer:
        paths.extend(renderer / "public" / name
                     for name in re.findall(r"\bstaticFile\(\s*['\"]([^'\"]+)['\"]\s*\)", content)
                     if (renderer / "public" / name).is_file())
    return paths


def dependency_files(workspace: Workspace, entrypoints: list[Path], *,
                     include_jev: bool = True, extra_root: Path | None = None,
                     job_id: str | None = None) -> list[Path]:
    allowed = (workspace.project_root / "renderer").resolve()
    job_area = workspace.videos_root.resolve()
    candidate_area = (workspace.workspace_root / "library" / "candidates" / "code").resolve()
    pending = [path.resolve() for path in entrypoints]
    seen: set[Path] = set()
    while pending:
        path = pending.pop()
        if path in seen or not path.is_file():
            continue
        if not (path.is_relative_to(allowed) or path.is_relative_to(job_area)
                or path.is_relative_to(candidate_area)
                or (extra_root and path.is_relative_to(extra_root.resolve()))):
            raise ValueError(f"Visual import escapes renderer/job workspace: {path}")
        if "node_modules" in path.parts:
            continue
        public_jobs = workspace.project_root / "renderer/public/jobs"
        if job_id and path.is_relative_to(public_jobs):
            if path.relative_to(public_jobs).parts[0] != job_id:
                continue
        if not include_jev and path.name == "JevVisuals.tsx":
            continue
        if path == workspace.project_root.resolve() / "renderer/library/manifest.json":
            continue
        seen.add(path)
        pending.extend(_imports(path))
    return sorted(seen)


def renderer_lock(workspace: Workspace, visual_paths: list[Path] | None = None,
                  *, include_jev: bool = True, job_id: str | None = None) -> dict[str, str]:
    root = workspace.project_root
    entries = [root / "renderer/src/VidkitShort.tsx", root / "renderer/src/Root.tsx",
               root / "renderer/src/index.ts", root / "renderer/remotion.config.ts",
               *(visual_paths or [])]
    files = dependency_files(workspace, entries, include_jev=include_jev, job_id=job_id)
    if (root / "renderer/package-lock.json").is_file():
        files.append(root / "renderer/package-lock.json")
    return {path.relative_to(root).as_posix(): sha256_file(path) for path in sorted(set(files))}


def current_renderer_lock(workspace: Workspace, job_id: str, language: str,
                          timeline: dict[str, Any]) -> dict[str, str]:
    from . import library, visuals

    chosen = {scene.get("componentId", scene.get("component")) for scene in timeline.get("scenes", [])}
    background_lock = timeline.get("backgroundLock") or {}
    from .backgrounds import resolve
    available = [*visuals.entries(workspace, job_id, language), *library.entries(workspace)]
    layer_locks = timeline.get("backgroundLayers") or (
        resolve(timeline["background"], available, require_motion=False)["backgroundLayers"] if timeline.get("background") is not None else [])
    layer_keys = {(layer["id"], layer["version"], layer["sha256"]) for layer in layer_locks}
    paths = [Path(path) for item in available
             if item["id"] in chosen or (item.get("id"), item.get("version"), item.get("sha256")) in layer_keys
             or (item.get("kind") == "background" and item["id"] == timeline.get("backgroundId")
                                         and (not background_lock or (item.get("version") == background_lock.get("version")
                                                                      and item.get("sha256") == background_lock.get("sha256"))))
             for path in item.get("sourcePaths", [])]
    return renderer_lock(workspace, paths, job_id=job_id,
                         include_jev=any(str(scene.get("motion", {}).get("mode", "")).startswith("jev-")
                                         for scene in timeline.get("scenes", [])))


def lock_diff(workspace: Workspace, lock: dict[str, str]) -> list[str]:
    root = workspace.project_root.resolve()
    changes = []
    for relative, expected in lock.items():
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            changes.append(f"missing: {relative}")
        elif sha256_file(path) != expected:
            changes.append(f"changed: {relative}")
    return changes


def _sources(workspace: Workspace, job_id: str, language: str) -> list[Path]:
    job = workspace.get_job(job_id)
    if language not in job["languages"]:
        raise ValueError(f"Unknown job language: {language}")
    root = workspace.job_root(job_id)
    excluded = {"checkpoints", "history", "previews", "exports", "qa", "approvals", "review"}
    superseded = set()
    if workspace.layout_version(job_id) >= 2:
        with workspace.connect() as conn:
            superseded = {row[0] for row in conn.execute(
                "SELECT old_path FROM path_aliases WHERE old_path LIKE ?",
                (f"videos/{job['folder_name']}/%",))}
    return [path for path in root.rglob("*") if path.is_file()
            and path.name != "project.json"
            and path.relative_to(workspace.workspace_root).as_posix() not in superseded
            and not any(part in excluded for part in path.relative_to(root).parts)
            and (path.relative_to(root).parts[0] not in job["languages"]
                 or path.relative_to(root).parts[0] == language)]


def latest(workspace: Workspace, job_id: str, language: str) -> dict[str, Any] | None:
    root = workspace.checkpoint_dir(job_id, language)
    items = sorted(root.glob("r*/manifest.json"), key=lambda path: int(path.parent.name[1:])) if root.is_dir() else []
    return json.loads(items[-1].read_text(encoding="utf-8")) if items else None


def checkpoint(workspace: Workspace, job_id: str, language: str,
               lock: dict[str, str] | None = None) -> dict[str, Any]:
    current = latest(workspace, job_id, language)
    revision = current["revision"] + 1 if current else 1
    root = workspace.project_root.resolve()
    destination = workspace.checkpoint_dir(job_id, language) / f"r{revision}"
    files = {path.resolve() for path in _sources(workspace, job_id, language)}
    files.update((root / name).resolve() for name in (lock or renderer_lock(workspace, job_id=job_id)))
    records = []
    for source in sorted(files):
        if not source.is_relative_to(root) or not source.is_file():
            raise ValueError(f"Checkpoint source is unavailable: {source}")
        relative = source.relative_to(root)
        checksum = sha256_file(source)
        if workspace.layout_version(job_id) >= 2:
            target = workspace.objects_root / checksum[:2] / checksum
            if not target.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(target.name + "." + uuid.uuid4().hex + ".tmp")
                try:
                    shutil.copy2(source, temporary)
                    if sha256_file(temporary) != checksum:
                        raise ValueError(f"Checkpoint copy changed: {source}")
                    os.replace(temporary, target)
                finally:
                    temporary.unlink(missing_ok=True)
        else:
            target = destination / "files" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        records.append({"path": relative.as_posix(), "sha256": checksum})
    artifact_revisions = [{"kind": item["kind"], "revision": item["revision"],
                           "sha256": item["sha256"], "status": item["status"]}
                          for item in workspace.list_artifacts(job_id)
                          if item["language"] in {language, None}]
    result = {"jobId": job_id, "language": language, "revision": revision,
              "createdAt": utc_now(), "files": records, "artifactRevisions": artifact_revisions}
    destination.mkdir(parents=True, exist_ok=True)
    temporary = destination / "manifest.json.tmp"
    temporary.write_text(json.dumps(result, indent=2), encoding="utf-8")
    os.replace(temporary, destination / "manifest.json")
    return result


def diff(workspace: Workspace, job_id: str, language: str) -> dict[str, Any]:
    saved = latest(workspace, job_id, language)
    if not saved:
        return {"checkpoint": None, "changes": [], "issue": "No checkpoint exists"}
    root = workspace.project_root.resolve()
    snapshot = workspace.checkpoint_dir(job_id, language) / f"r{saved['revision']}" / "files"
    known = {}
    for item in saved["files"]:
        original = item["path"]
        current_path = workspace.resolve_path(original.removeprefix("workspace/")) if original.startswith("workspace/") else root / original
        key = current_path.relative_to(root).as_posix() if current_path.is_relative_to(root) else original
        known[key] = item["sha256"]
    known.pop((workspace.job_root(job_id) / "project.json").relative_to(root).as_posix(), None)
    current = {path.resolve().relative_to(root).as_posix() for path in _sources(workspace, job_id, language)}
    from .models import ArtifactKind
    timeline = workspace.latest_artifact(job_id, ArtifactKind.TIMELINE, language)
    if timeline:
        payload = json.loads(workspace.resolve_path(timeline).read_text(encoding="utf-8"))
        current.update(current_renderer_lock(workspace, job_id, language, payload))
    else:
        current.update(renderer_lock(workspace))
    changes = []
    for relative in sorted(set(known) | current):
        path = (root / relative).resolve()
        if relative not in known:
            changes.append({"path": relative, "status": "added"})
        elif not path.is_file():
            changes.append({"path": relative, "status": "deleted"})
        elif sha256_file(path) != known[relative]:
            entry: dict[str, Any] = {"path": relative, "status": "modified"}
            if path.suffix in {".json", ".ts", ".tsx", ".css", ".md"}:
                saved_file = snapshot / relative
                if not saved_file.is_file():
                    saved_file = workspace.objects_root / known[relative][:2] / known[relative]
                before = saved_file.read_text(encoding="utf-8").splitlines()
                after = path.read_text(encoding="utf-8").splitlines()
                entry["diff"] = "\n".join(difflib.unified_diff(before, after, fromfile="checkpoint", tofile="current", lineterm=""))
            changes.append(entry)
    return {"checkpoint": saved["revision"], "changes": changes}
