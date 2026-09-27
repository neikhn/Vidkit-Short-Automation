import json
import shutil
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from vidkit.assets import detect_image, prepare_asset_entry
from vidkit.captions import build_caption_cues
from vidkit.models import ArtifactKind as K, ArtifactStatus as S
from vidkit.storage import Workspace, sha256_file
from vidkit.workflow import approve, current_approval, make_qa
from vidkit import library
from vidkit.timeline import compile_storyboard
from vidkit.render import prepare_renderer_job


class V3WorkflowTests(unittest.TestCase):
    def test_renderer_copies_secondary_scene_asset(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = Workspace(root)
            workspace.initialize()
            assets = workspace.workspace_root / "assets"
            assets.mkdir(parents=True)
            article = assets / "article.png"
            portrait = assets / "portrait.png"
            Image.new("RGB", (20, 20)).save(article)
            Image.new("RGB", (20, 20)).save(portrait)
            narration = root / "narration.mp3"
            narration.write_bytes(b"audio fixture")
            timeline = {"scenes": [{"asset": {"path": "assets/article.png", "sha256": sha256_file(article)},
                                    "supportAssets": [{"path": "assets/portrait.png", "sha256": sha256_file(portrait)}]}]}
            props_path = prepare_renderer_job(workspace, "job", "en", timeline, narration)
            props = json.loads(props_path.read_text(encoding="utf8"))
            secondary = props["scenes"][0]["supportAssets"][0]
            self.assertTrue((root / "renderer" / "public" / secondary["src"]).is_file())

    def test_storyboard_support_asset_is_resolved_and_required(self):
        transcript = {"words": [{"text": "Founder", "start": 0.1, "end": 0.4}]}
        scene = {"id": "article", "layout": "screenshot-focus", "title": "Founder",
                 "assetId": "article", "supportAssetIds": ["portrait"],
                 "startAnchor": {"wordIndex": 0}, "endAnchor": {"wordIndex": 0}}
        storyboard = {"schemaVersion": 3, "theme": "dark-grid", "scenes": [scene]}
        article = {"id": "article", "path": "article.png", "width": 1000, "height": 1000}
        portrait = {"id": "portrait", "path": "portrait.png", "width": 720, "height": 720}
        timeline, missing = compile_storyboard(transcript, storyboard,
                                               {"assets": [article, portrait]}, "Founder", "en", "audio.wav")
        self.assertFalse(missing)
        self.assertEqual(timeline["scenes"][0]["supportAssets"], [portrait])
        _, missing = compile_storyboard(transcript, storyboard, {"assets": [article]},
                                        "Founder", "en", "audio.wav")
        self.assertIn("portrait", missing)

    def test_storyboard_whoosh_uses_word_anchor(self):
        transcript = {"words": [{"text": "Hello", "start": 0.1, "end": 0.3},
                                {"text": "world.", "start": 0.5, "end": 0.8}]}
        storyboard = {"schemaVersion": 3, "theme": "dark-grid",
                      "scenes": [{"id": "one", "layout": "takeaway", "title": "Hello",
                                  "startAnchor": {"wordIndex": 0}, "endAnchor": {"wordIndex": 1}}],
                      "sfx": [{"type": "whoosh", "wordIndex": 1}]}
        timeline, missing = compile_storyboard(transcript, storyboard, {"assets": []},
                                               "Hello", "en", "audio.wav")
        self.assertFalse(missing)
        self.assertEqual(timeline["sfx"], [{"type": "whoosh", "wordIndex": 1, "atMs": 500}])

    def test_concept_and_export_approvals_are_revision_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory))
            job = workspace.create_job("Example", ["en"], workflow_version=3)
            self.assertEqual(workspace.get_job(job)["workflow_version"], 3)
            workspace.add_json_artifact(job, "en", K.SCRIPT, {"tts_input": "One"}, S.CHECKED)
            workspace.add_json_artifact(job, "en", K.BRIEF, {"theme": "dark-grid"}, S.CHECKED)
            approve(workspace, job, "en", "concept", "Human")
            self.assertTrue(current_approval(workspace, job, "en", "concept"))
            workspace.invalidate_downstream(job, "en", K.AUDIO)
            self.assertTrue(current_approval(workspace, job, "en", "concept"))
            workspace.add_json_artifact(job, "en", K.BRIEF, {"theme": "dark-contours"}, S.CHECKED)
            self.assertFalse(current_approval(workspace, job, "en", "concept"))
            workspace.add_json_artifact(job, "en", K.TIMELINE, {"validationIssues": [], "missingAssets": []}, S.CHECKED)
            preview_file = Path(directory) / "preview.mp4"
            preview_file.write_bytes(b"test-fixture")
            workspace.add_file_artifact(job, "en", K.PREVIEW, preview_file, S.NEEDS_REVIEW)
            make_qa(workspace, job, "en")
            approve(workspace, job, "en", "export", "Human")
            self.assertTrue(current_approval(workspace, job, "en", "export"))
            make_qa(workspace, job, "en", {"checks": {"frameInspection": {
                "status": "fail", "evidence": ["Title clips on phone"]}}})
            with self.assertRaisesRegex(ValueError, "QA failed"):
                approve(workspace, job, "en", "export", "Human")
            workspace.add_json_artifact(job, "en", K.TIMELINE, {"validationIssues": [], "missingAssets": []}, S.CHECKED)
            self.assertFalse(current_approval(workspace, job, "en", "export"))

    def test_caption_does_not_orphan_directly_or_at(self):
        text = "Jev returns structured choices scores probabilities and confidence that code can use directly."
        words = [{"text": token, "start": index * .22, "end": index * .22 + .18}
                 for index, token in enumerate(text.split())]
        cues = build_caption_cues(words)
        self.assertEqual([token.text for cue in cues for token in cue.tokens], text.split())
        self.assertTrue(all(len(cue.lines) <= 2 for cue in cues))
        self.assertTrue(all(cue.tokens[-1].text.casefold().strip(".") != "at" for cue in cues))
        self.assertFalse(any(cue.text == "directly." for cue in cues))
        self.assertTrue(all(left.end_ms <= right.start_ms for left, right in zip(cues, cues[1:])))
        price = "The company reports response times from 70 to 500 milliseconds, with input priced at $0.042 per million tokens"
        price_words = [{"text": token, "start": index * .22, "end": index * .22 + .18}
                       for index, token in enumerate(price.split())]
        price_cues = build_caption_cues(price_words)
        self.assertFalse(any(cue.text.casefold().endswith(" at") for cue in price_cues))
        self.assertFalse(any(line.casefold().endswith(" at") for cue in price_cues for line in cue.lines))
        self.assertTrue(any("$0.042" in cue.text for cue in price_cues))

    def test_display_mapping_covers_spoken_words(self):
        words = [
            {"text": "zero", "start": 0, "end": .2},
            {"text": "point", "start": .21, "end": .4},
            {"text": "zero", "start": .41, "end": .6},
            {"text": "four", "start": .61, "end": .8},
            {"text": "two", "start": .81, "end": 1},
            {"text": "dollars", "start": 1.01, "end": 1.3},
        ]
        plan = {"groups": [{"startWord": 0, "endWord": 5, "displayTokens": [
            {"text": "$0.042", "startWord": 0, "endWord": 5, "spokenText": "zero point zero four two dollars"}
        ]}]}
        cues = build_caption_cues(words, plan=plan)
        self.assertEqual(cues[0].text, "$0.042")
        bad = json.loads(json.dumps(plan))
        bad["groups"][0]["displayTokens"][0]["spokenText"] = "something else"
        with self.assertRaises(ValueError):
            build_caption_cues(words, plan=bad)

    def test_image_content_controls_extension(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Workspace(Path(directory))
            job = workspace.create_job("Example", ["en"])
            image = Path(directory) / "misleading.jpg"
            Image.new("RGB", (1000, 800), "blue").save(image, format="PNG")
            self.assertEqual(detect_image(image)[2:], (".png", "image/png"))
            entry, target = prepare_asset_entry(workspace, job, image, "Official artwork",
                                                "official-media", "https://example.com", "artwork")
            self.assertEqual(target.suffix, ".png")
            self.assertEqual(entry["evidenceType"], "artwork")

    def test_library_candidate_and_shared_asset_lifecycle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "renderer" / "library" / "manifest.json"
            manifest.parent.mkdir(parents=True)
            source_manifest = Path(__file__).resolve().parents[1] / "renderer" / "library" / "manifest.json"
            shutil.copy2(source_manifest, manifest)
            workspace = Workspace(root)
            workspace.initialize()
            fixture = root / "fixture.json"
            fixture.write_text('{"schemaVersion":3,"durationSeconds":2,"scenes":[{"id":"sample","layout":"diagram-flow","title":"Example","body":"A → B","startMs":0,"endMs":2000}]}', encoding="utf-8")
            candidate_file = root / "candidate.json"
            candidate_file.write_text(json.dumps({
                "id": "custom-flow", "version": "1.0.0", "kind": "component",
                "baseComponent": "diagram-flow", "description": "A tailored flow",
                "tags": ["flow"], "useCases": ["product process"], "limitations": [],
                "propsSchema": {}, "source": "Vidkit", "license": "MIT", "preview": "fixture.json"
            }), encoding="utf-8")
            candidate = library.add_candidate(workspace, candidate_file)
            self.assertEqual(candidate["status"], "candidate")
            self.assertEqual(library.show(workspace, "custom-flow")["baseComponent"], "diagram-flow")
            self.assertEqual(len(library.search(workspace, "custom", kind="component", theme="dark-grid", aspect="portrait", status="candidate")), 1)
            def checked_fixture(entry_id):
                item = library.show(workspace, entry_id)
                fixture_path = workspace.workspace_root / item["preview"]
                image_path = workspace.workspace_root / "library" / "previews" / f"{entry_id}.png"
                image_path.parent.mkdir(parents=True, exist_ok=True)
                Image.new("RGB", (360, 640)).save(image_path)
                item.update({"fixtureSha256": sha256_file(fixture_path),
                             "previewImage": image_path.relative_to(workspace.workspace_root).as_posix(),
                             "previewSha256": sha256_file(image_path),
                             "previewManifestSha256": library.checksum(item)})
                candidate_path = workspace.workspace_root / "library" / "candidates" / f"{entry_id}-1-0-0.json"
                candidate_path.write_text(json.dumps(item), encoding="utf-8")
            checked_fixture("custom-flow")
            promoted = library.approve(workspace, "custom-flow", "Human")
            self.assertEqual(library.show(workspace, "custom-flow")["status"], "approved")
            self.assertTrue((root / "renderer/library/approved/custom-flow-1-0-0.json").is_file())
            self.assertEqual(Path(promoted["approvedManifest"]), root / "renderer/library/approved/custom-flow-1-0-0.json")
            image = root / "artwork.fake"
            Image.new("RGB", (900, 500)).save(image, format="PNG")
            asset_manifest = root / "asset.json"
            asset_manifest.write_text(json.dumps({
                "id": "shared-artwork", "version": "1.0.0", "kind": "asset",
                "description": "Reusable sourced artwork", "tags": ["artwork"],
                "useCases": ["demonstration"], "limitations": [], "propsSchema": {},
                "source": "https://example.com", "license": "permitted",
                "sourceUrl": "https://example.com", "usageBasis": "official media",
                "evidenceType": "artwork", "file": "artwork.fake"
            }), encoding="utf-8")
            asset = library.add_candidate(workspace, asset_manifest)
            self.assertEqual(asset["mime"], "image/png")
            self.assertEqual(asset["aspect"], "landscape")
            self.assertEqual(library.show(workspace, "shared-artwork")["sha256"], asset["sha256"])
            self.assertEqual(len(library.search(workspace, "artwork", kind="asset", aspect="landscape")), 1)
            library.approve(workspace, "shared-artwork", "Human")
            self.assertEqual(library.show(workspace, "shared-artwork")["status"], "approved")
            second_candidate_file = root / "another.json"
            second_candidate_file.write_text(json.dumps({
                "id": "automatic-flow", "version": "1.0.0", "kind": "component",
                "baseComponent": "diagram-flow", "description": "Automation fixture",
                "tags": ["flow"], "useCases": ["demo"], "limitations": [],
                "propsSchema": {}, "source": "Vidkit", "license": "MIT", "preview": "fixture.json"
            }), encoding="utf-8")
            library.add_candidate(workspace, second_candidate_file)
            checked_fixture("automatic-flow")
            timeline, missing = compile_storyboard(
                {"words": [{"text": "Hello", "start": 0, "end": .3},
                           {"text": "world.", "start": .31, "end": .6}]},
                {"schemaVersion": 3, "theme": "dark-grid", "scenes": [{
                    "id": "one", "layout": "diagram-flow", "component": "automatic-flow",
                    "componentVersion": "1.0.0", "title": "Example", "body": "A → B",
                    "startAnchor": {"wordIndex": 0}, "endAnchor": {"wordIndex": 1}
                }]},
                {"assets": []}, "Example", "en", "audio.wav", library_entries=library.entries(workspace)
            )
            self.assertFalse(missing)
            self.assertEqual(timeline["componentLocks"][0]["id"], "automatic-flow")
            self.assertEqual(library.show(workspace, "automatic-flow")["status"], "candidate")
            stale_fixture = workspace.workspace_root / library.show(workspace, "automatic-flow")["preview"]
            stale_fixture.write_text(stale_fixture.read_text(encoding="utf-8") + " ", encoding="utf-8")
            self.assertFalse(library.show(workspace, "automatic-flow")["previewValid"])
            with self.assertRaisesRegex(ValueError, "rendered library preview"):
                compile_storyboard(
                    {"words": [{"text": "Hello", "start": 0, "end": .3},
                               {"text": "world.", "start": .31, "end": .6}]},
                    {"schemaVersion": 3, "theme": "dark-grid", "scenes": [{
                        "id": "one", "layout": "diagram-flow", "component": "automatic-flow",
                        "componentVersion": "1.0.0", "title": "Example",
                        "startAnchor": {"wordIndex": 0}, "endAnchor": {"wordIndex": 1}}]},
                    {"assets": []}, "Example", "en", "audio.wav", library_entries=library.entries(workspace))


if __name__ == "__main__":
    unittest.main()
