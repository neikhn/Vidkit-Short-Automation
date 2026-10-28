import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from vidkit import library
from vidkit.models import ArtifactKind as K, ArtifactStatus as S
from vidkit.storage import Workspace
from vidkit.timeline import compile_storyboard, validate_storyboard_shape
from vidkit.visuals import render_entry
from vidkit.workflow import add_brief


ROOT = Path(__file__).resolve().parents[1]


class BackgroundTests(unittest.TestCase):
    def test_five_builtins_have_two_loop_fixtures_and_source_locks(self):
        workspace = Workspace(ROOT)
        backgrounds = library.search(workspace, kind="background")
        self.assertEqual({item["id"] for item in backgrounds}, {
            "grid-drift", "contour-flow", "light-editorial-loop", "radial-glow", "fireflies"})
        for item in backgrounds:
            fixture = json.loads((ROOT / "renderer/library" / item["preview"]).read_text(encoding="utf-8"))
            self.assertEqual(fixture["backgroundId"], item["id"])
            self.assertGreaterEqual(fixture["durationSeconds"], 2 * item["loopSeconds"])
            self.assertTrue(all(item["sourceChecksums"].values()))
            self.assertTrue(library.locks_match(workspace, {"backgroundLock": {
                "id": item["id"], "version": item["version"], "sha256": item["sha256"]}}))

    def test_v7_timeline_locks_background_and_legacy_timeline_does_not(self):
        entries = library.entries(Workspace(ROOT))
        words = [{"text": "Hello", "start": 0, "end": 1}]
        board = {"schemaVersion": 4, "theme": "dark-grid", "backgroundId": "grid-drift",
                 "scenes": [{"id": "one", "layout": "takeaway", "title": "Hello",
                             "development": {"understanding": "One claim", "object": "Card",
                                             "action": "Reveal", "result": "Readable text", "connection": "End"},
                             "startAnchor": {"wordIndex": 0}, "endAnchor": {"wordIndex": 0}}]}
        transcript = {"words": words, "durationSeconds": 1}
        self.assertEqual(validate_storyboard_shape(board, require_background=True), [])
        result, missing = compile_storyboard(transcript, board, {"assets": []}, "Topic", "en", "audio.wav",
                                             library_entries=entries, require_background=True)
        self.assertEqual(missing, [])
        self.assertEqual(result["backgroundId"], "grid-drift")
        self.assertEqual(result["backgroundLoopSeconds"], 8)
        self.assertTrue(library.locks_match(Workspace(ROOT), result))
        old, _ = compile_storyboard(transcript, board, {"assets": []}, "Topic", "en", "audio.wav",
                                    library_entries=entries)
        self.assertNotIn("backgroundId", old)
        with self.assertRaisesRegex(ValueError, "Unknown background"):
            compile_storyboard(transcript, {**board, "backgroundId": "missing"}, {"assets": []},
                               "Topic", "en", "audio.wav", library_entries=entries, require_background=True)
        candidate = {**next(item for item in entries if item["id"] == "grid-drift"),
                     "status": "candidate", "previewValid": False}
        with self.assertRaisesRegex(ValueError, "rendered motion preview"):
            compile_storyboard(transcript, board, {"assets": []}, "Topic", "en", "audio.wav",
                               library_entries=[item for item in entries if item["id"] != "grid-drift"] + [candidate],
                               require_background=True)

    def test_background_candidate_requires_preview_then_promotes_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = root / "renderer/library"
            catalog.mkdir(parents=True)
            (catalog / "manifest.json").write_text('{"components":[],"themes":[],"backgrounds":[]}', encoding="utf-8")
            workspace = Workspace(root)
            workspace.initialize()
            package = root / "candidate"
            package.mkdir()
            (package / "Loop.tsx").write_text("export default function Loop(){return null;}", encoding="utf-8")
            fixture = {"schemaVersion": 4, "durationSeconds": 8, "backgroundId": "test-loop",
                       "backgroundLoopSeconds": 4, "scenes": [{"id": "one", "layout": "takeaway",
                       "startMs": 0, "endMs": 8000}]}
            (package / "fixture.json").write_text(json.dumps(fixture), encoding="utf-8")
            manifest = {"id": "test-loop", "version": "1.0.0", "kind": "background", "description": "Test",
                        "tags": ["test"], "useCases": ["test"], "limitations": [], "propsSchema": {},
                        "source": "test", "license": "MIT", "preview": "fixture.json",
                        "entrypoint": "Loop.tsx", "loopSeconds": 4}
            source = package / "manifest.json"
            source.write_text(json.dumps(manifest), encoding="utf-8")
            library.add_candidate(workspace, source)
            with self.assertRaisesRegex(ValueError, "preview is missing or stale"):
                library.approve(workspace, "test-loop", "Reviewer")

            def fake_render(command, **_kwargs):
                output = Path(command[4])
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(b"rendered")
                return SimpleNamespace(returncode=0)

            with patch("vidkit.render.remotion_command", return_value=["remotion"]), \
                 patch("vidkit.library.subprocess.run", side_effect=fake_render):
                library.preview(workspace, "test-loop")
            self.assertTrue(library.show(workspace, "test-loop")["previewValid"])
            approved = library.approve(workspace, "test-loop", "Reviewer")
            self.assertTrue(Path(approved["approvedManifest"]).is_file())
            self.assertTrue((catalog / "approved/code/test-loop-1-0-0/Loop.tsx").is_file())
            self.assertEqual(library.show(workspace, "test-loop")["status"], "approved")

    def test_render_entry_uses_the_locked_background_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = Workspace(root)
            old = root / "old.tsx"
            new = root / "new.tsx"
            old.write_text("export default () => null", encoding="utf-8")
            new.write_text("export default () => null", encoding="utf-8")
            candidates = [
                {"id": "shared", "kind": "background", "version": "1.0.0", "sha256": "old",
                 "entrypoint": "old.tsx", "entrypointAbsolute": str(old)},
                {"id": "shared", "kind": "background", "version": "2.0.0", "sha256": "new",
                 "entrypoint": "new.tsx", "entrypointAbsolute": str(new)},
            ]
            path = render_entry(workspace, "job", "en", {"scenes": [], "backgroundId": "shared",
                               "backgroundLock": {"id": "shared", "version": "1.0.0", "sha256": "old"}},
                                supplied_entries=candidates)
            generated = path.read_text(encoding="utf-8")
            self.assertIn("old.tsx", generated)
            self.assertNotIn("new.tsx", generated)

    def test_changing_background_requires_new_concept_but_keeps_voice_and_transcript(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            catalog = root / "renderer/library"
            catalog.mkdir(parents=True)
            shutil.copy2(ROOT / "renderer/library/manifest.json", catalog / "manifest.json")
            workspace = Workspace(root)
            job = workspace.create_job("Background choice", ["en"], workflow_version=7)
            workspace.add_json_artifact(job, "en", K.SCRIPT,
                                        {"cta": {"commentQuestion": "What next?"}}, S.CHECKED)
            roles = ("hook", "evidence", "takeaway", "cta")
            brief = {"angle": "Explain", "theme": "dark-grid", "backgroundId": "grid-drift",
                     "hook": "Why?", "visualStrategy": "Show one result",
                     "beats": [{"id": "beat", "approach": "reuse", "development": {
                         "understanding": "Claim", "object": "Card", "action": "Reveal",
                         "result": "Visible", "connection": "Next"}}],
                     "explanationAlternatives": ["card", "diagram"], "chosenExplanation": "card",
                     "conceptPreview": {"scenes": [{"id": role, "role": role, "component": "takeaway",
                         "title": "What next?", "body": "Follow", "startMs": index * 1000,
                         "endMs": (index + 1) * 1000} for index, role in enumerate(roles)]}}
            source = root / "brief.json"
            source.write_text(json.dumps(brief), encoding="utf-8")
            add_brief(workspace, job, "en", source)
            audio = root / "audio.mp3"
            audio.write_bytes(b"voice")
            workspace.add_file_artifact(job, "en", K.AUDIO, audio, S.CHECKED)
            workspace.add_json_artifact(job, "en", K.TRANSCRIPT, {"words": []}, S.CHECKED,
                                        metadata={"variant": "normalized"})
            workspace.add_json_artifact(job, "en", K.STORYBOARD, {"backgroundId": "grid-drift"}, S.CHECKED)
            workspace.add_json_artifact(job, "en", K.TIMELINE, {"backgroundId": "grid-drift"}, S.CHECKED)
            workspace.add_json_artifact(job, "en", K.APPROVAL, {"stage": "concept"}, S.APPROVED,
                                        metadata={"stage": "concept"})
            brief["backgroundId"] = "contour-flow"
            source.write_text(json.dumps(brief), encoding="utf-8")
            add_brief(workspace, job, "en", source)
            self.assertIsNotNone(workspace.latest_artifact(job, K.AUDIO, "en"))
            self.assertIsNotNone(workspace.latest_artifact(job, K.TRANSCRIPT, "en"))
            self.assertIsNotNone(workspace.latest_artifact(job, K.STORYBOARD, "en"))
            self.assertIsNone(workspace.latest_artifact(job, K.TIMELINE, "en"))
            self.assertIsNone(workspace.latest_artifact(job, K.APPROVAL, "en"))


if __name__ == "__main__":
    unittest.main()
