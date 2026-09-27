from __future__ import annotations

import json
import os
import shutil
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

from .storage import Workspace, sha256_file
from .runtime import resolve_node


class RenderDependencyError(RuntimeError):
    pass


def remotion_command(project_root: Path) -> list[str]:
    node = resolve_node()
    cli = project_root / "renderer" / "node_modules" / "@remotion" / "cli" / "remotion-cli.js"
    if node and cli.is_file():
        return [str(node), str(cli)]
    npx = shutil.which("npx.cmd") or shutil.which("npx")
    if npx:
        return [npx, "remotion"]
    raise RenderDependencyError(
        "Remotion CLI is unavailable; run npm install in renderer before preview or render"
    )


def prepare_renderer_job(
    workspace: Workspace,
    job_id: str,
    language: str,
    timeline: dict[str, Any],
    audio_path: Path | None,
) -> Path:
    public_dir = workspace.project_root / "renderer" / "public" / "jobs" / job_id / language
    public_dir.mkdir(parents=True, exist_ok=True)
    props = deepcopy(timeline)
    if audio_path:
        audio_target = public_dir / f"narration{audio_path.suffix.lower()}"
        shutil.copy2(audio_path, audio_target)
        props["audioSrc"] = f"jobs/{job_id}/{language}/{audio_target.name}"
    else:
        props["audioSrc"] = ""
    assets_dir = public_dir / "assets"
    for track in props.get("soundTracks", []):
        asset = track["asset"]
        source = workspace.resolve_path(asset["path"])
        if not source.is_file() or sha256_file(source) != asset["sha256"]:
            raise RenderDependencyError(f"Sound asset missing or checksum mismatch: {asset['id']}")
        destination = public_dir / "sound" / (asset["sha256"] + source.suffix.lower())
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        track["src"] = f"jobs/{job_id}/{language}/sound/{destination.name}"
    for scene in props.get("scenes", []):
        for asset in [scene.get("asset"), *scene.get("supportAssets", [])]:
            if not asset or not asset.get("path"):
                continue
            source = workspace.resolve_path(asset["path"])
            if not source.is_file():
                scene["status"] = "blocked"
                continue
            if asset.get("sha256") and sha256_file(source) != asset["sha256"]:
                raise RenderDependencyError(f"Asset checksum mismatch: {asset.get('id', source.name)}")
            assets_dir.mkdir(parents=True, exist_ok=True)
            target = assets_dir / source.name
            shutil.copy2(source, target)
            asset["src"] = f"jobs/{job_id}/{language}/assets/{target.name}"
    props_path = public_dir / "props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False, indent=2), encoding="utf-8")
    return props_path


def run_studio(project_root: Path, props_path: Path, output_path: Path, entrypoint: Path | None = None) -> int:
    command = remotion_command(project_root)
    renderer = project_root / "renderer"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["VIDKIT_STUDIO_OUTPUT"] = str(output_path.resolve())
    return subprocess.run(
        [*command, "studio", str(entrypoint or "src/index.ts"), "--props", str(props_path)],
        cwd=renderer,
        env=environment,
        check=False,
    ).returncode


def run_render(project_root: Path, props_path: Path, output: Path, entrypoint: Path | None = None) -> int:
    command = remotion_command(project_root)
    renderer = project_root / "renderer"
    output.parent.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        [
            *command,
            "render",
            str(entrypoint or "src/index.ts"),
            "VidkitShort",
            str(output),
            "--props",
            str(props_path),
            "--codec",
            "h264",
            "--audio-codec",
            "aac",
        ],
        cwd=renderer,
        check=False,
    ).returncode
