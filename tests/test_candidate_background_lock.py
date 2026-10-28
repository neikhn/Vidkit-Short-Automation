import tempfile
import unittest
from pathlib import Path

from vidkit.checkpoints import dependency_files, lock_diff, renderer_lock
from vidkit.storage import Workspace


class CandidateBackgroundLockTests(unittest.TestCase):
    def test_candidate_imports_are_locked_and_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = Workspace(root)
            package = root / 'workspace/library/candidates/code/grid-1-0-0'
            package.mkdir(parents=True)
            entry = package / 'entry.tsx'
            pattern = package / 'Pattern.tsx'
            entry.write_text("import Pattern from './Pattern'; export default Pattern;", encoding='utf-8')
            pattern.write_text('export default () => null;', encoding='utf-8')
            lock = renderer_lock(workspace, [entry])
            self.assertIn(pattern.relative_to(root).as_posix(), lock)
            pattern.write_text('export default () => <svg/>;', encoding='utf-8')
            self.assertIn('changed: ' + pattern.relative_to(root).as_posix(), lock_diff(workspace, lock))
            outside = package.parent.parent / 'outside.tsx'
            outside.write_text('export default () => null;', encoding='utf-8')
            entry.write_text("import Outside from '../../outside'; export default Outside;", encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'escapes renderer/job workspace'):
                dependency_files(workspace, [entry])
