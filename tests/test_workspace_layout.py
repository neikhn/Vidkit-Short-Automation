import json
import tempfile
import unittest
from pathlib import Path

from vidkit.checkpoints import checkpoint, diff, renderer_lock
from vidkit.models import ArtifactKind, ArtifactStatus
from vidkit.storage import Workspace, sha256_file
from vidkit.workspace_layout import audit, migrate


class WorkspaceLayoutTests(unittest.TestCase):
    def test_new_job_uses_grouped_paths_and_checkpoint_objects(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory))
            job = workspace.create_job("Demo", ["vi"])
            script = workspace.add_json_artifact(job, "vi", ArtifactKind.SCRIPT,
                                                 {"text": "Xin chào"}, ArtifactStatus.CHECKED)
            self.assertIn("/vi/writing/scripts/", script["path"])
            saved = checkpoint(workspace, job, "vi", {})
            record = next(item for item in saved["files"] if item["path"].endswith("script.r1.json"))
            blob = workspace.objects_root / record["sha256"][:2] / record["sha256"]
            self.assertEqual(sha256_file(blob), record["sha256"])
            self.assertEqual(diff(workspace, job, "vi")["changes"], [])

    def test_copy_migration_keeps_revisions_and_old_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory))
            job = workspace.create_job("Legacy", ["en"])
            with workspace.connect() as conn:
                conn.execute("UPDATE jobs SET storage_layout_version = 1 WHERE id = ?", (job,))
            workspace._ensure_job_tree(job)
            script = workspace.add_json_artifact(job, "en", ArtifactKind.SCRIPT,
                                                 {"text": "One"}, ArtifactStatus.CHECKED)
            old_path = workspace.resolve_path(script)
            old_hash = script["sha256"]
            checkpoint(workspace, job, "en", {})
            source = workspace.workspace_root / "notes.txt"
            source.write_text("manual", encoding="utf-8")
            self.assertEqual(audit(workspace, hashes=True)["problems"], [])
            self.assertEqual(migrate(workspace)["mode"], "dry-run")
            result = migrate(workspace, apply=True)
            self.assertIn(job, result["migrated"])
            current = workspace.latest_artifact(job, ArtifactKind.SCRIPT, "en")
            self.assertIn("/en/writing/scripts/", current["path"])
            self.assertEqual(current["revision"], script["revision"])
            self.assertEqual(sha256_file(workspace.resolve_path(current)), old_hash)
            self.assertEqual(workspace.resolve_path(script), workspace.resolve_path(current))
            self.assertEqual(sha256_file(old_path), old_hash)
            self.assertEqual(diff(workspace, job, "en")["changes"], [])
            self.assertTrue((workspace.workbench_root / "inbox/notes.txt").is_file())
            self.assertEqual(migrate(workspace, apply=True)["migrated"], {})

    def test_renderer_lock_scopes_staged_media_to_own_job(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = Workspace(root)
            source = root / "renderer/src/VidkitShort.tsx"
            source.parent.mkdir(parents=True)
            source.write_text("import './SoundTracks';", encoding="utf-8")
            sound = source.parent / "SoundTracks.tsx"
            sound.write_text("staticFile('jobs/own/en/a.wav'); staticFile('jobs/other/en/b.wav');",
                             encoding="utf-8")
            for name in ("own/en/a.wav", "other/en/b.wav"):
                path = root / "renderer/public/jobs" / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"audio")
            locked = renderer_lock(workspace, job_id="own")
            self.assertTrue(any("own/en/a.wav" in path for path in locked))
            self.assertFalse(any("other/en/b.wav" in path for path in locked))


if __name__ == "__main__":
    unittest.main()
