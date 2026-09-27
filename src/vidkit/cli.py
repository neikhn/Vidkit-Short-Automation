from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from .assets import load_asset_manifest, prepare_asset_entry
from .config import load_env_file, voice_id_for
from .elevenlabs import ElevenLabsClient
from .media import audio_duration
from .models import ArtifactKind, ArtifactStatus, Mode
from .render import prepare_renderer_job, remotion_command, run_render, run_studio
from .runtime import resolve_node
from . import checkpoints, library, sound, visuals, workflow
from .script_bundle import validate_script_bundle
from .storage import Workspace, sha256_file, slugify
from .subtitles import render_srt, render_vtt
from .timeline import build_draft_timeline, compile_storyboard, validate_storyboard_shape
from .transcript import load_json, normalize_transcript, validate_transcript


def project_root() -> Path:
    return Path.cwd()


def read_artifact_json(workspace: Workspace, artifact: dict[str, Any]) -> dict[str, Any]:
    return json.loads(workspace.resolve_path(artifact).read_text(encoding="utf-8"))


def require_artifact(
    workspace: Workspace, job_id: str, language: str | None, kind: ArtifactKind
) -> dict[str, Any]:
    artifact = workspace.latest_artifact(job_id, kind, language)
    if artifact is None:
        suffix = f"/{language}" if language else ""
        raise RuntimeError(f"Missing {kind.value} artifact for {job_id}{suffix}")
    return artifact


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vidkit")
    parser.add_argument("--root", type=Path, default=project_root())
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init")
    sub.add_parser("migrate")
    doctor = sub.add_parser("doctor")
    doctor.add_argument("--json", action="store_true")

    create = sub.add_parser("create")
    create.add_argument("topic")
    create.add_argument("--languages", default="vi,en")
    create.add_argument("--mode", choices=[mode.value for mode in Mode], default=Mode.REVIEW.value)
    create.add_argument("--source-url")
    create.add_argument("--workflow-version", type=int, choices=[2, 3, 4], default=4,
                        help=argparse.SUPPRESS)

    for name in ("checkpoint", "diff"):
        command = sub.add_parser(name)
        command.add_argument("job_id")
        command.add_argument("language")

    add_visual = sub.add_parser("add-visual")
    add_visual.add_argument("job_id")
    add_visual.add_argument("language")
    add_visual.add_argument("file", type=Path)
    sound_plan = sub.add_parser("add-sound-plan")
    sound_plan.add_argument("job_id")
    sound_plan.add_argument("language")
    sound_plan.add_argument("file", type=Path)
    for name in ("sfx", "music"):
        audio_gen = sub.add_parser(name)
        audio_gen.add_argument("action", choices=["generate"])
        audio_gen.add_argument("job_id")
        audio_gen.add_argument("language")
        if name == "sfx":
            audio_gen.add_argument("--cue", required=True)
        audio_gen.add_argument("--new-take", action="store_true", help="Explicitly generate another take")
    audio_parser = sub.add_parser("audio")
    audio_commands = audio_parser.add_subparsers(dest="audio_command", required=True)
    audio_commands.add_parser("reindex")
    audio_import = audio_commands.add_parser("import")
    audio_import.add_argument("job_id")
    audio_import.add_argument("file", type=Path)
    audio_import.add_argument("--asset-id", required=True)
    audio_import.add_argument("--kind", choices=["sfx", "music"], required=True)
    audio_import.add_argument("--description", required=True)
    audio_import.add_argument("--source", required=True)
    audio_import.add_argument("--usage-basis", required=True)
    audio_share = audio_commands.add_parser("share")
    audio_share.add_argument("job_id")
    audio_share.add_argument("asset_id")
    audio_share.add_argument("--purpose", required=True)
    audio_reuse = audio_commands.add_parser("reuse")
    audio_reuse.add_argument("job_id")
    audio_reuse.add_argument("entry_id")
    audio_reuse.add_argument("--asset-id", required=True)
    for name in ("preview", "requests", "recover"):
        audio_command = audio_commands.add_parser(name)
        audio_command.add_argument("job_id")
        audio_command.add_argument("language")
        if name == "recover":
            audio_command.add_argument("request_id")
            audio_command.add_argument("file", type=Path)
    preview_visual = sub.add_parser("preview-visual")
    preview_visual.add_argument("job_id")
    preview_visual.add_argument("language")
    preview_visual.add_argument("visual_id")

    feedback = sub.add_parser("add-feedback")
    feedback.add_argument("job_id")
    feedback.add_argument("language")
    feedback.add_argument("file", type=Path)
    metrics = sub.add_parser("metrics")
    metrics.add_argument("job_id")
    metrics.add_argument("language")

    listing = sub.add_parser("list")
    listing.add_argument("--status")
    listing.add_argument("--json", action="store_true")

    for name in ("show", "status", "open"):
        command = sub.add_parser(name)
        command.add_argument("job_id")

    rename = sub.add_parser("rename")
    rename.add_argument("job_id")
    rename.add_argument("title")

    next_command = sub.add_parser("next")
    next_command.add_argument("job_id")
    next_command.add_argument("--language")
    next_command.add_argument("--json", action="store_true")

    add_source = sub.add_parser("add-source")
    add_source.add_argument("job_id")
    add_source.add_argument("file", type=Path)

    add_script = sub.add_parser("add-script")
    add_script.add_argument("job_id")
    add_script.add_argument("language")
    add_script.add_argument("file", type=Path)

    add_asset = sub.add_parser("add-asset")
    add_asset.add_argument("job_id")
    add_asset.add_argument("file", type=Path)
    add_asset.add_argument("--description", required=True)
    add_asset.add_argument("--usage-basis", required=True)
    add_asset.add_argument("--source-url")
    add_asset.add_argument("--type", choices=["screenshot", "logo", "artwork", "chart", "diagram", "illustration"], default="artwork")

    for name in ("add-brief", "add-caption-plan"):
        command = sub.add_parser(name)
        command.add_argument("job_id")
        command.add_argument("language")
        command.add_argument("file", type=Path)

    approval = sub.add_parser("approve")
    approval.add_argument("job_id")
    approval.add_argument("language")
    approval.add_argument("stage", choices=["concept", "export"])
    approval.add_argument("--reviewer", required=True)

    qa = sub.add_parser("qa")
    qa.add_argument("job_id")
    qa.add_argument("language")
    qa.add_argument("file", type=Path, nargs="?")

    library_parser = sub.add_parser("library")
    library_commands = library_parser.add_subparsers(dest="library_command", required=True)
    lib_search = library_commands.add_parser("search")
    lib_search.add_argument("query", nargs="?", default="")
    for name in ("kind", "theme", "status", "aspect"):
        lib_search.add_argument(f"--{name}")
    for name in ("show", "preview"):
        command = library_commands.add_parser(name)
        command.add_argument("entry_id")
    lib_add = library_commands.add_parser("add")
    lib_add.add_argument("file", type=Path)
    lib_approve = library_commands.add_parser("approve")
    lib_approve.add_argument("entry_id")
    lib_approve.add_argument("--reviewer", required=True)

    add_storyboard = sub.add_parser("add-storyboard")
    add_storyboard.add_argument("job_id")
    add_storyboard.add_argument("language")
    add_storyboard.add_argument("file", type=Path)

    tts = sub.add_parser("tts")
    tts.add_argument("job_id")
    tts.add_argument("language")
    tts.add_argument("--voice-id")

    transcribe = sub.add_parser("transcribe")
    transcribe.add_argument("job_id")
    transcribe.add_argument("language")

    import_transcript = sub.add_parser("import-transcript")
    import_transcript.add_argument("job_id")
    import_transcript.add_argument("language")
    import_transcript.add_argument("file", type=Path)
    import_transcript.add_argument("--audio", type=Path)

    timeline = sub.add_parser("timeline")
    timeline.add_argument("job_id")
    timeline.add_argument("language")
    timeline.add_argument("--draft", action="store_true")

    for name in ("studio", "preview", "render"):
        command = sub.add_parser(name)
        command.add_argument("job_id")
        command.add_argument("language")
        if name == "preview":
            command.add_argument("--stage", choices=["concept", "video"], default="video")
            command.add_argument("--scenes", help="Comma-separated scene IDs for concept preview")

    import_render = sub.add_parser("import-render")
    import_render.add_argument("job_id")
    import_render.add_argument("language")
    import_render.add_argument("file", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    load_env_file(root / ".env")
    workspace = Workspace(root)
    workspace.initialize()
    try:
        if args.command == "init":
            print(f"Initialized {workspace.workspace_root}")
        elif args.command == "migrate":
            print(json.dumps(workspace.migrate_legacy(), ensure_ascii=False, indent=2))
        elif args.command == "doctor":
            _doctor(workspace, args.json)
        elif args.command == "create":
            print(
                workspace.create_job(
                    args.topic, args.languages.split(","), Mode(args.mode), args.source_url,
                    args.workflow_version,
                )
            )
        elif args.command == "checkpoint":
            print(json.dumps(checkpoints.checkpoint(workspace, args.job_id, args.language), ensure_ascii=False, indent=2))
        elif args.command == "diff":
            print(json.dumps(checkpoints.diff(workspace, args.job_id, args.language), ensure_ascii=False, indent=2))
        elif args.command == "add-visual":
            print(json.dumps(visuals.add(workspace, args.job_id, args.language, args.file), ensure_ascii=False, indent=2))
        elif args.command == "add-sound-plan":
            print(sound.add_plan(workspace, args.job_id, args.language, args.file)["path"])
        elif args.command in {"sfx", "music"}:
            print(json.dumps(sound.generate(workspace, args.job_id, args.language, args.command,
                                           getattr(args, "cue", None), args.new_take), ensure_ascii=False, indent=2))
        elif args.command == "audio":
            if args.audio_command == "reindex":
                print(json.dumps({"indexed": sound.reindex_library(workspace)}))
            elif args.audio_command == "share":
                print(json.dumps(sound.share_asset(workspace, args.job_id, args.asset_id, args.purpose), ensure_ascii=False, indent=2))
            elif args.audio_command == "reuse":
                print(json.dumps(sound.reuse_asset(workspace, args.job_id, args.entry_id, args.asset_id), ensure_ascii=False, indent=2))
            elif args.audio_command == "import":
                print(json.dumps(sound.register_asset(workspace, args.job_id, args.file, args.asset_id,
                    args.kind, {"description": args.description, "source": args.source,
                                "usageBasis": args.usage_basis}), ensure_ascii=False, indent=2))
            elif args.audio_command == "recover":
                print(json.dumps(sound.recover_request(workspace, args.job_id, args.language,
                    args.request_id, args.file), ensure_ascii=False, indent=2))
            elif args.audio_command == "requests":
                request_dir = workspace.job_dir(args.job_id, args.language) / "audio" / "sound-plan" / "requests"
                print(json.dumps([json.loads(path.read_text(encoding="utf-8"))
                                  for path in sorted(request_dir.glob("*.json"))], ensure_ascii=False, indent=2))
            else:
                return _audio_preview(workspace, args.job_id, args.language)
        elif args.command == "preview-visual":
            print(json.dumps(visuals.preview(workspace, args.job_id, args.language, args.visual_id), ensure_ascii=False, indent=2))
        elif args.command == "add-feedback":
            _add_feedback(workspace, args.job_id, args.language, args.file)
        elif args.command == "metrics":
            _metrics(workspace, args.job_id, args.language)
        elif args.command == "list":
            _list_jobs(workspace, args.status, args.json)
        elif args.command in {"show", "status"}:
            _show(workspace, args.job_id)
        elif args.command == "open":
            _open_job(workspace, args.job_id)
        elif args.command == "rename":
            print(json.dumps(workspace.rename_job(args.job_id, args.title), ensure_ascii=False, indent=2))
        elif args.command == "next":
            _next(workspace, args.job_id, args.language, args.json)
        elif args.command == "add-source":
            _add_source(workspace, args.job_id, args.file)
        elif args.command == "add-script":
            _add_script(workspace, args.job_id, args.language, args.file)
        elif args.command == "add-asset":
            _add_asset(
                workspace,
                args.job_id,
                args.file,
                args.description,
                args.usage_basis,
                args.source_url,
                args.type,
            )
        elif args.command == "add-brief":
            print(workflow.add_brief(workspace, args.job_id, args.language, args.file)["path"])
        elif args.command == "add-caption-plan":
            print(workflow.add_caption_plan(workspace, args.job_id, args.language, args.file)["path"])
        elif args.command == "approve":
            print(workflow.approve(workspace, args.job_id, args.language, args.stage, args.reviewer)["path"])
        elif args.command == "qa":
            supplied = load_json(args.file) if args.file else None
            print(workflow.make_qa(workspace, args.job_id, args.language, supplied)["path"])
        elif args.command == "library":
            _library(workspace, args)
        elif args.command == "add-storyboard":
            _add_storyboard(workspace, args.job_id, args.language, args.file)
        elif args.command == "tts":
            _tts(workspace, args.job_id, args.language, args.voice_id)
        elif args.command == "transcribe":
            _transcribe(workspace, args.job_id, args.language)
        elif args.command == "import-transcript":
            _import_transcript(workspace, args.job_id, args.language, args.file, args.audio)
        elif args.command == "timeline":
            _timeline(workspace, args.job_id, args.language, args.draft)
        elif args.command in {"studio", "preview", "render"}:
            if args.command == "preview" and args.stage == "concept":
                return _concept_preview(workspace, args.job_id, args.language, args.scenes)
            if args.command == "preview" and args.scenes:
                raise ValueError("--scenes is only available for --stage concept")
            return _remotion(workspace, args.job_id, args.language, args.command)
        elif args.command == "import-render":
            _import_render(workspace, args.job_id, args.language, args.file)
        return 0
    except (KeyError, ValueError, RuntimeError, FileNotFoundError, OSError) as exc:
        print(f"vidkit: {exc}", file=sys.stderr)
        return 2


def _doctor(workspace: Workspace, as_json: bool) -> None:
    local_remotion = (
        workspace.project_root
        / "renderer"
        / "node_modules"
        / "@remotion"
        / "cli"
        / "remotion-cli.js"
    )
    checks = {
        "workspace": workspace.workspace_root.is_dir(),
        "python": sys.version.split()[0],
        "node": str(resolve_node()) if resolve_node() else None,
        "npm": shutil.which("npm.cmd") is not None or shutil.which("npm") is not None,
        "npx": shutil.which("npx.cmd") is not None or shutil.which("npx") is not None,
        "ffprobe": shutil.which("ffprobe") is not None,
        "rendererDependencies": (workspace.project_root / "renderer" / "node_modules").is_dir(),
        "remotionCli": local_remotion.is_file(),
        "elevenLabsApiKey": bool(os.environ.get("ELEVENLABS_API_KEY")),
        "voiceVi": bool(voice_id_for("vi")),
        "voiceEn": bool(voice_id_for("en")),
    }
    try:
        checks["remotionCommand"] = remotion_command(workspace.project_root)
    except RuntimeError as exc:
        checks["remotionCommand"] = str(exc)
    if as_json:
        print(json.dumps(checks, ensure_ascii=False, indent=2))
        return
    for key, value in checks.items():
        print(f"{key:22} {value}")


def _library(workspace: Workspace, args: argparse.Namespace) -> None:
    if args.library_command == "search":
        result = library.search(workspace, args.query, kind=args.kind, theme=args.theme,
                                status=args.status, aspect=args.aspect)
    elif args.library_command in {"show", "preview"}:
        result = library.show(workspace, args.entry_id)
        if args.library_command == "preview":
            preview_path = library.preview(workspace, args.entry_id)
            result = {"id": result["id"], "version": result["version"],
                      "preview": str(preview_path),
                      "motionPreview": str(preview_path.with_suffix(".mp4")) if result.get("entrypoint")
                      and isinstance(preview_path, Path) else None,
                      "description": result["description"], "useCases": result["useCases"],
                      "limitations": result["limitations"]}
    elif args.library_command == "add":
        result = library.add_candidate(workspace, args.file)
    else:
        result = library.approve(workspace, args.entry_id, args.reviewer)
    if args.library_command in {"search", "show"}:
        rows = result if isinstance(result, list) else [result]
        for item in rows:
            item["previewCommand"] = f"vidkit library preview {item['id']}"
            item["storyboardUse"] = (
                {"component": item["id"], "componentVersion": item["version"]}
                if item["kind"] == "component" and item["status"] in {"approved", "candidate"}
                else None
            )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def _list_jobs(workspace: Workspace, status: str | None, as_json: bool) -> None:
    jobs = [job for job in workspace.list_jobs() if status is None or job["status"] == status]
    for job in jobs:
        states = {language: _next_state(workspace, job, language) for language in job["languages"]}
        selected_language = next(
            (language for language, state in states.items() if state["step"] != "review"),
            job["languages"][0],
        )
        job["nextByLanguage"] = states
        job["next"] = states[selected_language]
    if as_json:
        print(json.dumps(jobs, ensure_ascii=False, indent=2))
        return
    print(f"{'ID':12}  {'STATUS':14}  {'LANG':8}  {'NEXT':18}  TITLE / ISSUES")
    for job in jobs:
        next_state = job["next"]
        issues = "; ".join(next_state["issues"])
        suffix = f" / {issues}" if issues else ""
        next_label = f"{next_state['language']}:{next_state['step']}"
        print(
            f"{job['id']:12}  {job['status'][:14]:14}  {','.join(job['languages']):8}  "
            f"{next_label[:18]:18}  {job['topic']}{suffix}"
        )


def _show(workspace: Workspace, job_id: str) -> None:
    payload = {"job": workspace.get_job(job_id), "artifacts": workspace.list_artifacts(job_id)}
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _open_job(workspace: Workspace, job_id: str) -> None:
    path = workspace.job_root(job_id)
    if os.name == "nt":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.run(["xdg-open", str(path)], check=False)
    print(path)


def _next(workspace: Workspace, job_id: str, language: str | None, as_json: bool) -> None:
    job = workspace.get_job(job_id)
    selected = language or job["languages"][0]
    result = _next_state(workspace, job, selected)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"{result['step']}: {result['command']}")
        if result["issues"]:
            print("Issues: " + "; ".join(result["issues"]))


def _next_state(workspace: Workspace, job: dict[str, Any], language: str) -> dict[str, Any]:
    if job.get("workflow_version", 2) >= 3:
        return workflow.next_state(workspace, job, language)
    job_id = job["id"]
    issues: list[str] = []
    source = workspace.latest_artifact(job_id, ArtifactKind.SOURCE, None)
    if not source:
        return {"jobId": job_id, "language": language, "step": "research", "command": f"vidkit add-source {job_id} <source-pack.json>", "issues": issues}
    if source["status"] != ArtifactStatus.CHECKED.value:
        return {"jobId": job_id, "language": language, "step": "research-review", "command": f"vidkit show {job_id}", "issues": [f"source status is {source['status']}"]}
    if not workspace.latest_artifact(job_id, ArtifactKind.SCRIPT, language):
        return {"jobId": job_id, "language": language, "step": "script", "command": f"vidkit add-script {job_id} {language} <script.json>", "issues": issues}
    if not workspace.latest_artifact(job_id, ArtifactKind.AUDIO, language):
        return {"jobId": job_id, "language": language, "step": "voice", "command": f"vidkit tts {job_id} {language}", "issues": issues}
    transcript = _normalized_transcript_artifact(workspace, job_id, language)
    if not transcript:
        return {"jobId": job_id, "language": language, "step": "transcript", "command": f"vidkit transcribe {job_id} {language}", "issues": issues}
    if transcript["status"] != ArtifactStatus.CHECKED.value:
        issues.append(f"transcript status is {transcript['status']}")
    if not workspace.latest_artifact(job_id, ArtifactKind.STORYBOARD, language):
        return {"jobId": job_id, "language": language, "step": "storyboard", "command": f"vidkit add-storyboard {job_id} {language} <storyboard.json>", "issues": issues}
    timeline = workspace.latest_artifact(job_id, ArtifactKind.TIMELINE, language)
    if not timeline:
        return {"jobId": job_id, "language": language, "step": "timeline", "command": f"vidkit timeline {job_id} {language}", "issues": issues}
    timeline_payload = read_artifact_json(workspace, timeline)
    if timeline_payload.get("missingAssets"):
        issues.append("missing assets: " + ", ".join(timeline_payload["missingAssets"]))
        return {"jobId": job_id, "language": language, "step": "assets", "command": f"vidkit add-asset {job_id} <image> --description <text> --usage-basis <basis>", "issues": issues}
    if timeline_payload.get("assetWarnings"):
        issues.extend(timeline_payload["assetWarnings"])
        return {"jobId": job_id, "language": language, "step": "assets-review", "command": f"vidkit show {job_id}", "issues": issues}
    if not workspace.latest_artifact(job_id, ArtifactKind.RENDER, language):
        return {"jobId": job_id, "language": language, "step": "preview", "command": f"vidkit studio {job_id} {language}", "issues": issues}
    return {"jobId": job_id, "language": language, "step": "review", "command": f"vidkit show {job_id}", "issues": issues}


def _add_source(workspace: Workspace, job_id: str, file: Path) -> None:
    payload = load_json(file)
    errors = _validate_source_pack(payload)
    if errors:
        raise ValueError("; ".join(errors))
    for language in workspace.get_job(job_id)["languages"]:
        workspace.invalidate_downstream(job_id, language, ArtifactKind.SOURCE)
    artifact = workspace.add_json_artifact(job_id, None, ArtifactKind.SOURCE, payload, ArtifactStatus.CHECKED)
    print(artifact["path"])


def _validate_source_pack(payload: dict[str, Any]) -> list[str]:
    claims = payload.get("claims")
    if not isinstance(claims, list) or not claims:
        return ["Source pack must contain a non-empty claims list"]
    errors: list[str] = []
    required = ("id", "statement", "sourceUrl", "retrievedAt", "publishedAt", "uncertainty")
    seen: set[str] = set()
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            errors.append(f"claim {index + 1} must be an object")
            continue
        missing = [
            key
            for key in required
            if key not in claim
            or (
                key not in {"publishedAt", "uncertainty"}
                and (claim[key] is None or claim[key] == "")
            )
            or (key in {"publishedAt", "uncertainty"} and claim[key] == "")
        ]
        if missing:
            errors.append(f"claim {index + 1} is missing: {', '.join(missing)}")
        claim_id = str(claim.get("id", ""))
        if claim_id in seen:
            errors.append(f"duplicate claim id: {claim_id}")
        seen.add(claim_id)
    return errors


def _add_script(workspace: Workspace, job_id: str, language: str, file: Path) -> None:
    payload = load_json(file)
    errors = validate_script_bundle(payload)
    if errors:
        raise ValueError("; ".join(errors))
    workspace.invalidate_downstream(job_id, language, ArtifactKind.SCRIPT)
    artifact = workspace.add_json_artifact(job_id, language, ArtifactKind.SCRIPT, payload, ArtifactStatus.CHECKED)
    print(artifact["path"])


def _add_asset(
    workspace: Workspace,
    job_id: str,
    file: Path,
    description: str,
    usage_basis: str,
    source_url: str | None,
    evidence_type: str,
) -> None:
    if not usage_basis.strip():
        raise ValueError("usage basis cannot be empty")
    manifest, previous = load_asset_manifest(workspace, job_id)
    entry, target = prepare_asset_entry(
        workspace, job_id, file, description, usage_basis, source_url, evidence_type
    )
    existing = next((item for item in manifest["assets"] if item["sha256"] == entry["sha256"]), None)
    if existing:
        print(existing["id"])
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(file.resolve(), target)
    manifest["assets"].append(entry)
    artifact = workspace.add_json_artifact(
        job_id,
        None,
        ArtifactKind.ASSET_MANIFEST,
        manifest,
        ArtifactStatus.CHECKED,
        upstream={"asset-manifest": previous["revision"]} if previous else {},
    )
    workspace.invalidate_visuals(job_id)
    print(
        json.dumps(
            {
                "assetId": entry["id"],
                "manifest": artifact["path"],
                "qualityWarnings": entry["qualityWarnings"],
            },
            ensure_ascii=False,
        )
    )


def _add_storyboard(workspace: Workspace, job_id: str, language: str, file: Path) -> None:
    payload = load_json(file)
    if payload.get("language") and payload["language"] != language:
        raise ValueError(f"Storyboard language {payload['language']} does not match {language}")
    errors = validate_storyboard_shape(payload)
    if errors:
        raise ValueError("; ".join(errors))
    workspace.invalidate_downstream(job_id, language, ArtifactKind.STORYBOARD)
    artifact = workspace.add_json_artifact(job_id, language, ArtifactKind.STORYBOARD, payload, ArtifactStatus.CHECKED)
    print(artifact["path"])


def _tts(workspace: Workspace, job_id: str, language: str, voice_id: str | None) -> None:
    job = workspace.get_job(job_id)
    if job.get("workflow_version", 2) >= 3 and job["mode"] == Mode.REVIEW.value and not workflow.current_approval(workspace, job_id, language, "concept"):
        raise RuntimeError("Concept approval for current script and brief is required before TTS")
    voice_id = voice_id or voice_id_for(language)
    if not voice_id:
        variable = f"VIDKIT_VOICE_{language.upper().replace('-', '_')}"
        raise RuntimeError(f"Missing voice ID: set {variable} in .env or pass --voice-id")
    script_artifact = require_artifact(workspace, job_id, language, ArtifactKind.SCRIPT)
    script = read_artifact_json(workspace, script_artifact)
    output = workspace.pending_path(job_id, language, "narration.pending.mp3")
    ElevenLabsClient().text_to_speech(script["tts_input"], voice_id, output)
    workspace.invalidate_downstream(job_id, language, ArtifactKind.AUDIO)
    artifact = workspace.add_file_artifact(
        job_id,
        language,
        ArtifactKind.AUDIO,
        output,
        ArtifactStatus.GENERATED,
        upstream={"script": script_artifact["revision"]},
        metadata={"provider": "elevenlabs", "model": "eleven_v3", "voice_id": voice_id},
    )
    output.unlink(missing_ok=True)
    print(artifact["path"])


def _transcribe(workspace: Workspace, job_id: str, language: str) -> None:
    audio_artifact = require_artifact(workspace, job_id, language, ArtifactKind.AUDIO)
    payload = ElevenLabsClient().speech_to_text(workspace.resolve_path(audio_artifact), language_code=language)
    raw_path = workspace.pending_path(job_id, language, "transcript.raw.pending.json")
    raw_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    workspace.invalidate_downstream(job_id, language, ArtifactKind.TRANSCRIPT)
    _store_transcript(workspace, job_id, language, raw_path, audio_artifact)
    raw_path.unlink(missing_ok=True)


def _import_transcript(
    workspace: Workspace,
    job_id: str,
    language: str,
    transcript_file: Path,
    audio_file: Path | None,
) -> None:
    job = workspace.get_job(job_id)
    if job.get("workflow_version", 2) >= 3 and job["mode"] == Mode.REVIEW.value and not workflow.current_approval(workspace, job_id, language, "concept"):
        raise RuntimeError("Concept approval is required before importing narration or transcript")
    audio_artifact = workspace.latest_artifact(job_id, ArtifactKind.AUDIO, language)
    if audio_file:
        if not audio_file.is_file():
            raise FileNotFoundError(audio_file)
        workspace.invalidate_downstream(job_id, language, ArtifactKind.AUDIO)
        audio_artifact = workspace.add_file_artifact(
            job_id, language, ArtifactKind.AUDIO, audio_file, ArtifactStatus.GENERATED, metadata={"provider": "import"}
        )
    workspace.invalidate_downstream(job_id, language, ArtifactKind.TRANSCRIPT)
    _store_transcript(workspace, job_id, language, transcript_file, audio_artifact)


def _store_transcript(
    workspace: Workspace,
    job_id: str,
    language: str,
    transcript_file: Path,
    audio_artifact: dict[str, Any] | None,
) -> None:
    raw_payload = load_json(transcript_file)
    normalized = normalize_transcript(raw_payload)
    script_artifact = workspace.latest_artifact(job_id, ArtifactKind.SCRIPT, language)
    expected = read_artifact_json(workspace, script_artifact).get("expected_spoken_text") if script_artifact else None
    duration = audio_duration(workspace.resolve_path(audio_artifact)) if audio_artifact else None
    findings = validate_transcript(normalized, expected, duration)
    normalized["audio"] = {
        "revision": audio_artifact["revision"] if audio_artifact else None,
        "sha256": audio_artifact["sha256"] if audio_artifact else None,
        "duration_seconds": duration,
        "synchronization_verified": duration is not None,
    }
    normalized["findings"] = [finding.to_dict() for finding in findings]
    has_error = any(finding.severity == "error" for finding in findings)
    status = ArtifactStatus.NEEDS_REVIEW if has_error or not audio_artifact or duration is None else ArtifactStatus.CHECKED
    raw_artifact = workspace.add_file_artifact(
        job_id,
        language,
        ArtifactKind.TRANSCRIPT,
        transcript_file,
        ArtifactStatus.GENERATED,
        upstream={"audio": audio_artifact["revision"]} if audio_artifact else {},
        metadata={"variant": "raw"},
    )
    artifact = workspace.add_json_artifact(
        job_id,
        language,
        ArtifactKind.TRANSCRIPT,
        normalized,
        status,
        upstream={"audio": audio_artifact["revision"]} if audio_artifact else {},
        metadata={"variant": "normalized", "raw_revision": raw_artifact["revision"]},
    )
    print(artifact["path"])


def _normalized_transcript_artifact(
    workspace: Workspace, job_id: str, language: str
) -> dict[str, Any] | None:
    artifacts = [
        artifact
        for artifact in workspace.list_artifacts(job_id)
        if artifact["language"] == language
        and artifact["kind"] == ArtifactKind.TRANSCRIPT.value
        and artifact["metadata"].get("variant") == "normalized"
        and artifact["status"] != ArtifactStatus.INVALIDATED.value
    ]
    return artifacts[-1] if artifacts else None


def _timeline(workspace: Workspace, job_id: str, language: str, draft: bool) -> None:
    job_info = workspace.get_job(job_id)
    if job_info.get("workflow_version", 2) >= 3:
        require_artifact(workspace, job_id, language, ArtifactKind.BRIEF)
        if job_info["mode"] == Mode.REVIEW.value and not workflow.current_approval(workspace, job_id, language, "concept"):
            raise RuntimeError("Concept approval is required before timeline compilation")
    transcript_artifact = _normalized_transcript_artifact(workspace, job_id, language)
    if not transcript_artifact:
        raise RuntimeError("Missing normalized transcript")
    transcript = read_artifact_json(workspace, transcript_artifact)
    script_artifact = require_artifact(workspace, job_id, language, ArtifactKind.SCRIPT)
    script = read_artifact_json(workspace, script_artifact)
    audio_artifact = require_artifact(workspace, job_id, language, ArtifactKind.AUDIO)
    storyboard_artifact = None
    caption_plan_artifact = workspace.latest_artifact(job_id, ArtifactKind.CAPTION_PLAN, language)
    caption_plan = read_artifact_json(workspace, caption_plan_artifact) if caption_plan_artifact else None
    manifest_artifact = workspace.latest_artifact(job_id, ArtifactKind.ASSET_MANIFEST, None)
    if draft:
        timeline = build_draft_timeline(
            transcript, script.get("title") or workspace.get_job(job_id)["topic"], language, audio_artifact["path"]
        )
        missing_assets: list[str] = []
    else:
        storyboard_artifact = require_artifact(workspace, job_id, language, ArtifactKind.STORYBOARD)
        storyboard = read_artifact_json(workspace, storyboard_artifact)
        if job_info.get("workflow_version", 2) >= 3:
            brief = read_artifact_json(workspace, require_artifact(workspace, job_id, language, ArtifactKind.BRIEF))
            if brief.get("soundDirection") and not workspace.latest_artifact(job_id, ArtifactKind.SOUND_PLAN, language):
                raise ValueError("Creative brief requests sound design; add a sound plan before compiling")
            if storyboard.get("theme", "dark-grid") != brief["theme"]:
                raise ValueError("Storyboard theme differs from approved creative brief; revise brief and approval")
            if job_info.get("workflow_version", 2) >= 4:
                reference_ids = {item["id"] for item in brief.get("references", [])}
                for scene in storyboard.get("scenes", []):
                    if not set(scene.get("referenceIds", [])) <= reference_ids:
                        raise ValueError(f"Scene {scene.get('id')} uses an unknown reference")
        manifest, _ = load_asset_manifest(workspace, job_id)
        timeline, missing_assets = compile_storyboard(
            transcript,
            storyboard,
            manifest,
            script.get("title") or workspace.get_job(job_id)["topic"],
            language,
            audio_artifact["path"],
            caption_plan,
            ([*library.entries(workspace), *visuals.entries(workspace, job_id, language)]
             if workspace.get_job(job_id).get("workflow_version", 2) >= 4 else
             library.entries(workspace) if workspace.get_job(job_id).get("workflow_version", 2) >= 3 else None),
        )
    job = workspace.get_job(job_id)
    sound.compile_sound(workspace, job_id, language, timeline, transcript["words"])
    if job.get("workflow_version", 2) >= 3:
        timeline["schemaVersion"] = 3
        timeline["rendererCodeSha256"] = sha256_file(workspace.project_root / "renderer" / "src" / "VidkitShort.tsx")
        timeline["rendererPackageLockSha256"] = sha256_file(workspace.project_root / "renderer" / "package-lock.json")
        if job.get("workflow_version", 2) >= 4:
            timeline["schemaVersion"] = 4
            timeline["rendererLock"] = checkpoints.current_renderer_lock(workspace, job_id, language, timeline)
        if "theme" not in timeline:
            brief_artifact = workspace.latest_artifact(job_id, ArtifactKind.BRIEF, language)
            timeline["theme"] = read_artifact_json(workspace, brief_artifact).get("theme", "dark-grid") if brief_artifact else "dark-grid"
    validation_issues: list[str] = []
    if transcript_artifact["status"] != ArtifactStatus.CHECKED.value:
        validation_issues.append(f"transcript status is {transcript_artifact['status']}")
    validation_issues.extend(timeline.get("assetWarnings", []))
    source_artifact = workspace.latest_artifact(job_id, ArtifactKind.SOURCE, None)
    if job.get("workflow_version", 2) >= 3 and source_artifact:
        claim_ids = {item["id"] for item in read_artifact_json(workspace, source_artifact).get("claims", [])}
        unknown_claims = set(timeline.get("claimToScene", {})) - claim_ids
        if unknown_claims:
            validation_issues.append("unknown storyboard claim IDs: " + ", ".join(sorted(unknown_claims)))
    if job["mode"] == Mode.AUTOMATIC.value and (
        not source_artifact or source_artifact["status"] != ArtifactStatus.CHECKED.value
    ):
        validation_issues.append("checked source pack is required in automatic mode")
    timeline["validationIssues"] = validation_issues
    workspace.invalidate_downstream(job_id, language, ArtifactKind.TIMELINE)
    upstream = {
        "script": script_artifact["revision"],
        "audio": audio_artifact["revision"],
        "transcript": transcript_artifact["revision"],
    }
    if storyboard_artifact:
        upstream["storyboard"] = storyboard_artifact["revision"]
    if caption_plan_artifact:
        upstream["caption-plan"] = caption_plan_artifact["revision"]
    if manifest_artifact:
        upstream["asset-manifest"] = manifest_artifact["revision"]
    sound_plan = workspace.latest_artifact(job_id, ArtifactKind.SOUND_PLAN, language)
    if sound_plan:
        upstream["sound-plan"] = sound_plan["revision"]
        sound_assets = workspace.latest_artifact(job_id, ArtifactKind.SOUND_ASSETS, None)
        if sound_assets:
            upstream["sound-assets"] = sound_assets["revision"]
    if missing_assets:
        timeline_status = ArtifactStatus.BLOCKED
    elif job["mode"] == Mode.AUTOMATIC.value:
        timeline_status = ArtifactStatus.BLOCKED if validation_issues else ArtifactStatus.CHECKED
    else:
        timeline_status = ArtifactStatus.NEEDS_REVIEW
    artifact = workspace.add_json_artifact(
        job_id,
        language,
        ArtifactKind.TIMELINE,
        timeline,
        timeline_status,
        upstream=upstream,
    )
    for kind, suffix, content in (
        (ArtifactKind.SUBTITLE_SRT, ".srt", render_srt(timeline["captions"])),
        (ArtifactKind.SUBTITLE_VTT, ".vtt", render_vtt(timeline["captions"])),
    ):
        pending = workspace.pending_path(job_id, language, f"subtitle.pending{suffix}")
        pending.write_text(content, encoding="utf-8")
        subtitle_status = (
            ArtifactStatus.BLOCKED
            if timeline_status == ArtifactStatus.BLOCKED
            else ArtifactStatus.CHECKED
            if job["mode"] == Mode.AUTOMATIC.value
            else ArtifactStatus.NEEDS_REVIEW
        )
        workspace.add_file_artifact(
            job_id,
            language,
            kind,
            pending,
            subtitle_status,
            upstream={"timeline": artifact["revision"], "transcript": transcript_artifact["revision"]},
        )
        pending.unlink(missing_ok=True)
    print(artifact["path"])


def _remotion(workspace: Workspace, job_id: str, language: str, action: str) -> int:
    timeline_artifact = require_artifact(workspace, job_id, language, ArtifactKind.TIMELINE)
    timeline = read_artifact_json(workspace, timeline_artifact)
    if not sound.locks_match(workspace, job_id, language, timeline):
        raise RuntimeError("Sound plan or audio assets changed; rebuild timeline and preview")
    audio_artifact = require_artifact(workspace, job_id, language, ArtifactKind.AUDIO)
    job = workspace.get_job(job_id)
    is_v4 = job.get("workflow_version", 2) >= 4
    if job.get("workflow_version", 2) >= 3:
        if is_v4:
            changes = checkpoints.lock_diff(workspace, timeline.get("rendererLock", {}))
            if changes or timeline.get("rendererLock") != checkpoints.current_renderer_lock(workspace, job_id, language, timeline):
                raise RuntimeError("Renderer dependencies changed; rebuild timeline: " + ", ".join(changes))
        elif timeline.get("rendererCodeSha256") != sha256_file(workspace.project_root / "renderer" / "src" / "VidkitShort.tsx"):
            raise RuntimeError("Renderer code changed since timeline compilation; rebuild timeline and preview")
        if timeline.get("rendererPackageLockSha256") != sha256_file(workspace.project_root / "renderer" / "package-lock.json"):
            raise RuntimeError("Renderer dependencies changed since timeline compilation; rebuild timeline and preview")
        if not library.locks_match(workspace, timeline,
                                   visuals.entries(workspace, job_id, language) if is_v4 else None):
            raise RuntimeError("A locked theme, component or effect changed; rebuild timeline and preview")
        if audio_artifact["sha256"] != sha256_file(workspace.resolve_path(audio_artifact)):
            raise RuntimeError("Audio checksum differs from tracked artifact")
    props = prepare_renderer_job(
        workspace, job_id, language, timeline, workspace.resolve_path(audio_artifact)
    )
    entrypoint = visuals.render_entry(workspace, job_id, language, timeline) if is_v4 else None
    checkpoint_revision = None
    if is_v4:
        changes = checkpoints.diff(workspace, job_id, language)
        if changes["checkpoint"] is None or changes["changes"]:
            checkpoint_revision = checkpoints.checkpoint(workspace, job_id, language,
                                                         timeline["rendererLock"])["revision"]
        else:
            checkpoint_revision = changes["checkpoint"]
    if action == "studio":
        output = workspace.job_root(job_id) / "exports" / f"{slugify(job['topic'])}.{language}.studio.mp4"
        return run_studio(workspace.project_root, props, output, entrypoint)
    if timeline.get("missingAssets"):
        raise RuntimeError("Cannot export: required assets are missing")
    if timeline_artifact["status"] == ArtifactStatus.BLOCKED.value:
        raise RuntimeError("Cannot export: timeline has blocking validation issues")
    if job["mode"] == Mode.AUTOMATIC.value and timeline_artifact["status"] not in {
        ArtifactStatus.CHECKED.value,
        ArtifactStatus.APPROVED.value,
    }:
        raise RuntimeError("Automatic export is blocked until timeline checks pass")
    is_v3 = job.get("workflow_version", 2) >= 3
    if is_v3 and action == "render":
        qa = workspace.latest_artifact(job_id, ArtifactKind.QA_REPORT, language)
        if not qa:
            raise RuntimeError("QA report is required before export")
        if any(check["status"] == "fail" for check in read_artifact_json(workspace, qa)["checks"].values()):
            raise RuntimeError("QA failed")
        if job["mode"] == Mode.REVIEW.value and not workflow.current_approval(workspace, job_id, language, "export"):
            raise RuntimeError("Export approval for current preview, QA and timeline is required")
    if is_v3 and action == "preview":
        workspace.invalidate_downstream(job_id, language, ArtifactKind.PREVIEW)
    if is_v3 and action == "render" and not workspace.latest_artifact(job_id, ArtifactKind.PREVIEW, language):
        raise RuntimeError("Preview MP4 is required before export")
    output = workspace.pending_path(job_id, language, "final.pending.mp4")
    code = run_render(workspace.project_root, props, output, entrypoint)
    if code == 0:
        kind = ArtifactKind.PREVIEW if action == "preview" else ArtifactKind.RENDER
        upstream = {"timeline": timeline_artifact["revision"]}
        if kind == ArtifactKind.RENDER:
            preview_artifact = workspace.latest_artifact(job_id, ArtifactKind.PREVIEW, language)
            qa_artifact = workspace.latest_artifact(job_id, ArtifactKind.QA_REPORT, language)
            if preview_artifact:
                upstream["preview"] = preview_artifact["revision"]
            if qa_artifact:
                upstream["qa-report"] = qa_artifact["revision"]
        artifact = workspace.add_file_artifact(
            job_id,
            language,
            kind,
            output,
            ArtifactStatus.NEEDS_REVIEW,
            upstream=upstream,
            metadata={"renderer": "remotion", "format": "1080x1920@30",
                      "theme": timeline.get("theme"), "componentLocks": timeline.get("componentLocks", []),
                      "themeLock": timeline.get("themeLock"), "effectLocks": timeline.get("effectLocks", []),
                      "soundPlanLock": timeline.get("soundPlanLock"),
                      "soundAssets": [{"id": track["asset"]["id"], "sha256": track["asset"]["sha256"]}
                                      for track in timeline.get("soundTracks", [])],
                      "rendererCodeSha256": timeline.get("rendererCodeSha256"),
                      "rendererPackageLockSha256": timeline.get("rendererPackageLockSha256"),
                      "rendererLock": timeline.get("rendererLock"), "checkpointRevision": checkpoint_revision,
                      "claimToScene": timeline.get("claimToScene", {})},
        )
        output.unlink(missing_ok=True)
        print(artifact["path"])
    return code


def _audio_preview(workspace: Workspace, job_id: str, language: str) -> int:
    timeline_artifact = require_artifact(workspace, job_id, language, ArtifactKind.TIMELINE)
    timeline = read_artifact_json(workspace, timeline_artifact)
    if not sound.locks_match(workspace, job_id, language, timeline):
        raise ValueError("Sound plan changed; rebuild timeline")
    audio = require_artifact(workspace, job_id, language, ArtifactKind.AUDIO)
    if sha256_file(workspace.resolve_path(audio)) != audio["sha256"]:
        raise ValueError("Narration checksum mismatch")
    if timeline.get("rendererLock") and (checkpoints.lock_diff(workspace, timeline["rendererLock"])
            or timeline["rendererLock"] != checkpoints.current_renderer_lock(workspace, job_id, language, timeline)):
        raise ValueError("Renderer changed; rebuild timeline")
    props = prepare_renderer_job(workspace, job_id, language, timeline, workspace.resolve_path(audio))
    entry = visuals.render_entry(workspace, job_id, language, timeline) if timeline.get("schemaVersion", 2) >= 4 else Path("src/index.ts")
    output = workspace.pending_path(job_id, language, "mix.pending.wav")
    code = subprocess.run([*remotion_command(workspace.project_root), "render", str(entry), "VidkitShort",
                           str(output), "--props", str(props), "--codec", "wav"],
                          cwd=workspace.project_root / "renderer", check=False).returncode
    if code == 0:
        info = sound.inspect_audio(output)
        artifact = workspace.add_file_artifact(job_id, language, ArtifactKind.AUDIO_MIX, output, ArtifactStatus.NEEDS_REVIEW,
            upstream={"timeline": timeline_artifact["revision"]}, metadata={**info, "soundPlanLock": timeline.get("soundPlanLock"),
            "audioListening": "not-run"})
        output.unlink(missing_ok=True)
        print(artifact["path"])
    return code


def _concept_preview(workspace: Workspace, job_id: str, language: str, selection: str | None) -> int:
    job = workspace.get_job(job_id)
    if job.get("workflow_version", 2) < 4:
        raise ValueError("Concept preview requires workflow v4")
    brief_artifact = require_artifact(workspace, job_id, language, ArtifactKind.BRIEF)
    brief = read_artifact_json(workspace, brief_artifact)
    source_scenes = brief["conceptPreview"]["scenes"]
    selected = set(selection.split(",")) if selection else {
        scene["id"] for scene in source_scenes if scene["role"] in {"hook", "evidence"}
    }
    if not selected or selected - {scene["id"] for scene in source_scenes}:
        raise ValueError("--scenes contains an unknown concept scene")
    import copy
    audio_artifact = workspace.latest_artifact(job_id, ArtifactKind.AUDIO, language)
    audio_path = workspace.resolve_path(audio_artifact) if audio_artifact else None
    if audio_path and sha256_file(audio_path) != audio_artifact["sha256"]:
        raise ValueError("Audio checksum mismatch")
    audio_ms = (audio_duration(audio_path) or 0) * 1000 if audio_path else 0
    scenes = []
    audio_segments = []
    cursor = 0
    for original in source_scenes:
        if original["id"] not in selected:
            continue
        scene = copy.deepcopy(original)
        scene["componentId"] = scene.get("componentId", scene.get("component"))
        duration = scene["endMs"] - scene["startMs"]
        source_start = scene.get("audioStartMs", scene["startMs"])
        if audio_path and 0 <= source_start and source_start + duration <= audio_ms:
            audio_segments.append({"startMs": cursor, "endMs": cursor + duration,
                                   "sourceStartMs": source_start})
        elif audio_path and "audioStartMs" in scene:
            raise ValueError(f"Concept audio range exceeds narration: {scene['id']}")
        scene["startMs"] = cursor
        scene["endMs"] = cursor + duration
        cursor += duration
        scenes.append(scene)
    props_data = {"schemaVersion": 4, "language": language, "title": job["topic"],
                  "audioSrc": "", "theme": brief["theme"], "durationSeconds": cursor / 1000,
                  "captions": [], "scenes": scenes}
    props_data["audioSegments"] = audio_segments
    theme_entry = library.show(workspace, brief["theme"])
    props_data["themeData"] = theme_entry["style"]
    props = prepare_renderer_job(workspace, job_id, language, props_data, audio_path if audio_segments else None)
    entry = visuals.render_entry(workspace, job_id, language, props_data)
    output_dir = workspace.job_dir(job_id, language) / "briefs" / "concept"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"concept.r{brief_artifact['revision']}.mp4"
    code = run_render(workspace.project_root, props, output, entry)
    if code:
        return code
    complete_scenes = copy.deepcopy(source_scenes)
    for scene in complete_scenes:
        scene["componentId"] = scene.get("componentId", scene.get("component"))
    complete = {**props_data, "scenes": complete_scenes,
                "durationSeconds": max(scene["endMs"] for scene in source_scenes) / 1000}
    complete_props = prepare_renderer_job(workspace, job_id, language, complete, None)
    complete_entry = visuals.render_entry(workspace, job_id, language, complete)
    frames = {}
    for role in ("hook", "evidence", "takeaway"):
        scene = next(item for item in source_scenes if item["role"] == role)
        frame = max(0, round((scene["startMs"] + scene["endMs"]) / 2000 * 30))
        target = output_dir / f"{role}.r{brief_artifact['revision']}.png"
        still = [*remotion_command(workspace.project_root), "still", str(complete_entry),
                 "VidkitShort", str(target), "--props", str(complete_props), "--frame", str(frame),
                 "--overwrite"]
        code = subprocess.run(still, cwd=workspace.project_root / "renderer", check=False).returncode
        if code:
            return code
        frames[role] = target.relative_to(workspace.workspace_root).as_posix()
    metadata = {"briefRevision": brief_artifact["revision"], "briefSha256": brief_artifact["sha256"],
                "selectedScenes": [scene["id"] for scene in scenes], "provisionalTiming": True,
                "preview": output.relative_to(workspace.workspace_root).as_posix(),
                "sha256": sha256_file(output), "frames": frames}
    metadata["audioReuse"] = {"revision": audio_artifact["revision"] if audio_segments else None,
                              "sha256": audio_artifact["sha256"] if audio_segments else None,
                              "segments": audio_segments,
                              "silentSceneIds": [scene["id"] for scene in scenes
                                  if not any(segment["startMs"] == scene["startMs"] for segment in audio_segments)]}
    metadata["rendererLock"] = checkpoints.current_renderer_lock(workspace, job_id, language, complete)
    metadata["themeLock"] = {"id": theme_entry["id"], "version": theme_entry["version"],
                             "sha256": theme_entry["sha256"]}
    (output_dir / f"concept.r{brief_artifact['revision']}.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)
    return 0


def _add_feedback(workspace: Workspace, job_id: str, language: str, source: Path) -> None:
    from datetime import UTC, datetime
    data = load_json(source)
    timeline = require_artifact(workspace, job_id, language, ArtifactKind.TIMELINE)
    preview = workspace.latest_artifact(job_id, ArtifactKind.PREVIEW, language)
    scene_ids = {scene["id"] for scene in read_artifact_json(workspace, timeline).get("scenes", [])}
    observations = data.get("observations")
    if not isinstance(observations, list) or not observations:
        raise ValueError("Feedback needs observations")
    for item in observations:
        if item.get("sceneId") not in scene_ids or item.get("scope") not in {"video", "general-proposal"}:
            raise ValueError("Feedback needs valid sceneId and video/general-proposal scope")
        if item.get("category") not in {"layout", "explanation", "timing", "visual", "caption", "transition"}:
            raise ValueError("Feedback category is invalid")
        if not item.get("observation"):
            raise ValueError("Feedback observation is required")
    minutes = data.get("reviewMinutes")
    if minutes is not None and (not isinstance(minutes, (int, float)) or minutes < 0):
        raise ValueError("reviewMinutes must be nonnegative")
    root = workspace.job_dir(job_id, language) / "feedback"
    root.mkdir(parents=True, exist_ok=True)
    revision = len(list(root.glob("feedback.r*.json"))) + 1
    record = {"timelineRevision": timeline["revision"], "timelineSha256": timeline["sha256"],
              "previewRevision": preview["revision"] if preview else None,
              "createdAt": datetime.now(UTC).isoformat(), "observations": observations,
              "reviewMinutes": minutes}
    output = root / f"feedback.r{revision}.json"
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(output)


def _metrics(workspace: Workspace, job_id: str, language: str) -> None:
    workspace.get_job(job_id)
    root = workspace.job_dir(job_id, language) / "feedback"
    feedback = [json.loads(path.read_text(encoding="utf-8")) for path in root.glob("feedback.r*.json")]
    revisions = workspace.list_artifacts(job_id)
    previews = [item for item in revisions if item["kind"] == ArtifactKind.PREVIEW.value
                and item["language"] == language]
    observations = [item for record in feedback for item in record["observations"]]
    report = {"jobId": job_id, "language": language, "previewRounds": len(previews),
              "manualRevisionRequests": len([item for item in observations if item["scope"] == "video"]),
              "reviewMinutesRecorded": sum(record.get("reviewMinutes") or 0 for record in feedback),
              "reviewsWithoutTime": sum(record.get("reviewMinutes") is None for record in feedback),
              "revisionRequestsByCategory": {category: sum(item["category"] == category for item in observations)
                                              for category in ("layout", "explanation", "timing", "visual", "caption", "transition")}}
    print(json.dumps(report, ensure_ascii=False, indent=2))


def _import_render(workspace: Workspace, job_id: str, language: str, file: Path) -> None:
    timeline = require_artifact(workspace, job_id, language, ArtifactKind.TIMELINE)
    is_v3 = workspace.get_job(job_id).get("workflow_version", 2) >= 3
    if is_v3:
        workspace.invalidate_downstream(job_id, language, ArtifactKind.PREVIEW)
    artifact = workspace.add_file_artifact(
        job_id,
        language,
        ArtifactKind.PREVIEW if is_v3 else ArtifactKind.RENDER,
        file,
        ArtifactStatus.NEEDS_REVIEW,
        upstream={"timeline": timeline["revision"]},
        metadata={"renderer": "remotion-studio", "imported": True, "source_sha256": sha256_file(file)},
    )
    print(artifact["path"])


if __name__ == "__main__":
    raise SystemExit(main())
