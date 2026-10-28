import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from vidkit import backgrounds, library, workflow
from vidkit.cli import build_parser, _add_storyboard
from vidkit.models import ArtifactKind as K, ArtifactStatus as S
from vidkit.storage import Workspace, sha256_file
from vidkit.timeline import compile_storyboard, validate_storyboard_shape
from vidkit.visuals import render_entry


class BackgroundStackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        catalog = self.root / 'renderer/library'
        catalog.mkdir(parents=True)
        (catalog / 'manifest.json').write_text(json.dumps({
            'components': [{'id': 'takeaway', 'kind': 'component', 'version': '1.0.0'},
                           {'id': 'channel-cta-strip', 'kind': 'component', 'version': '1.0.0'}],
            'themes': [{'id': 'dark-grid', 'kind': 'theme', 'version': '1.0.0', 'style': {}}]}))
        self.workspace = Workspace(self.root)
        self.workspace.initialize()
        self.add_layer('test-grid', 'background-pattern')
        self.add_layer('test-glow', 'background-effect')

    def add_layer(self, entry_id, kind):
        package = self.root / entry_id
        package.mkdir()
        (package / 'entry.tsx').write_text('export default () => null;')
        config = {'patternId': entry_id if kind == 'background-pattern' else 'test-grid',
                  'effectIds': [] if kind == 'background-pattern' else [entry_id]}
        (package / 'fixture.json').write_text(json.dumps({'schemaVersion': 4, 'language': 'en',
            'durationSeconds': 24, 'theme': 'dark-grid', 'background': config, 'scenes': [], 'captions': []}))
        manifest = {'id': entry_id, 'version': '1.0.0', 'kind': kind, 'description': entry_id,
                    'tags': [], 'useCases': [], 'limitations': [], 'source': 'test', 'license': 'MIT',
                    'propsSchema': {}, 'entrypoint': 'entry.tsx', 'loopSeconds': 12, 'preview': 'fixture.json'}
        path = package / 'manifest.json'
        path.write_text(json.dumps(manifest))
        return library.add_candidate(self.workspace, path)

    def preview(self, entry_id, still=False):
        def fake_run(command, **_kwargs):
            Path(command[4]).write_bytes(b'preview')
            return SimpleNamespace(returncode=0)
        with patch('vidkit.render.remotion_command', return_value=['remotion']), \
                patch('vidkit.library.subprocess.run', side_effect=fake_run) as run:
            result = library.preview(self.workspace, entry_id, still_only=still)
        return result, run.call_args_list

    def test_still_does_not_render_motion_or_allow_promotion(self):
        path, calls = self.preview('test-grid', still=True)
        self.assertEqual(len(calls), 1)
        command = calls[0].args[0]
        self.assertEqual(command[1], 'still')
        self.assertEqual(command[command.index('--frame') + 1], '90')
        self.assertEqual(command[command.index('--scale') + 1], '1')
        self.assertTrue(path.is_file())
        self.assertFalse(path.with_suffix('.mp4').exists())
        self.assertFalse(library.show(self.workspace, 'test-grid')['previewValid'])
        with self.assertRaisesRegex(ValueError, 'preview is missing'):
            library.approve(self.workspace, 'test-grid', 'Reviewer')
        _, motion_calls = self.preview('test-grid')
        motion_command = motion_calls[-1].args[0]
        self.assertEqual(motion_command[motion_command.index('--scale') + 1], '1')
        self.assertTrue(library.show(self.workspace, 'test-grid')['previewValid'])
        # A later still-only run cannot reuse an old clip as fresh motion evidence.
        self.preview('test-grid', still=True)
        self.assertFalse(library.show(self.workspace, 'test-grid')['previewValid'])

    def test_transparent_effect_preview_tracks_pattern_source_and_promotes_package(self):
        self.preview('test-grid')
        self.preview('test-glow')
        self.assertTrue(library.show(self.workspace, 'test-glow')['previewValid'])
        grid = library.show(self.workspace, 'test-grid')
        Path(grid['entrypointAbsolute']).write_text('export default () => <div/>;')
        self.assertFalse(library.show(self.workspace, 'test-glow')['previewValid'])
        self.preview('test-grid')
        self.preview('test-glow')
        result = library.approve(self.workspace, 'test-glow', 'Reviewer')
        self.assertTrue(Path(result['approvedManifest']).is_file())
        self.assertTrue((self.root / 'renderer/library/approved/code/test-glow-1-0-0/entry.tsx').is_file())
        self.assertEqual(library.show(self.workspace, 'test-grid')['status'], 'candidate')

    def test_stack_validation_locks_and_generated_registry(self):
        self.assertEqual(build_parser().parse_args(['create', 'Topic']).workflow_version, 10)
        self.assertTrue(build_parser().parse_args(['library', 'preview', 'test-grid', '--still-only']).still_only)
        config = {'patternId': 'test-grid', 'effectIds': ['test-glow']}
        self.preview('test-grid', still=True)
        with self.assertRaisesRegex(ValueError, 'still is insufficient'):
            backgrounds.resolve(config, library.entries(self.workspace))
        for bad in ({}, {'patternId': 'test-grid', 'effectIds': ['test-glow', 'test-glow']},
                    {'patternId': 'test-grid', 'patternProps': {'density': 0}}):
            with self.assertRaises(ValueError):
                backgrounds.normalize(bad)
        self.preview('test-grid')
        self.preview('test-glow')
        board = {'schemaVersion': 4, 'background': config, 'theme': 'dark-grid',
                 'scenes': [{'id': 'one', 'layout': 'takeaway', 'title': 'One idea',
                             'development': dict.fromkeys(['understanding', 'object', 'action', 'result', 'connection'], 'Explain'),
                             'startAnchor': {'wordIndex': 0}, 'endAnchor': {'wordIndex': 0}}]}
        self.assertEqual(validate_storyboard_shape(board, require_background_stack=True), [])
        timeline, _ = compile_storyboard({'words': [{'text': 'hello', 'start': 0, 'end': 2}], 'durationSeconds': 2},
                                        board, {'assets': []}, 'Topic', 'en', 'voice.wav',
                                        library_entries=library.entries(self.workspace), require_background_stack=True)
        self.assertEqual([x['kind'] for x in timeline['backgroundLayers']], ['background-pattern', 'background-effect'])
        self.assertTrue(library.locks_match(self.workspace, timeline))
        self.assertNotIn('backgroundId', timeline)
        entry = render_entry(self.workspace, 'job', 'en', timeline, library.entries(self.workspace))
        self.assertIn('test-grid', entry.read_text())
        self.assertIn('test-glow', entry.read_text())
        # An unselected layer has no effect on this render's locks.
        self.add_layer('other-pattern', 'background-pattern')
        Path(library.show(self.workspace, 'other-pattern')['entrypointAbsolute']).write_text('// changed')
        self.assertTrue(library.locks_match(self.workspace, timeline))
        Path(library.show(self.workspace, 'test-glow')['entrypointAbsolute']).write_text('// changed')
        self.assertFalse(library.locks_match(self.workspace, timeline))
        with self.assertRaisesRegex(ValueError, 'Locked background source'):
            render_entry(self.workspace, 'job', 'en', timeline, library.entries(self.workspace))

    def test_v10_approval_and_visual_change_preserve_voice(self):
        self.preview('test-grid')
        self.preview('test-glow')
        w = self.workspace
        job = w.create_job('Topic', ['en'], workflow_version=10)
        w.add_json_artifact(job, 'en', K.SCRIPT, {'cta': {}}, S.CHECKED)
        brief = {'angle': 'Explain', 'theme': 'dark-grid', 'background': {'patternId': 'test-grid'},
                 'hook': 'Why?', 'visualStrategy': 'Explain one idea', 'beats': [{'id': 'one', 'approach': 'reuse',
                 'development': dict.fromkeys(['understanding', 'object', 'action', 'result', 'connection'], 'Explain')}],
                 'explanationAlternatives': ['diagram', 'example'], 'chosenExplanation': 'diagram',
                 'conceptPreview': {'scenes': [
                     {'id': role, 'role': role, 'component': 'takeaway', 'startMs': i * 1000, 'endMs': (i + 1) * 1000}
                     for i, role in enumerate(['hook', 'evidence', 'takeaway'])] + [
                     {'id': 'cta', 'role': 'cta', 'component': 'channel-cta-strip', 'title': 'More examples', 'startMs': 3000, 'endMs': 9000}]}}
        source = self.root / 'brief.json'
        source.write_text(json.dumps(brief))
        artifact = workflow.add_brief(w, job, 'en', source)
        data = workflow.payload(w, artifact)
        self.assertEqual(data['background']['effectIds'], [])
        preview = w.area(job, 'en', 'briefs') / 'concept'
        preview.mkdir(parents=True)
        clip = preview / 'concept.mp4'
        clip.write_bytes(b'concept')
        evidence = {'briefSha256': artifact['sha256'], 'preview': clip.relative_to(w.workspace_root).as_posix(),
                    'sha256': sha256_file(clip), 'rendererLock': {},
                    **backgrounds.resolve(data['background'], library.entries(w))}
        record = preview / f"concept.r{artifact['revision']}.json"
        record.write_text(json.dumps(evidence))
        with patch('vidkit.checkpoints.current_renderer_lock', return_value={}):
            workflow.approve(w, job, 'en', 'concept', 'Reviewer')
        self.assertTrue(workflow.current_approval(w, job, 'en', 'concept'))
        board = {'schemaVersion': 4, 'background': {'patternId': 'test-grid', 'effectIds': ['test-glow']},
                 'scenes': [{'id': 'cta', 'role': 'cta', 'layout': 'custom', 'component': 'channel-cta-strip',
                             'title': 'More', 'startAnchor': {'wordIndex': 0}, 'endAnchor': {'wordIndex': 0},
                             'development': dict.fromkeys(['understanding', 'object', 'action', 'result', 'connection'], 'Explain')}]}
        storyboard = self.root / 'board.json'
        storyboard.write_text(json.dumps(board))
        with self.assertRaisesRegex(ValueError, 'differs from approved creative brief'):
            _add_storyboard(w, job, 'en', storyboard)
        audio = self.root / 'fixture.wav'
        audio.write_bytes(b'fixture')
        w.add_file_artifact(job, 'en', K.AUDIO, audio, S.CHECKED)
        w.add_json_artifact(job, 'en', K.TRANSCRIPT, {'words': []}, S.CHECKED, metadata={'variant': 'normalized'})
        w.add_json_artifact(job, 'en', K.TIMELINE, {}, S.CHECKED)
        brief['background']['effectIds'] = ['test-glow']
        source.write_text(json.dumps(brief))
        workflow.add_brief(w, job, 'en', source)
        self.assertFalse(workflow.current_approval(w, job, 'en', 'concept'))
        self.assertIsNone(w.latest_artifact(job, K.TIMELINE, 'en'))
        self.assertIsNotNone(w.latest_artifact(job, K.AUDIO, 'en'))
        self.assertIsNotNone(w.latest_artifact(job, K.TRANSCRIPT, 'en'))

    def test_next_stops_at_candidate_image_review_even_in_automatic_mode(self):
        from vidkit.models import Mode
        w = self.workspace
        job = w.create_job('Topic', ['en'], Mode.AUTOMATIC, workflow_version=10)
        for kind, language, data in [(K.SOURCE, None, {}), (K.SCRIPT, 'en', {}),
                                     (K.BRIEF, 'en', {'background': {'patternId': 'test-grid'}})]:
            w.add_json_artifact(job, language, kind, data, S.CHECKED)
        state = workflow.next_state(w, w.get_job(job), 'en')
        self.assertEqual(state['step'], 'background-image-preview')
        self.assertIn('--still-only', state['command'])
        self.preview('test-grid', still=True)
        state = workflow.next_state(w, w.get_job(job), 'en')
        self.assertEqual(state['step'], 'await-background-image-review')
        self.assertEqual(state['afterImageApprovalCommand'], 'vidkit library preview test-grid')


if __name__ == '__main__':
    unittest.main()
