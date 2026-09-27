from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from .checkpoints import dependency_files
from .models import ArtifactKind
from .storage import Workspace, sha256_file, slugify


IDENTIFIER = re.compile(r"^[a-z][a-z0-9-]*$")


def _package_root(workspace: Workspace, job_id: str, language: str) -> Path:
    return workspace.job_dir(job_id, language) / "visuals"


def entries(workspace: Workspace, job_id: str, language: str) -> list[dict[str, Any]]:
    root = _package_root(workspace, job_id, language)
    result = []
    for path in root.glob("*/manifest.json"):
        item = json.loads(path.read_text(encoding="utf-8"))
        sources = [root / item["package"] / name for name in item["files"]]
        digest = {name: sha256_file(root / item["package"] / name) for name in item["files"]}
        item["previewValid"] = bool(item.get("previewImage") and item.get("previewClip")
                                    and (root / item["package"] / item["previewImage"]).is_file()
                                    and (root / item["package"] / item["previewClip"]).is_file()
                                    and digest == item.get("previewSourceHashes"))
        item["sha256"] = sha256_file(path)
        item["sourcePaths"] = [str(file) for file in sources]
        result.append(item)
    return result


def add(workspace: Workspace, job_id: str, language: str, source: Path) -> dict[str, Any]:
    if workspace.get_job(job_id)["workflow_version"] < 4:
        raise ValueError("Job visuals require workflow v4")
    source = source.resolve()
    item = json.loads(source.read_text(encoding="utf-8"))
    if item.get("kind") != "component" or not IDENTIFIER.fullmatch(str(item.get("id", ""))):
        raise ValueError("Visual needs kind=component and lowercase hyphenated id")
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(item.get("version", ""))):
        raise ValueError("Visual version must be semantic, e.g. 1.0.0")
    if not isinstance(item.get("propsSchema"), dict) or not item.get("description"):
        raise ValueError("Visual needs propsSchema and description")
    entry = item.get("entrypoint")
    fixture = item.get("fixture")
    if not isinstance(entry, str) or not entry.endswith(".tsx") or not isinstance(fixture, str):
        raise ValueError("Visual needs TSX entrypoint and JSON fixture")
    package = f"{item['id']}-{item['version']}"
    root = _package_root(workspace, job_id, language)
    target = root / package
    if target.exists():
        raise ValueError("Visual version already exists; use a new version")
    files = dependency_files(workspace, [(source.parent / entry).resolve()], extra_root=source.parent)
    files.append((source.parent / fixture).resolve())
    if any(not path.is_relative_to(source.parent) for path in files):
        raise ValueError("Visual imports must remain inside the source package")
    if not (source.parent / fixture).is_file():
        raise FileNotFoundError(source.parent / fixture)
    fixture_data = json.loads((source.parent / fixture).read_text(encoding="utf-8"))
    if not fixture_data.get("scenes") or fixture_data.get("durationSeconds", 0) <= 0:
        raise ValueError("Visual fixture needs scenes and durationSeconds")
    target.mkdir(parents=True)
    relative_files = []
    for path in sorted(set(files)):
        relative = path.relative_to(source.parent)
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        relative_files.append(relative.as_posix())
    stored = {**item, "package": package, "files": relative_files, "preview": fixture,
              "status": "candidate"}
    (target / "manifest.json").write_text(json.dumps(stored, ensure_ascii=False, indent=2), encoding="utf-8")
    workspace.invalidate_downstream(job_id, language, ArtifactKind.STORYBOARD)
    return stored


def preview(workspace: Workspace, job_id: str, language: str, visual_id: str) -> dict[str, str]:
    from .render import remotion_command
    item = next((entry for entry in entries(workspace, job_id, language) if entry["id"] == visual_id), None)
    if item is None:
        raise KeyError(f"Unknown visual: {visual_id}")
    package = _package_root(workspace, job_id, language) / item["package"]
    fixture = package / item["fixture"]
    data = json.loads(fixture.read_text(encoding="utf-8"))
    if not any(scene.get("componentId", scene.get("component")) == visual_id for scene in data["scenes"]):
        raise ValueError("Visual fixture must use its componentId")
    entry = render_entry(workspace, job_id, language, data)
    output = package / "preview.mp4"
    still = package / "preview.png"
    command = remotion_command(workspace.project_root)
    for args in (["render", str(entry), "VidkitShort", str(output), "--props", str(fixture),
                  "--codec", "h264", "--scale", "0.5", "--overwrite"],
                 ["still", str(entry), "VidkitShort", str(still), "--props", str(fixture),
                  "--frame", "30", "--scale", "0.3333333333333333", "--overwrite"]):
        result = subprocess.run([*command, *args], cwd=workspace.project_root / "renderer", check=False)
        if result.returncode:
            raise RuntimeError(f"Visual preview failed: {result.returncode}")
    item = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
    item["previewImage"] = still.name
    item["previewClip"] = output.name
    item["previewSourceHashes"] = {name: sha256_file(package / name) for name in item["files"]}
    (package / "manifest.json").write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"image": str(still), "clip": str(output)}


def render_entry(workspace: Workspace, job_id: str, language: str,
                 timeline: dict[str, Any],
                 supplied_entries: list[dict[str, Any]] | None = None) -> Path:
    selected = {scene.get("componentId", scene.get("component")) for scene in timeline.get("scenes", [])}
    if supplied_entries is None:
        from . import library
        candidates = [*entries(workspace, job_id, language), *library.entries(workspace)]
    else:
        candidates = supplied_entries
    items = [item for item in candidates if item["id"] in selected and item.get("entrypoint")]
    generated = workspace.project_root / "renderer/src/.vidkit-generated" / job_id / language
    generated.mkdir(parents=True, exist_ok=True)
    imports = []
    registry = []
    for index, item in enumerate(items):
        absolute = Path(item["entrypointAbsolute"]) if item.get("entrypointAbsolute") else (
            _package_root(workspace, job_id, language) / item["package"] / item["entrypoint"])
        relative = Path(os.path.relpath(absolute, generated)).as_posix()
        imports.append(f"import Visual{index} from {json.dumps(relative)};")
        registry.append(f"{json.dumps(item['id'])}: Visual{index}")
    source = "\n".join([
        "import React from 'react';",
        "import {registerRoot, Composition} from 'remotion';",
        "import '@fontsource/noto-sans/400.css';",
        "import '@fontsource/noto-sans/700.css';",
        "import {VidkitShort, VidkitShortProps} from '../../../VidkitShort';",
        "import {defaultProps, calculateMetadata} from '../../../Root';",
        *imports,
        f"const registry = {{{', '.join(registry)}}};",
        "const Video: React.FC<VidkitShortProps> = (props) => <VidkitShort {...props} visualRegistry={registry} />;",
        "const Root = () => <Composition id=\"VidkitShort\" component={Video} width={1080} height={1920} fps={30} durationInFrames={300} defaultProps={defaultProps} calculateMetadata={calculateMetadata} />;",
        "registerRoot(Root);",
    ])
    path = generated / "index.tsx"
    path.write_text(source, encoding="utf-8")
    return path
