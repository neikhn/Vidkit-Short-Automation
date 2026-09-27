from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import unicodedata
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable, Iterator

from .models import ArtifactKind, ArtifactStatus, Mode


STAGE_ORDER = [kind.value for kind in ArtifactKind]
SHARED_KINDS = {ArtifactKind.SOURCE, ArtifactKind.ASSET_MANIFEST, ArtifactKind.SOUND_ASSETS}
KIND_DIRECTORIES = {
    ArtifactKind.SOURCE: "sources",
    ArtifactKind.ASSET_MANIFEST: "assets",
    ArtifactKind.SCRIPT: "scripts",
    ArtifactKind.BRIEF: "briefs",
    ArtifactKind.AUDIO: "audio",
    ArtifactKind.TRANSCRIPT: "transcripts",
    ArtifactKind.STORYBOARD: "storyboard",
    ArtifactKind.CAPTION_PLAN: "subtitles",
    ArtifactKind.SOUND_PLAN: "audio/sound-plan",
    ArtifactKind.SOUND_ASSETS: "audio-assets",
    ArtifactKind.AUDIO_MIX: "audio/mix",
    ArtifactKind.TIMELINE: "storyboard",
    ArtifactKind.SUBTITLE_SRT: "subtitles",
    ArtifactKind.SUBTITLE_VTT: "subtitles",
    ArtifactKind.PREVIEW: "previews",
    ArtifactKind.QA_REPORT: "qa",
    ArtifactKind.APPROVAL: "approvals",
    ArtifactKind.RENDER: "exports",
    ArtifactKind.PUBLICATION: "exports",
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def slugify(value: str, max_length: int = 48) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = "".join(char if char.isalnum() else "-" for char in ascii_text)
    slug = "-".join(part for part in slug.split("-") if part)
    return (slug or "video")[:max_length].rstrip("-")


class Workspace:
    def __init__(self, project_root: Path):
        self.project_root = project_root.resolve()
        self.workspace_root = self.project_root / "workspace"
        self.state_root = self.workspace_root
        self.db_path = self.workspace_root / "workspace.sqlite3"
        self.videos_root = self.workspace_root / "videos"
        self.cache_root = self.workspace_root / "cache"
        self.legacy_root = self.project_root / ".vidkit"

    def initialize(self) -> None:
        self.videos_root.mkdir(parents=True, exist_ok=True)
        self.cache_root.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(
                """
                PRAGMA journal_mode=WAL;
                PRAGMA foreign_keys=ON;
                CREATE TABLE IF NOT EXISTS jobs (
                  id TEXT PRIMARY KEY,
                  topic TEXT NOT NULL,
                  source_url TEXT,
                  mode TEXT NOT NULL,
                  languages_json TEXT NOT NULL,
                  status TEXT NOT NULL,
                  folder_name TEXT NOT NULL UNIQUE,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS artifacts (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  job_id TEXT NOT NULL REFERENCES jobs(id),
                  language TEXT,
                  kind TEXT NOT NULL,
                  revision INTEGER NOT NULL,
                  status TEXT NOT NULL,
                  path TEXT NOT NULL,
                  sha256 TEXT NOT NULL,
                  upstream_json TEXT NOT NULL,
                  metadata_json TEXT NOT NULL,
                  created_at TEXT NOT NULL,
                  UNIQUE(job_id, language, kind, revision)
                );
                CREATE INDEX IF NOT EXISTS idx_artifact_latest
                  ON artifacts(job_id, language, kind, revision DESC);
                CREATE TABLE IF NOT EXISTS workspace_meta (
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL
                );
                INSERT OR REPLACE INTO workspace_meta(key, value) VALUES ('schema_version', '3');
                """
            )
            columns = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)")}
            if "workflow_version" not in columns:
                conn.execute("ALTER TABLE jobs ADD COLUMN workflow_version INTEGER NOT NULL DEFAULT 2")

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def create_job(
        self,
        topic: str,
        languages: Iterable[str],
        mode: Mode = Mode.REVIEW,
        source_url: str | None = None,
        workflow_version: int = 4,
    ) -> str:
        self.initialize()
        job_id = uuid.uuid4().hex[:12]
        now = utc_now()
        normalized_languages = list(dict.fromkeys(lang.strip() for lang in languages if lang.strip()))
        if not normalized_languages:
            raise ValueError("At least one language is required")
        folder_name = self._folder_name(job_id, topic, now)
        with self.connect() as conn:
            conn.execute(
                "INSERT INTO jobs (id, topic, source_url, mode, languages_json, status, folder_name, created_at, updated_at, workflow_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    job_id,
                    topic,
                    source_url,
                    mode.value,
                    json.dumps(normalized_languages, ensure_ascii=False),
                    "prepared",
                    folder_name,
                    now,
                    now,
                    workflow_version,
                ),
            )
        self._ensure_job_tree(job_id)
        self.update_project_manifest(job_id)
        return job_id

    def get_job(self, job_id: str) -> dict[str, Any]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown job: {job_id}")
        result = dict(row)
        result["languages"] = json.loads(result.pop("languages_json"))
        result["directory"] = f"videos/{result['folder_name']}"
        return result

    def list_jobs(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
        jobs = []
        for row in rows:
            job = dict(row)
            job["languages"] = json.loads(job.pop("languages_json"))
            job["directory"] = f"videos/{job['folder_name']}"
            jobs.append(job)
        return jobs

    def rename_job(self, job_id: str, topic: str) -> dict[str, Any]:
        topic = topic.strip()
        if not topic:
            raise ValueError("Title cannot be empty")
        with self.connect() as conn:
            updated = conn.execute(
                "UPDATE jobs SET topic = ?, updated_at = ? WHERE id = ?",
                (topic, utc_now(), job_id),
            ).rowcount
        if not updated:
            raise KeyError(f"Unknown job: {job_id}")
        self.update_project_manifest(job_id)
        return self.get_job(job_id)

    def job_root(self, job_id: str) -> Path:
        job = self.get_job(job_id)
        return self.videos_root / job["folder_name"]

    def job_dir(self, job_id: str, language: str | None = None) -> Path:
        target = self.job_root(job_id)
        if language:
            target /= language
        target.mkdir(parents=True, exist_ok=True)
        return target

    def pending_path(self, job_id: str, language: str | None, filename: str) -> Path:
        target = self.cache_root / "jobs" / job_id
        if language:
            target /= language
        target.mkdir(parents=True, exist_ok=True)
        return target / filename

    def asset_dir(self, job_id: str) -> Path:
        target = self.job_root(job_id) / "assets" / "files"
        target.mkdir(parents=True, exist_ok=True)
        return target

    def resolve_path(self, artifact_or_path: dict[str, Any] | str) -> Path:
        value = artifact_or_path["path"] if isinstance(artifact_or_path, dict) else artifact_or_path
        return (self.workspace_root / value).resolve()

    def latest_artifact(
        self,
        job_id: str,
        kind: ArtifactKind | str,
        language: str | None,
        include_invalidated: bool = False,
    ) -> dict[str, Any] | None:
        kind_value = kind.value if isinstance(kind, ArtifactKind) else kind
        invalidated_filter = "" if include_invalidated else "AND status != 'invalidated'"
        query = f"""
            SELECT * FROM artifacts
            WHERE job_id = ? AND kind = ? AND language IS ? {invalidated_filter}
            ORDER BY revision DESC LIMIT 1
        """
        with self.connect() as conn:
            row = conn.execute(query, (job_id, kind_value, language)).fetchone()
        return self._decode_artifact(row) if row else None

    def list_artifacts(self, job_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM artifacts WHERE job_id = ? ORDER BY language, kind, revision",
                (job_id,),
            ).fetchall()
        return [self._decode_artifact(row) for row in rows]

    def add_json_artifact(
        self,
        job_id: str,
        language: str | None,
        kind: ArtifactKind,
        payload: dict[str, Any],
        status: ArtifactStatus,
        upstream: dict[str, int] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.get_job(job_id)
        revision = self._next_revision(job_id, language, kind)
        output = self._artifact_output(job_id, language, kind, revision, ".json")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return self._record_artifact(
            job_id, language, kind, revision, status, output, upstream, metadata
        )

    def add_file_artifact(
        self,
        job_id: str,
        language: str | None,
        kind: ArtifactKind,
        source: Path,
        status: ArtifactStatus,
        upstream: dict[str, int] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.get_job(job_id)
        source = source.resolve()
        if not source.is_file():
            raise FileNotFoundError(source)
        revision = self._next_revision(job_id, language, kind)
        output = self._artifact_output(job_id, language, kind, revision, source.suffix.lower())
        output.parent.mkdir(parents=True, exist_ok=True)
        if source != output.resolve():
            shutil.copy2(source, output)
        return self._record_artifact(
            job_id, language, kind, revision, status, output, upstream, metadata
        )

    def invalidate_downstream(self, job_id: str, language: str, changed_kind: ArtifactKind) -> None:
        if changed_kind in {ArtifactKind.BRIEF, ArtifactKind.CAPTION_PLAN, ArtifactKind.STORYBOARD,
                            ArtifactKind.SOUND_PLAN, ArtifactKind.SOUND_ASSETS}:
            downstream = [kind.value for kind in (
                ArtifactKind.TIMELINE, ArtifactKind.SUBTITLE_SRT, ArtifactKind.SUBTITLE_VTT,
                ArtifactKind.AUDIO_MIX, ArtifactKind.PREVIEW, ArtifactKind.QA_REPORT, ArtifactKind.RENDER,
            )]
        else:
            index = STAGE_ORDER.index(changed_kind.value)
            downstream = [kind for kind in STAGE_ORDER[index + 1 :]
                          if kind not in {ArtifactKind.APPROVAL.value, ArtifactKind.SOUND_ASSETS.value,
                                          ArtifactKind.SOUND_PLAN.value}]
        if not downstream:
            return
        placeholders = ",".join("?" for _ in downstream)
        with self.connect() as conn:
            conn.execute(
                f"""
                UPDATE artifacts SET status = 'invalidated'
                WHERE job_id = ? AND language IS ? AND kind IN ({placeholders})
                  AND status != 'published'
                """,
                (job_id, language, *downstream),
            )
            conn.execute("UPDATE jobs SET updated_at = ? WHERE id = ?", (utc_now(), job_id))
            if changed_kind in {ArtifactKind.SOURCE, ArtifactKind.SCRIPT, ArtifactKind.BRIEF}:
                approval_stages = ("concept", "export")
            elif changed_kind in {ArtifactKind.AUDIO, ArtifactKind.TRANSCRIPT,
                                  ArtifactKind.ASSET_MANIFEST, ArtifactKind.STORYBOARD,
                                  ArtifactKind.CAPTION_PLAN, ArtifactKind.TIMELINE,
                                  ArtifactKind.SOUND_PLAN, ArtifactKind.SOUND_ASSETS,
                                  ArtifactKind.PREVIEW, ArtifactKind.QA_REPORT}:
                approval_stages = ("export",)
            else:
                approval_stages = ()
            if approval_stages:
                stage_placeholders = ",".join("?" for _ in approval_stages)
                conn.execute(
                    "UPDATE artifacts SET status = 'invalidated' WHERE job_id = ? AND language IS ? "
                    f"AND kind = 'approval' AND json_extract(metadata_json, '$.stage') IN ({stage_placeholders})",
                    (job_id, language, *approval_stages),
                )
        self.update_project_manifest(job_id)

    def invalidate_visuals(self, job_id: str) -> None:
        kinds = [
            ArtifactKind.TIMELINE.value,
            ArtifactKind.SUBTITLE_SRT.value,
            ArtifactKind.SUBTITLE_VTT.value,
            ArtifactKind.RENDER.value,
            ArtifactKind.PREVIEW.value,
            ArtifactKind.QA_REPORT.value,
            ArtifactKind.PUBLICATION.value,
        ]
        placeholders = ",".join("?" for _ in kinds)
        with self.connect() as conn:
            conn.execute(
                f"UPDATE artifacts SET status = 'invalidated' "
                f"WHERE job_id = ? AND kind IN ({placeholders}) AND status != 'published'",
                (job_id, *kinds),
            )
            conn.execute("UPDATE jobs SET updated_at = ? WHERE id = ?", (utc_now(), job_id))
            conn.execute(
                "UPDATE artifacts SET status = 'invalidated' WHERE job_id = ? AND kind = 'approval' "
                "AND json_extract(metadata_json, '$.stage') = 'export'",
                (job_id,),
            )
        self.update_project_manifest(job_id)

    def migrate_legacy(self) -> dict[str, int]:
        legacy_db = self.legacy_root / "vidkit.sqlite3"
        if not legacy_db.is_file():
            return {"jobs": 0, "artifacts": 0, "skipped_jobs": 0}
        self.initialize()
        old = sqlite3.connect(legacy_db)
        old.row_factory = sqlite3.Row
        migrated_jobs = 0
        migrated_artifacts = 0
        skipped_jobs = 0
        try:
            legacy_jobs = old.execute("SELECT * FROM jobs ORDER BY created_at").fetchall()
            for row in legacy_jobs:
                job_id = row["id"]
                with self.connect() as conn:
                    exists = conn.execute("SELECT 1 FROM jobs WHERE id = ?", (job_id,)).fetchone()
                if exists:
                    skipped_jobs += 1
                else:
                    folder_name = self._folder_name(job_id, row["topic"], row["created_at"])
                    with self.connect() as conn:
                        conn.execute(
                            "INSERT INTO jobs (id, topic, source_url, mode, languages_json, status, folder_name, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            (
                                job_id,
                                row["topic"],
                                row["source_url"],
                                row["mode"],
                                row["languages_json"],
                                row["status"],
                                folder_name,
                                row["created_at"],
                                row["updated_at"],
                            ),
                        )
                    migrated_jobs += 1
                self._ensure_job_tree(job_id)
                rows = old.execute(
                    "SELECT * FROM artifacts WHERE job_id = ? ORDER BY id", (job_id,)
                ).fetchall()
                for artifact_row in rows:
                    source = (self.project_root / artifact_row["path"]).resolve()
                    if not source.is_relative_to(self.legacy_root.resolve()):
                        raise ValueError(f"Legacy artifact is outside .vidkit: {source}")
                    if not source.is_file():
                        raise FileNotFoundError(f"Legacy artifact is missing: {source}")
                    actual_hash = sha256_file(source)
                    if actual_hash != artifact_row["sha256"]:
                        raise ValueError(f"Legacy checksum mismatch: {source}")
                    with self.connect() as conn:
                        existing_artifact = conn.execute(
                            "SELECT * FROM artifacts WHERE job_id = ? AND language IS ? "
                            "AND kind = ? AND revision = ?",
                            (
                                job_id,
                                artifact_row["language"],
                                artifact_row["kind"],
                                artifact_row["revision"],
                            ),
                        ).fetchone()
                    kind = ArtifactKind(artifact_row["kind"])
                    target = self._artifact_output(
                        job_id,
                        artifact_row["language"],
                        kind,
                        artifact_row["revision"],
                        source.suffix.lower(),
                    )
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if existing_artifact:
                        recorded_hash = existing_artifact["sha256"]
                        if recorded_hash != actual_hash:
                            raise ValueError(f"Migrated checksum mismatch: {target}")
                        if not target.exists():
                            shutil.copy2(source, target)
                        if sha256_file(target) != actual_hash:
                            raise ValueError(f"Migration target checksum mismatch: {target}")
                        continue
                    if target.exists() and sha256_file(target) != actual_hash:
                        raise ValueError(f"Migration target checksum mismatch: {target}")
                    if not target.exists():
                        shutil.copy2(source, target)
                    relative = target.relative_to(self.workspace_root).as_posix()
                    with self.connect() as conn:
                        conn.execute(
                            """
                            INSERT INTO artifacts
                            (job_id, language, kind, revision, status, path, sha256,
                             upstream_json, metadata_json, created_at)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                job_id,
                                artifact_row["language"],
                                artifact_row["kind"],
                                artifact_row["revision"],
                                artifact_row["status"],
                                relative,
                                actual_hash,
                                artifact_row["upstream_json"],
                                artifact_row["metadata_json"],
                                artifact_row["created_at"],
                            ),
                        )
                    migrated_artifacts += 1
                self.update_project_manifest(job_id)
        finally:
            old.close()
        return {
            "jobs": migrated_jobs,
            "artifacts": migrated_artifacts,
            "skipped_jobs": skipped_jobs,
        }

    def update_project_manifest(self, job_id: str) -> None:
        job = self.get_job(job_id)
        artifacts = self.list_artifacts(job_id)
        latest: dict[str, dict[str, Any]] = {}
        for artifact in artifacts:
            key = f"{artifact['language'] or 'shared'}:{artifact['kind']}"
            latest[key] = {
                "revision": artifact["revision"],
                "status": artifact["status"],
                "path": artifact["path"],
                "sha256": artifact["sha256"],
            }
        payload = {
            "schemaVersion": 2,
            "id": job["id"],
            "title": job["topic"],
            "sourceUrl": job["source_url"],
            "mode": job["mode"],
            "workflowVersion": job["workflow_version"],
            "languages": job["languages"],
            "status": job["status"],
            "directory": job["directory"],
            "createdAt": job["created_at"],
            "updatedAt": job["updated_at"],
            "latestArtifacts": latest,
        }
        path = self.job_root(job_id) / "project.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _next_revision(self, job_id: str, language: str | None, kind: ArtifactKind) -> int:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT COALESCE(MAX(revision), 0) + 1 AS revision FROM artifacts "
                "WHERE job_id = ? AND language IS ? AND kind = ?",
                (job_id, language, kind.value),
            ).fetchone()
        return int(row["revision"])

    def _record_artifact(
        self,
        job_id: str,
        language: str | None,
        kind: ArtifactKind,
        revision: int,
        status: ArtifactStatus,
        path: Path,
        upstream: dict[str, int] | None,
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        now = utc_now()
        rel_path = path.resolve().relative_to(self.workspace_root).as_posix()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO artifacts
                (job_id, language, kind, revision, status, path, sha256,
                 upstream_json, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    language,
                    kind.value,
                    revision,
                    status.value,
                    rel_path,
                    sha256_file(path),
                    json.dumps(upstream or {}, ensure_ascii=False),
                    json.dumps(metadata or {}, ensure_ascii=False),
                    now,
                ),
            )
            conn.execute(
                "UPDATE jobs SET status = ?, updated_at = ? WHERE id = ?",
                (status.value, now, job_id),
            )
            row = conn.execute("SELECT * FROM artifacts WHERE id = last_insert_rowid()").fetchone()
        self.update_project_manifest(job_id)
        return self._decode_artifact(row)

    def _artifact_output(
        self,
        job_id: str,
        language: str | None,
        kind: ArtifactKind,
        revision: int,
        suffix: str,
    ) -> Path:
        job = self.get_job(job_id)
        root = self.videos_root / job["folder_name"]
        if kind in {ArtifactKind.RENDER, ArtifactKind.PUBLICATION, ArtifactKind.PREVIEW}:
            lang = language or "shared"
            filename = f"{slugify(job['topic'])}.{lang}.r{revision}{suffix}"
            return root / KIND_DIRECTORIES[kind] / filename
        if kind in SHARED_KINDS:
            directory = root / KIND_DIRECTORIES[kind]
        else:
            if not language:
                raise ValueError(f"Language is required for {kind.value}")
            directory = root / language / KIND_DIRECTORIES[kind]
        return directory / f"{kind.value}.r{revision}{suffix}"

    def _ensure_job_tree(self, job_id: str) -> None:
        job = self.get_job(job_id)
        root = self.videos_root / job["folder_name"]
        for shared in ("sources", "assets", "previews", "exports"):
            (root / shared).mkdir(parents=True, exist_ok=True)
        for language in job["languages"]:
            for folder in ("scripts", "briefs", "audio", "transcripts", "storyboard", "subtitles", "qa", "approvals"):
                (root / language / folder).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _folder_name(job_id: str, topic: str, created_at: str) -> str:
        date = created_at[:10] if len(created_at) >= 10 else datetime.now(UTC).date().isoformat()
        return f"{date}_{slugify(topic)}_{job_id}"

    @staticmethod
    def _decode_artifact(row: sqlite3.Row) -> dict[str, Any]:
        result = dict(row)
        result["upstream"] = json.loads(result.pop("upstream_json"))
        result["metadata"] = json.loads(result.pop("metadata_json"))
        return result
