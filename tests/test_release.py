import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import sop
import install as installer
import sync
import finish
from locks import lock


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = (Path(self.tmp.name)/'source').resolve()
        self.root.mkdir()
        self.home = Path(self.tmp.name)/'home'
        self.registry = self.root/'.local/installations.json'
        self.command('init')
        self.command('config', 'user.name', 'Synthetic test author')
        self.command('config', 'user.email', 'fixture@example.invalid')
        self.write('.gitignore', '.local/\n')
        self.write('rules.md', '# Fixture SOP\n')
        self.write('shared-rules.md', '# Fixture shared rules\n')
        self.write('skills/personal-sop-maintainer/SKILL.md', '---\nname: personal-sop-maintainer\ndescription: Fixture\n---\nOld committed entry\n')
        self.commit()
        sync.register(self.registry, 'codex', 'user', self.home, None, True)
        self.destination = self.home/'.agents/skills/personal-sop-maintainer'

    def tearDown(self):
        self.tmp.cleanup()

    def command(self, *args):
        return sync.git(self.root, *args)

    def write(self, name, content):
        path = self.root/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
        return path

    def commit(self):
        self.command('add', '.')
        self.command('commit', '-m', 'Synthetic fixture snapshot')

    def child(self):
        sop.init(self.root, 'example')
        self.write('example/rules.md', '# Complete synthetic rules\n')
        sop.approve(self.root, 'example', 'Synthetic test fixture; not a human approval.')
        self.write('example/skills/example-task/SKILL.md', '---\nname: example-task\ndescription: Fixture task\n---\nBody\n')
        self.write('example/skills/example-task/scripts/helper.py', 'print(1)\n')
        sop.record_skill(self.root, 'example', 'example-task')

    def test_sync_uses_committed_tree_and_preserves_unrelated_skills(self):
        unrelated = self.home/'.agents/skills/unrelated/SKILL.md'
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text('Untouched', encoding='utf-8')
        self.write('skills/personal-sop-maintainer/SKILL.md', 'UNCOMMITTED CHANGE\n')
        report = sync.sync_all(self.root, self.registry, True)
        self.assertIn('Old committed entry', (self.destination/'SKILL.md').read_text(encoding='utf-8'))
        self.assertEqual(json.loads((self.destination/'.sop-root.json').read_text())['revision'], self.command('rev-parse', 'HEAD'))
        self.assertTrue(report['applied'])
        self.assertEqual(unrelated.read_text(), 'Untouched')

    def test_draft_skipped_approved_child_synced_and_stale_resources_deactivated(self):
        sop.init(self.root, 'pending')
        self.child()
        self.commit()
        report = sync.sync_all(self.root, self.registry, True)
        published = self.home/'.agents/skills/example-task'
        self.assertTrue((published/'SKILL.md').exists())
        self.assertIn('check-skill example example-task', (published/'SKILL.md').read_text(encoding='utf-8'))
        self.assertEqual(report['targets'][0]['child_skills'], ['example-task'])
        self.assertTrue(any(row['domain'] == 'pending' for row in report['blocked']))
        self.write('example/skills/example-task/scripts/helper.py', 'print(2)\n')
        self.commit()
        report = sync.sync_all(self.root, self.registry, True)
        self.assertFalse(published.exists())
        self.assertEqual(report['targets'][0]['deactivated'], ['example-task'])
        self.assertTrue(list((self.home/'.agents/.personal-sop-disabled').glob('example-task-*')))

    def test_removed_resources_not_left_in_installed_entry(self):
        extra = self.write('skills/personal-sop-maintainer/obsolete.txt', 'old\n')
        self.commit()
        sync.sync_all(self.root, self.registry, True)
        self.assertTrue((self.destination/'obsolete.txt').exists())
        extra.unlink()
        self.commit()
        sync.sync_all(self.root, self.registry, True)
        self.assertFalse((self.destination/'obsolete.txt').exists())

    def test_finish_preserves_unrelated_staging_and_syncs_new_commit(self):
        self.write('unrelated.md', 'Keep staged\n')
        self.command('add', 'unrelated.md')
        self.write('rules.md', '# Intentional fixture update\n')
        calls = []
        report = finish.finish(self.root, ['rules.md'], 'Synthetic scoped commit', self.registry,
                               validator=lambda root: calls.append(root))
        self.assertEqual(calls, [self.root])
        self.assertEqual(self.command('diff', '--cached', '--name-only'), 'unrelated.md')
        self.assertEqual(self.command('show', '--format=', '--name-only', 'HEAD'), 'rules.md')
        self.assertEqual(report['revision'], self.command('rev-parse', 'HEAD'))
        self.assertTrue(report['committed'])

    def test_validation_failure_blocks_commit_and_sync(self):
        previous = self.command('rev-parse', 'HEAD')
        self.write('rules.md', '# Unvalidated\n')
        def fail(_): raise ValueError('Synthetic validation failure')
        with self.assertRaises(ValueError):
            finish.finish(self.root, ['rules.md'], 'Must not commit', self.registry, fail)
        self.assertEqual(self.command('rev-parse', 'HEAD'), previous)
        self.assertFalse(self.destination.exists())

    def test_failing_commit_hook_blocks_sync(self):
        previous = self.command('rev-parse', 'HEAD')
        hook = self.write('.git/hooks/pre-commit', '#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
        self.write('rules.md', '# Hook should reject\n')
        with self.assertRaises(subprocess.CalledProcessError):
            finish.finish(self.root, ['rules.md'], 'Rejected commit', self.registry, lambda _: None)
        self.assertEqual(self.command('rev-parse', 'HEAD'), previous)
        self.assertFalse(self.destination.exists())

    def test_no_change_no_empty_commit_and_explicit_deletion_supported(self):
        previous = self.command('rev-parse', 'HEAD')
        report = finish.finish(self.root, ['rules.md'], 'No empty commit', self.registry, lambda _: None)
        self.assertFalse(report['committed'])
        self.assertEqual(self.command('rev-parse', 'HEAD'), previous)
        self.write('obsolete.txt', 'Delete me\n')
        self.commit()
        (self.root/'obsolete.txt').unlink()
        report = finish.finish(self.root, ['obsolete.txt'], 'Delete explicit fixture file', self.registry, lambda _: None)
        self.assertTrue(report['committed'])
        self.assertNotIn('obsolete.txt', self.command('ls-tree', '--name-only', 'HEAD').splitlines())

    def test_conflicting_child_target_blocks_all_updates(self):
        self.child()
        self.commit()
        conflict = self.home/'.agents/skills/example-task'
        conflict.mkdir(parents=True)
        (conflict/'SKILL.md').write_text('Unrelated owner', encoding='utf-8')
        with self.assertRaises(ValueError): sync.sync_all(self.root, self.registry, True)
        self.assertFalse(self.destination.exists())

    def test_unchanged_sync_does_not_accumulate_backups(self):
        sync.sync_all(self.root, self.registry, True)
        sync.sync_all(self.root, self.registry, True)
        self.assertFalse((self.home/'.agents/.personal-sop-backups').exists())
        self.assertFalse(list((self.home/'.codex').glob('AGENTS.md.*.bak')))

    def test_concurrent_finish_is_blocked_without_committing(self):
        previous = self.command('rev-parse', 'HEAD')
        with lock(self.root, 'finish'):
            with self.assertRaises(ValueError):
                finish.finish(self.root, ['rules.md'], 'Concurrent fixture', self.registry, lambda _: None)
        self.assertEqual(self.command('rev-parse', 'HEAD'), previous)

    def test_child_invocation_rejects_recorded_but_uncommitted_changes(self):
        self.child()
        self.commit()
        sop.checked_skill(self.root, 'example', 'example-task')
        self.write('example/skills/example-task/scripts/helper.py', 'print(3)\n')
        sop.record_skill(self.root, 'example', 'example-task')
        with self.assertRaises(ValueError): sop.checked_skill(self.root, 'example', 'example-task')
        self.commit()
        sop.checked_skill(self.root, 'example', 'example-task')

    def test_sync_failure_keeps_successful_commit(self):
        conflict = self.destination
        conflict.mkdir(parents=True)
        (conflict/'SKILL.md').write_text('Unrelated owner', encoding='utf-8')
        previous = self.command('rev-parse', 'HEAD')
        self.write('rules.md', '# Committed despite later sync conflict\n')
        with self.assertRaises(ValueError):
            finish.finish(self.root, ['rules.md'], 'Synthetic commit before sync failure', self.registry, lambda _: None)
        self.assertNotEqual(self.command('rev-parse', 'HEAD'), previous)
        self.assertEqual((conflict/'SKILL.md').read_text(), 'Unrelated owner')

    def test_receipt_alias_is_normalized_without_losing_owned_children(self):
        records=sop.read_json(self.registry)
        records[0]['home']=str(self.home/'..'/'home')
        records[0]['installed_skills']=['personal-sop-maintainer','existing-child']
        sop.write_json(self.registry,records)
        sync.register(self.registry,'codex','user',self.home,None,True)
        records=sop.read_json(self.registry)
        self.assertEqual(len(records),1)
        self.assertIn('existing-child',records[0]['installed_skills'])


if __name__ == '__main__':
    unittest.main()
