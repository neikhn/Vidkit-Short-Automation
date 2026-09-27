from __future__ import annotations

import json
import hashlib
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .storage import Workspace, sha256_file, slugify


def _builtins(workspace: Workspace) -> list[dict[str, Any]]:
    path = workspace.project_root / "renderer" / "library" / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    bits_file = workspace.project_root / "renderer" / "library" / "bits.json"
    bits = []
    if bits_file.is_file():
        for bit in json.loads(bits_file.read_text(encoding="utf-8")):
            bits.append({**bit, "version": "0.2.1", "kind": "bit", "status": "example",
                         "description": f"Remotion Bits example: {bit['name']}",
                         "tags": ["bits", bit["category"], *bit["name"].lower().split()],
                         "useCases": [bit["category"]],
                         "limitations": ["Demo content must be adapted and checked before production use"],
                         "propsSchema": {}, "source": "https://remotion-bits.dev/docs/getting-started/",
                         "license": "MIT", "preview": "BitsGallery"})
    return [*manifest["components"], *manifest["themes"], *manifest.get("effects", []),
            *manifest.get("references", []), *bits]


def _candidate_dir(workspace: Workspace) -> Path:
    target = workspace.workspace_root / "library" / "candidates"
    target.mkdir(parents=True, exist_ok=True)
    return target


def entries(workspace: Workspace) -> list[dict[str, Any]]:
    result = _builtins(workspace)
    approved = workspace.project_root / "renderer" / "library" / "approved"
    if approved.is_dir():
        result.extend(json.loads(path.read_text(encoding="utf-8")) for path in approved.glob("*.json"))
    for path in _candidate_dir(workspace).glob("*.json"):
        item = json.loads(path.read_text(encoding="utf-8"))
        if item["status"] == "candidate" or item.get("kind") == "asset":
            result.append(item)
    for item in result:
        if item.get("entrypoint") and item.get("codePath"):
            base = (workspace.workspace_root if item.get("codeLocation") == "workspace" else
                    workspace.project_root / "renderer/library") / item["codePath"]
            item["entrypointAbsolute"] = str((base / item["entrypoint"]).resolve())
            item["sourcePaths"] = [str((base / name).resolve()) for name in item.get("files", [])]
            item["sourceChecksums"] = {name: sha256_file(base / name) if (base / name).is_file() else None
                                       for name in item.get("files", [])}
        if item.get("status") == "candidate" and item.get("kind") in {"component", "theme"}:
            item["previewValid"] = candidate_preview_valid(workspace, item)
        if item.get("kind") == "asset":
            item["manifestSha256"] = checksum(item)
        else:
            item["sha256"] = checksum(item)
    return result


def checksum(entry: dict[str, Any]) -> str:
    stable = {key: value for key, value in entry.items() if key not in {
        "sha256", "manifestSha256", "status", "approvedBy", "preview",
        "fixtureSha256", "previewImage", "previewSha256", "previewManifestSha256", "checkedAt",
        "previewValid", "previewClip", "previewClipSha256",
        "entrypointAbsolute", "sourcePaths",
    }}
    return hashlib.sha256(json.dumps(stable, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def candidate_preview_valid(workspace: Workspace, item: dict[str, Any]) -> bool:
    if (not item.get("fixtureSha256") or not item.get("previewSha256")
            or item.get("previewManifestSha256") != checksum(item)):
        return False
    fixture = workspace.workspace_root / item.get("preview", "")
    image = workspace.workspace_root / item.get("previewImage", "")
    clip = workspace.workspace_root / item.get("previewClip", "") if item.get("entrypoint") else None
    return (fixture.is_file() and image.is_file()
            and sha256_file(fixture) == item["fixtureSha256"]
            and sha256_file(image) == item["previewSha256"]
            and (clip is None or (clip.is_file() and sha256_file(clip) == item.get("previewClipSha256"))))


def locks_match(workspace: Workspace, timeline: dict[str, Any],
                extra_entries: list[dict[str, Any]] | None = None) -> bool:
    current = {(item["id"], item["version"]): item["sha256"]
               for item in [*entries(workspace), *(extra_entries or [])]}
    locks = [*timeline.get("componentLocks", []), *timeline.get("effectLocks", [])]
    if timeline.get("themeLock"):
        locks.append(timeline["themeLock"])
    return all(current.get((item["id"], item["version"])) == item.get("sha256") for item in locks)


def search(workspace: Workspace, query: str = "", **filters: str | None) -> list[dict[str, Any]]:
    words = query.casefold().split()
    result = []
    for entry in entries(workspace):
        haystack = " ".join(str(entry.get(key, "")) for key in ("id", "description", "tags", "useCases")).casefold()
        if not all(word in haystack for word in words):
            continue
        kind, status, theme, aspect = (filters.get(name) for name in ("kind", "status", "theme", "aspect"))
        if kind and entry["kind"] != kind:
            continue
        if status and entry["status"] != status:
            continue
        if theme and entry.get("kind") == "theme" and entry["id"] != theme:
            continue
        if theme and entry.get("themes") and theme not in entry["themes"]:
            continue
        entry_aspect = entry.get("aspect", "portrait" if entry["kind"] in {"component", "theme", "effect"} else None)
        if aspect and entry_aspect != aspect:
            continue
        result.append(entry)
    return result


def show(workspace: Workspace, entry_id: str, version: str | None = None) -> dict[str, Any]:
    matches = [item for item in entries(workspace) if item["id"] == entry_id and
               (version is None or item["version"] == version)]
    if not matches:
        raise KeyError(f"Library entry not found: {entry_id}")
    return matches[-1]


def add_candidate(workspace: Workspace, source: Path) -> dict[str, Any]:
    item = json.loads(source.read_text(encoding="utf-8"))
    required = {"id", "version", "kind", "description", "tags", "useCases", "limitations",
                "propsSchema", "source", "license"}
    if item.get("kind") != "asset":
        required.add("preview")
    missing = required - item.keys()
    if missing:
        raise ValueError(f"Library manifest missing: {', '.join(sorted(missing))}")
    if item["kind"] not in {"component", "theme", "asset"}:
        raise ValueError("Unsupported library entry kind")
    if item["kind"] == "component":
        builtin_ids = {entry["id"] for entry in _builtins(workspace) if entry["kind"] == "component"}
        if not item.get("entrypoint") and item.get("baseComponent") not in builtin_ids:
            raise ValueError("Candidate component requires a tested baseComponent from the built-in registry")
    if item["kind"] == "theme":
        style = item.get("style", {})
        if not {"background", "surface", "text", "muted", "accent", "pattern",
                "typography", "motionIntensity", "captionStyle"} <= set(style):
            raise ValueError("Candidate theme needs complete style tokens")
        if not {"headlineSize", "captionSize"} <= set(style["typography"]) or not {
            "width", "outline", "shadow"} <= set(style["captionStyle"]):
            raise ValueError("Candidate theme typography/caption style is incomplete")
    if any(entry["id"] == item["id"] and entry["version"] == item["version"] for entry in entries(workspace)):
        raise ValueError("Library ID/version already exists")
    item["status"] = "candidate"
    item["sha256"] = sha256_file(source)
    if item["kind"] == "asset":
        media_path = (source.parent / item.get("file", "")).resolve()
        if not item.get("file") or not media_path.is_file():
            raise ValueError("Shared asset manifest needs an existing file")
        if not item.get("evidenceType") or not item.get("usageBasis") or not item.get("sourceUrl"):
            raise ValueError("Shared asset needs evidenceType, usageBasis and sourceUrl")
        item.update(import_shared_asset(workspace, media_path, item))
        item["preview"] = item["path"]
    else:
        fixture = (source.parent / item["preview"]).resolve()
        if not fixture.is_file() or fixture.suffix.lower() != ".json":
            raise ValueError("Candidate preview must point to an existing JSON fixture")
        fixture_data = json.loads(fixture.read_text(encoding="utf-8"))
        if fixture_data.get("schemaVersion") not in {3, 4} or not fixture_data.get("scenes") or fixture_data.get("durationSeconds", 0) <= 0:
            raise ValueError("Candidate fixture must be a v3/v4 Remotion props JSON with scenes and duration")
        expected_component = item["id"] if item.get("entrypoint") else item.get("baseComponent")
        if item["kind"] == "component" and not any(
            scene.get("componentId", scene.get("component", scene.get("layout"))) == expected_component
            for scene in fixture_data["scenes"]
        ):
            raise ValueError("Candidate fixture must show its component")
        if item["kind"] == "theme" and (
            fixture_data.get("theme") != item["id"] or fixture_data.get("themeData") != item["style"]
        ):
            raise ValueError("Candidate theme fixture must use the candidate theme and exact style tokens")
        fixture_target = _candidate_dir(workspace) / "fixtures" / f"{slugify(item['id'])}-{slugify(item['version'])}.json"
        fixture_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fixture, fixture_target)
        item["preview"] = fixture_target.relative_to(workspace.workspace_root).as_posix()
        if item.get("entrypoint"):
            from .checkpoints import dependency_files
            source_root = source.parent.resolve()
            source_entry = (source_root / item["entrypoint"]).resolve()
            if not source_entry.is_relative_to(source_root):
                raise ValueError("Component entrypoint escapes package")
            files = dependency_files(workspace, [source_entry], extra_root=source_root)
            if not files or any(not file.is_relative_to(source_root) for file in files):
                raise ValueError("Component imports must remain inside package")
            code_root = _candidate_dir(workspace) / "code" / f"{slugify(item['id'])}-{slugify(item['version'])}"
            code_root.mkdir(parents=True, exist_ok=False)
            for file in files:
                destination = code_root / file.relative_to(source_root)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file, destination)
            item["files"] = [file.relative_to(source_root).as_posix() for file in files]
            item["codePath"] = code_root.relative_to(workspace.workspace_root).as_posix()
            item["codeLocation"] = "workspace"
    target = _candidate_dir(workspace) / f"{slugify(item['id'])}-{slugify(item['version'])}.json"
    target.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    return item


def preview(workspace: Workspace, entry_id: str) -> Path | str:
    from .render import remotion_command
    item = show(workspace, entry_id)
    if item["status"] == "reference":
        return item["preview"]
    if item["kind"] == "asset":
        return workspace.workspace_root / item["path"]
    if item["kind"] == "bit":
        source_path = (workspace.project_root / "renderer" / "node_modules" / "remotion-bits"
                       / item["sourcePath"]).resolve()
        package_root = (workspace.project_root / "renderer" / "node_modules" / "remotion-bits").resolve()
        if not source_path.is_relative_to(package_root) or not source_path.is_file():
            raise FileNotFoundError("Remotion Bits example source is unavailable; run npm install in renderer")
        width, height = ((1080, 1920) if item["aspect"] == "portrait" else
                         (1080, 1080) if item["aspect"] == "square" else (1920, 1080))
        props_file = workspace.cache_root / "library" / f"{slugify(item['id'])}.json"
        props_file.parent.mkdir(parents=True, exist_ok=True)
        props_file.write_text(json.dumps({"bitId": item["id"], "durationFrames": item["durationFrames"],
                                          "width": width, "height": height}), encoding="utf-8")
        target = workspace.workspace_root / "library" / "previews" / f"{slugify(item['id'])}-0-2-1.png"
        target.parent.mkdir(parents=True, exist_ok=True)
        command = [*remotion_command(workspace.project_root), "still", "src/bits-index.ts", "BitsGallery",
                   str(target), "--props", str(props_file), "--frame",
                   str(min(60, item["durationFrames"] // 2)), "--scale", "0.333", "--overwrite"]
        result = subprocess.run(command, cwd=workspace.project_root / "renderer", check=False)
        if result.returncode != 0:
            raise RuntimeError(f"Remotion Bits preview render failed: {result.returncode}")
        return target
    fixture = workspace.project_root / "renderer" / "library" / item["preview"]
    if not fixture.is_file():
        fixture = workspace.workspace_root / item["preview"]
    if not fixture.is_file():
        raise FileNotFoundError(f"Library fixture missing: {item['preview']}")
    target = workspace.workspace_root / "library" / "previews" / f"{slugify(item['id'])}-{slugify(item['version'])}.png"
    target.parent.mkdir(parents=True, exist_ok=True)
    entrypoint = "src/index.ts"
    if item.get("entrypoint"):
        from .visuals import render_entry
        entrypoint = str(render_entry(workspace, "library", item["id"],
                                      json.loads(fixture.read_text(encoding="utf-8")), [item]))
    command = [*remotion_command(workspace.project_root), "still", entrypoint, "VidkitShort",
               str(target), "--props", str(fixture), "--frame", "30", "--scale", "0.333", "--overwrite"]
    result = subprocess.run(command, cwd=workspace.project_root / "renderer", check=False)
    if result.returncode != 0:
        raise RuntimeError(f"Library preview render failed: {result.returncode}")
    clip = None
    if item.get("entrypoint"):
        clip = target.with_suffix(".mp4")
        motion = [*remotion_command(workspace.project_root), "render", entrypoint, "VidkitShort",
                  str(clip), "--props", str(fixture), "--scale", "0.5", "--overwrite"]
        result = subprocess.run(motion, cwd=workspace.project_root / "renderer", check=False)
        if result.returncode:
            raise RuntimeError(f"Component motion preview failed: {result.returncode}")
    if item["status"] == "candidate":
        if clip:
            item["previewClip"] = clip.relative_to(workspace.workspace_root).as_posix()
            item["previewClipSha256"] = sha256_file(clip)
        item["fixtureSha256"] = sha256_file(fixture)
        item["previewImage"] = target.relative_to(workspace.workspace_root).as_posix()
        item["previewSha256"] = sha256_file(target)
        item["previewManifestSha256"] = checksum(item)
        item["checkedAt"] = datetime.now(UTC).isoformat()
        manifest_file = _candidate_dir(workspace) / f"{slugify(item['id'])}-{slugify(item['version'])}.json"
        manifest_file.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def approve(workspace: Workspace, entry_id: str, reviewer: str) -> dict[str, Any]:
    if not reviewer.strip():
        raise ValueError("Reviewer is required")
    item = show(workspace, entry_id)
    if item["status"] != "candidate":
        raise ValueError("Only candidates can be approved")
    if item["kind"] != "asset":
        if not candidate_preview_valid(workspace, item):
            raise ValueError("Candidate preview is missing or stale; run library preview first")
    target = _candidate_dir(workspace) / f"{slugify(item['id'])}-{slugify(item['version'])}.json"
    item["status"] = "approved"
    item["approvedBy"] = reviewer
    persisted = {key: value for key, value in item.items() if key not in {
        "entrypointAbsolute", "sourcePaths", "sourceChecksums", "sha256", "previewValid"
    }}
    target.write_text(json.dumps(persisted, ensure_ascii=False, indent=2), encoding="utf-8")
    if item["kind"] == "asset":
        return {**item, "approvedLocation": item["path"]}
    approved = workspace.project_root / "renderer" / "library" / "approved"
    approved.mkdir(parents=True, exist_ok=True)
    fixture_source = workspace.workspace_root / item["preview"]
    fixture_target = approved / "fixtures" / fixture_source.name
    fixture_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(fixture_source, fixture_target)
    approved_item = {**persisted, "preview": fixture_target.relative_to(workspace.project_root / "renderer" / "library").as_posix()}
    if item.get("entrypoint"):
        code_source = workspace.workspace_root / item["codePath"]
        code_target = approved / "code" / f"{slugify(item['id'])}-{slugify(item['version'])}"
        if code_target.exists():
            raise ValueError("Approved component version already exists")
        shutil.copytree(code_source, code_target)
        approved_item["codePath"] = code_target.relative_to(workspace.project_root / "renderer/library").as_posix()
        approved_item["codeLocation"] = "renderer"
    approved_manifest = approved / target.name
    approved_manifest.write_text(json.dumps(approved_item, ensure_ascii=False, indent=2), encoding="utf-8")
    return {**item, "approvedManifest": str(approved_manifest), "approvedFixture": str(fixture_target)}


def import_shared_asset(workspace: Workspace, source: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    from .assets import detect_image
    width, height, suffix, mime = detect_image(source)
    checksum = sha256_file(source)
    target_dir = workspace.workspace_root / "library" / "assets"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{checksum}{suffix}"
    if not target.exists():
        shutil.copy2(source, target)
    return {**manifest, "sha256": checksum, "path": target.relative_to(workspace.workspace_root).as_posix(),
            "width": width, "height": height, "mime": mime,
            "aspect": "landscape" if width > height * 1.1 else "portrait" if height > width * 1.1 else "square",
            "status": "candidate"}
