from __future__ import annotations

import difflib
import json
import re
import shutil
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
                     include_jev: bool = True, extra_root: Path | None = None) -> list[Path]:
    allowed = (workspace.project_root / "renderer").resolve()
    job_area = workspace.videos_root.resolve()
    pending = [path.resolve() for path in entrypoints]
    seen: set[Path] = set()
    while pending:
        path = pending.pop()
        if path in seen or not path.is_file():
            continue
        if not (path.is_relative_to(allowed) or path.is_relative_to(job_area)
                or (extra_root and path.is_relative_to(extra_root.resolve()))):
            raise ValueError(f"Visual import escapes renderer/job workspace: {path}")
        if "node_modules" in path.parts:
            continue
        if not include_jev and path.name == "JevVisuals.tsx":
            continue
        if path == workspace.project_root.resolve() / "renderer/library/manifest.json":
            continue
        seen.add(path)
        pending.extend(_imports(path))
    return sorted(seen)


def renderer_lock(workspace: Workspace, visual_paths: list[Path] | None = None,
                  *, include_jev: bool = True) -> dict[str, str]:
    root = workspace.project_root
    entries = [root / "renderer/src/VidkitShort.tsx", root / "renderer/src/Root.tsx",
               root / "renderer/src/index.ts", root / "renderer/remotion.config.ts",
               *(visual_paths or [])]
    files = dependency_files(workspace, entries, include_jev=include_jev)
    if (root / "renderer/package-lock.json").is_file():
        files.append(root / "renderer/package-lock.json")
    return {path.relative_to(root).as_posix(): sha256_file(path) for path in sorted(set(files))}


def current_renderer_lock(workspace: Workspace, job_id: str, language: str,
                          timeline: dict[str, Any]) -> dict[str, str]:
    from . import library, visuals

    chosen = {scene.get("componentId", scene.get("component")) for scene in timeline.get("scenes", [])}
    paths = [Path(path) for item in [*visuals.entries(workspace, job_id, language), *library.entries(workspace)]
             if item["id"] in chosen for path in item.get("sourcePaths", [])]
    return renderer_lock(workspace, paths,
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
    excluded = {"checkpoints", "previews", "exports", "qa", "approvals"}
    return [path for path in root.rglob("*") if path.is_file()
            and path.name != "project.json"
            and not any(part in excluded for part in path.relative_to(root).parts)
            and (path.relative_to(root).parts[0] not in job["languages"]
                 or path.relative_to(root).parts[0] == language)]


def latest(workspace: Workspace, job_id: str, language: str) -> dict[str, Any] | None:
    root = workspace.job_root(job_id) / "checkpoints" / language
    items = sorted(root.glob("r*/manifest.json"), key=lambda path: int(path.parent.name[1:])) if root.is_dir() else []
    return json.loads(items[-1].read_text(encoding="utf-8")) if items else None


def checkpoint(workspace: Workspace, job_id: str, language: str,
               lock: dict[str, str] | None = None) -> dict[str, Any]:
    current = latest(workspace, job_id, language)
    revision = current["revision"] + 1 if current else 1
    root = workspace.project_root.resolve()
    destination = workspace.job_root(job_id) / "checkpoints" / language / f"r{revision}"
    files = {path.resolve() for path in _sources(workspace, job_id, language)}
    files.update((root / name).resolve() for name in (lock or renderer_lock(workspace)))
    records = []
    for source in sorted(files):
        if not source.is_relative_to(root) or not source.is_file():
            raise ValueError(f"Checkpoint source is unavailable: {source}")
        relative = source.relative_to(root)
        target = destination / "files" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        records.append({"path": relative.as_posix(), "sha256": sha256_file(target)})
    artifact_revisions = [{"kind": item["kind"], "revision": item["revision"],
                           "sha256": item["sha256"], "status": item["status"]}
                          for item in workspace.list_artifacts(job_id)
                          if item["language"] in {language, None}]
    result = {"jobId": job_id, "language": language, "revision": revision,
              "createdAt": utc_now(), "files": records, "artifactRevisions": artifact_revisions}
    (destination / "manifest.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def diff(workspace: Workspace, job_id: str, language: str) -> dict[str, Any]:
    saved = latest(workspace, job_id, language)
    if not saved:
        return {"checkpoint": None, "changes": [], "issue": "No checkpoint exists"}
    root = workspace.project_root.resolve()
    snapshot = workspace.job_root(job_id) / "checkpoints" / language / f"r{saved['revision']}" / "files"
    known = {item["path"]: item["sha256"] for item in saved["files"]}
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
                before = (snapshot / relative).read_text(encoding="utf-8").splitlines()
                after = path.read_text(encoding="utf-8").splitlines()
                entry["diff"] = "\n".join(difflib.unified_diff(before, after, fromfile="checkpoint", tofile="current", lineterm=""))
            changes.append(entry)
    return {"checkpoint": saved["revision"], "changes": changes}
