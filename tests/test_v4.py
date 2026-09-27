import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from vidkit import library
from vidkit.cli import _add_feedback, _concept_preview, _metrics
from vidkit.models import ArtifactKind as K, ArtifactStatus as S
from vidkit.checkpoints import checkpoint, diff, lock_diff, renderer_lock
from vidkit.motion import compile_events
from vidkit.storage import Workspace, sha256_file
from vidkit.timeline import compile_storyboard, validate_storyboard_shape
from vidkit.visuals import add, entries


DEVELOPMENT = {"understanding": "What changed", "object": "A result", "action": "Reveal it",
               "result": "A visible typed output", "connection": "Use the result next"}


class V4Tests(unittest.TestCase):
    def test_concept_reuses_audio_ranges_and_rejects_explicit_overflow(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory))
            job = workspace.create_job("Audio concept", ["en"])
            audio = Path(directory) / "audio.wav"
            audio.write_bytes(b"fixture audio")
            workspace.add_file_artifact(job, "en", K.AUDIO, audio, S.CHECKED)
            scenes = [{"id": role, "role": role, "component": "takeaway", "startMs": i * 1000,
                       "endMs": (i + 1) * 1000, "audioStartMs": i * 1000 + 500}
                      for i, role in enumerate(("hook", "evidence", "takeaway"))]
            workspace.add_json_artifact(job, "en", K.BRIEF,
                                       {"theme": "dark-grid", "conceptPreview": {"scenes": scenes}}, S.CHECKED)
            prepared = []
            def prepare(*args):
                prepared.append(args[3])
                return Path(directory) / "props.json"
            def render(_root, _props, output, _entry):
                output.write_bytes(b"movie")
                return 0
            with patch("vidkit.cli.audio_duration", return_value=4), \
                    patch("vidkit.cli.library.show", return_value={"id": "dark-grid", "version": "1", "sha256": "theme", "style": {}}), \
                    patch("vidkit.cli.prepare_renderer_job", side_effect=prepare), \
                    patch("vidkit.cli.visuals.render_entry", return_value=Path(directory) / "index.tsx"), \
                    patch("vidkit.cli.run_render", side_effect=render), \
                    patch("vidkit.cli.remotion_command", return_value=["node"]), \
                    patch("vidkit.cli.subprocess.run", return_value=SimpleNamespace(returncode=0)), \
                    patch("vidkit.cli.checkpoints.current_renderer_lock", return_value={}), redirect_stdout(StringIO()):
                self.assertEqual(_concept_preview(workspace, job, "en", "evidence"), 0)
                self.assertEqual(prepared[0]["audioSegments"],
                                 [{"startMs": 0, "endMs": 1000, "sourceStartMs": 1500}])
                scenes[1]["audioStartMs"] = 3900
                workspace.add_json_artifact(job, "en", K.BRIEF,
                                           {"theme": "dark-grid", "conceptPreview": {"scenes": scenes}}, S.CHECKED)
                with self.assertRaisesRegex(ValueError, "exceeds narration"):
                    _concept_preview(workspace, job, "en", "evidence")

    def test_feedback_metrics_record_actual_revision_and_optional_time(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory))
            job = workspace.create_job("Review", ["en"])
            workspace.add_json_artifact(job, "en", K.TIMELINE, {"scenes": [{"id": "hook"}]}, S.CHECKED)
            movie = Path(directory) / "preview.mp4"
            movie.write_bytes(b"fixture")
            workspace.add_file_artifact(job, "en", K.PREVIEW, movie, S.NEEDS_REVIEW)
            source = Path(directory) / "review.json"
            source.write_text(json.dumps({"reviewMinutes": 7.5, "observations": [{
                "sceneId": "hook", "scope": "video", "category": "layout",
                "observation": "Move the image closer to the headline"}]}), encoding="utf-8")
            with redirect_stdout(StringIO()):
                _add_feedback(workspace, job, "en", source)
            output = StringIO()
            with redirect_stdout(output):
                _metrics(workspace, job, "en")
            report = json.loads(output.getvalue())
            self.assertEqual(report["previewRounds"], 1)
            self.assertEqual(report["manualRevisionRequests"], 1)
            self.assertEqual(report["reviewMinutesRecorded"], 7.5)

    def test_renderer_lock_tracks_imports_but_ignores_unrelated_component(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = Workspace(root)
            workspace.initialize()
            source = root / "renderer/src"
            source.mkdir(parents=True)
            (source / "VidkitShort.tsx").write_text("import './Widget'; import '../library/manifest.json';", encoding="utf-8")
            (source / "Widget.tsx").write_text("import './widget.css'; export const widget = 1;", encoding="utf-8")
            (source / "widget.css").write_text("@font-face {src: url('./font.woff2');}", encoding="utf-8")
            (source / "font.woff2").write_bytes(b"font")
            (source / "Other.tsx").write_text("export const other = 1;", encoding="utf-8")
            (source / "Root.tsx").write_text("export {};", encoding="utf-8")
            (source / "index.ts").write_text("export {};", encoding="utf-8")
            (root / "renderer/remotion.config.ts").write_text("export {};", encoding="utf-8")
            (root / "renderer/package-lock.json").write_text("{}", encoding="utf-8")
            manifest = root / "renderer/library/manifest.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"components":[]}', encoding="utf-8")
            lock = renderer_lock(workspace)
            self.assertIn("renderer/src/font.woff2", lock)
            (source / "Other.tsx").write_text("export const other = 2;", encoding="utf-8")
            manifest.write_text('{"components":[{"id":"unrelated"}]}', encoding="utf-8")
            self.assertEqual(lock_diff(workspace, lock), [])
            (source / "Widget.tsx").write_text("export const widget = 2;", encoding="utf-8")
            self.assertEqual(lock_diff(workspace, lock), ["changed: renderer/src/Widget.tsx"])

    def test_code_candidate_promotes_source_and_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "renderer/library/manifest.json"
            target.parent.mkdir(parents=True)
            shutil.copy2(Path(__file__).resolve().parents[1] / "renderer/library/manifest.json", target)
            workspace = Workspace(root)
            workspace.initialize()
            package = root / "package"
            package.mkdir()
            (package / "Shape.tsx").write_text("export default function Shape(){return null}", encoding="utf-8")
            (package / "fixture.json").write_text(json.dumps({"schemaVersion": 4, "durationSeconds": 5,
                "scenes": [{"componentId": "new-shape", "startMs": 0, "endMs": 5000}]}), encoding="utf-8")
            manifest = package / "manifest.json"
            manifest.write_text(json.dumps({"kind": "component", "id": "new-shape", "version": "1.0.0",
                "description": "Custom shape", "tags": ["shape"], "useCases": ["explanation"],
                "limitations": [], "propsSchema": {}, "source": "Fixture", "license": "MIT",
                "entrypoint": "Shape.tsx", "preview": "fixture.json"}), encoding="utf-8")
            library.add_candidate(workspace, manifest)

            def fake_run(command, **_kwargs):
                Path(command[4]).write_bytes(b"rendered fixture")
                return SimpleNamespace(returncode=0)

            with patch("vidkit.render.remotion_command", return_value=["remotion"]), patch(
                "vidkit.library.subprocess.run", side_effect=fake_run
            ):
                library.preview(workspace, "new-shape")
            self.assertTrue(library.show(workspace, "new-shape")["previewValid"])
            approved = library.approve(workspace, "new-shape", "Reviewer")
            self.assertTrue(Path(approved["approvedFixture"]).is_file())
            promoted = root / "renderer/library/approved/code/new-shape-1-0-0/Shape.tsx"
            self.assertTrue(promoted.is_file())

    def test_motion_dependencies_fit_and_cycles(self):
        words = [{"text": "first", "start": 0.0, "end": .2}]
        scene = {"id": "flow", "startMs": 0, "endMs": 3000, "startWord": 0, "endWord": 0,
                 "entities": [{"id": "object"}, {"id": "connector"}, {"id": "result"}],
                 "events": [{"id": "object-in", "entityId": "object", "wordIndex": 0, "durationFrames": 10},
                            {"id": "connect", "entityId": "connector", "after": "object-in", "durationFrames": 10},
                            {"id": "result-in", "entityId": "result", "after": "connect", "durationFrames": 10}]}
        events = compile_events(scene, words)
        self.assertEqual([item["atFrame"] for item in events], [0, 10, 20])
        scene["events"][0] = {"id": "object-in", "entityId": "object", "after": "result-in"}
        with self.assertRaisesRegex(ValueError, "cyclic"):
            compile_events(scene, words)
        scene["events"][0] = {"id": "object-in", "entityId": "missing", "wordIndex": 0}
        with self.assertRaisesRegex(ValueError, "unknown entity"):
            compile_events(scene, words)

    def test_custom_visual_add_and_checkpoint_diff(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = Workspace(root)
            job = workspace.create_job("Product", ["en"])
            self.assertEqual(workspace.get_job(job)["workflow_version"], 4)
            package = root / "source-visual"
            package.mkdir()
            (package / "Visual.tsx").write_text("export {default} from './Shape';", encoding="utf-8")
            (package / "Shape.tsx").write_text("export default function Shape(){return null}", encoding="utf-8")
            (package / "fixture.json").write_text(json.dumps({"schemaVersion": 4, "durationSeconds": 5,
                "scenes": [{"componentId": "my-shape", "startMs": 0, "endMs": 5000}]}), encoding="utf-8")
            manifest = package / "manifest.json"
            manifest.write_text(json.dumps({"kind": "component", "id": "my-shape", "version": "1.0.0",
                "description": "Job visual", "propsSchema": {}, "entrypoint": "Visual.tsx",
                "fixture": "fixture.json"}), encoding="utf-8")
            add(workspace, job, "en", manifest)
            item = entries(workspace, job, "en")[0]
            self.assertEqual(len(item["sourcePaths"]), 3)
            code = Path(item["sourcePaths"][0])
            lock_file = root / "lock.ts"
            lock_file.write_text("original", encoding="utf-8")
            checkpoint(workspace, job, "en", {"lock.ts": sha256_file(lock_file)})
            code.write_text("// edited in Studio review\n" + code.read_text(encoding="utf-8"), encoding="utf-8")
            changes = diff(workspace, job, "en")["changes"]
            self.assertTrue(any(change["path"].endswith(code.name) and change["status"] == "modified" for change in changes))

    def test_three_storyboard_forms_compile_without_template_limit(self):
        for label, component, props in (
            ("product", "article-highlight", {"excerpt": "A verified statement", "highlight": "verified", "source": "Docs"}),
            ("mechanism", "branch-flow", {"sourceNode": "Input", "branches": ["A", "B"]}),
            ("comparison", "range-log-chart", {"values": [{"label": "A", "value": 1}], "unit": "ms", "source": "Report", "scale": "linear"}),
        ):
            with self.subTest(label=label):
                transcript = {"words": [{"text": "Example", "start": 0, "end": .6}], "durationSeconds": 2}
                scene = {"id": label, "layout": "custom", "component": component, "title": label,
                         "componentProps": props, "development": DEVELOPMENT,
                         "startAnchor": {"wordIndex": 0}, "endAnchor": {"wordIndex": 0}}
                storyboard = {"schemaVersion": 4, "language": "en", "theme": "dark-grid", "scenes": [scene]}
                self.assertEqual(validate_storyboard_shape(storyboard), [])
                timeline, missing = compile_storyboard(transcript, storyboard, {"assets": []}, label, "en", "audio.wav")
                self.assertFalse(missing)
                self.assertEqual(timeline["scenes"][0]["componentId"], component)

    def test_continuity_origin_persists_into_next_scene(self):
        words = [{"text": "first", "start": 0, "end": .5},
                 {"text": "second", "start": 2, "end": 2.5}]
        scenes = []
        for index in range(2):
            scenes.append({"id": f"step-{index}", "layout": "custom", "component": "continuity-handoff",
                           "title": "Carry result", "development": DEVELOPMENT,
                           "entities": [{"id": "result"}], "continuityGroup": "result-chain",
                           "startAnchor": {"wordIndex": index}, "endAnchor": {"wordIndex": index}})
        timeline, _ = compile_storyboard({"words": words, "durationSeconds": 4},
                                         {"schemaVersion": 4, "theme": "dark-grid", "scenes": scenes},
                                         {"assets": []}, "Continuity", "en", "audio.wav")
        self.assertEqual(timeline["scenes"][0]["continuityStartFrame"], 0)
        self.assertEqual(timeline["scenes"][1]["continuityStartFrame"], 0)
        self.assertGreater(timeline["scenes"][1]["absoluteStartFrame"], 0)


if __name__ == "__main__":
    unittest.main()
