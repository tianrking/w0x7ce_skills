import json
import subprocess
import sys
import tempfile
import shutil
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import sop


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def rules(self, name='example'):
        sop.init(self.root, name)
        (self.root/name/'rules.md').write_text('# Synthetic fixture\nComplete test rules; not human approval.\n', encoding='utf-8')
        return self.root/name

    def test_draft_cannot_produce_recorded_skill(self):
        path = self.rules()
        (path/'skills/demo').mkdir(parents=True)
        (path/'skills/demo/SKILL.md').write_text('fixture', encoding='utf-8')
        with self.assertRaises(ValueError): sop.record_skill(self.root, 'example', 'demo')
        with self.assertRaises(ValueError): sop.approve(self.root, 'example', ' ')

    def test_revision_preserves_active_rules_and_detects_stale_skill(self):
        path = self.rules()
        sop.approve(self.root, 'example', 'Synthetic test fixture, not a real user confirmation.')
        (path/'skills/demo').mkdir(parents=True)
        (path/'skills/demo/SKILL.md').write_text('fixture', encoding='utf-8')
        sop.record_skill(self.root, 'example', 'demo')
        old = (path/'rules.md').read_bytes()
        sop.draft(self.root, 'example')
        (path/'rules.draft.md').write_text('# Revised synthetic rules\n', encoding='utf-8')
        self.assertEqual((path/'rules.md').read_bytes(), old)
        self.assertTrue(sop.status(self.root)[0]['pending_draft'])
        sop.approve(self.root, 'example', 'Synthetic revision confirmation fixture.')
        self.assertFalse((path/'rules.draft.md').exists())
        self.assertEqual(sop.status(self.root)[0]['skills']['demo'], 'needs-sync')

    def test_changed_confirmed_rules_block_skill_record(self):
        path = self.rules()
        sop.approve(self.root, 'example', 'Synthetic confirmation fixture.')
        (path/'rules.md').write_text('unconfirmed alteration', encoding='utf-8')
        with self.assertRaises(ValueError): sop.confirmed(path)
        with self.assertRaises(ValueError): sop.record_skill(self.root, 'example', 'demo')

    def test_incomplete_and_escaping_domain_rejected(self):
        sop.init(self.root, 'example')
        with self.assertRaises(ValueError): sop.approve(self.root, 'example', 'Synthetic fixture.')
        with self.assertRaises(ValueError): sop.init(self.root, '../outside')
        with self.assertRaises(ValueError): sop.init(self.root, 'skills')

    def test_git_line_endings_preserve_reviewed_fingerprint(self):
        path = self.rules()
        sop.approve(self.root, 'example', 'Synthetic confirmation fixture.')
        file = path/'rules.md'
        lf = file.read_bytes().replace(b'\r\n', b'\n')
        file.write_bytes(lf.replace(b'\n', b'\r\n'))
        sop.confirmed(path)
        file.write_bytes(lf)
        sop.confirmed(path)


class InstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = tempfile.TemporaryDirectory()
        cls.source = Path(cls.fixture.name)/'source'
        cls.source.mkdir()
        shutil.copytree(ROOT/'skills/personal-sop-maintainer', cls.source/'skills/personal-sop-maintainer')
        (cls.source/'scripts').mkdir()
        (cls.source/'scripts/sop.py').write_text('# fixture\n', encoding='utf-8')
        (cls.source/'rules.md').write_text('# fixture rules\n', encoding='utf-8')
        for command in [['init'], ['config','user.name','Synthetic fixture'], ['config','user.email','fixture@example.invalid'],
                        ['add','.'], ['commit','-m','Synthetic source']]:
            subprocess.run(['git','-C',str(cls.source),*command],check=True,capture_output=True)

    @classmethod
    def tearDownClass(cls):
        cls.fixture.cleanup()

    def run_installer(self, home, *args, ok=True):
        result = subprocess.run([sys.executable, str(ROOT/'scripts/install.py'), '--home', str(home),
                                 '--root', str(self.source), '--agent', 'both',
                                 '--registry', str(home/'installations.json'), *args],
                                capture_output=True, text=True, encoding='utf-8')
        if ok: self.assertEqual(result.returncode, 0, result.stderr)
        else: self.assertNotEqual(result.returncode, 0)
        return result

    def test_preview_install_reinstall_and_locator(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            self.run_installer(home, '--with-guidance')
            self.assertEqual(list(home.iterdir()), [])
            (home/'.claude').mkdir()
            instructions = home/'.claude/CLAUDE.md'
            instructions.write_text('Existing instructions\n', encoding='utf-8')
            for _ in range(2): self.run_installer(home, '--with-guidance', '--apply')
            text = instructions.read_text(encoding='utf-8')
            self.assertTrue(text.startswith('Existing instructions'))
            self.assertEqual(text.count('<!-- personal-sop:begin -->'), 1)
            self.assertTrue(list((home/'.claude').glob('CLAUDE.md.*.bak')))
            for agent in ['.agents', '.claude']:
                locator = home/agent/'skills/personal-sop-maintainer/scripts/locate_sop.py'
                result = subprocess.run([sys.executable, str(locator)], capture_output=True, text=True, encoding='utf-8', check=True)
                self.assertEqual(Path(json.loads(result.stdout)['root']), self.source)

    def test_conflict_preflights_both_agents(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            occupied = home/'.claude/skills/personal-sop-maintainer'
            occupied.mkdir(parents=True)
            (occupied/'SKILL.md').write_text('Unrelated skill', encoding='utf-8')
            self.run_installer(home, '--apply', ok=False)
            self.assertFalse((home/'.agents').exists())
            self.assertEqual((occupied/'SKILL.md').read_text(), 'Unrelated skill')

    def test_project_scope_installs_to_requested_project(self):
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp)/'project'
            self.run_installer(Path(temp)/'unused-home', '--scope', 'project', '--target', str(project), '--apply')
            self.assertTrue((project/'.agents/skills/personal-sop-maintainer/SKILL.md').is_file())
            self.assertTrue((project/'.claude/skills/personal-sop-maintainer/SKILL.md').is_file())
            self.assertFalse((project/'AGENTS.md').exists())

    def test_explicit_source_migration_transfers_receipt_and_preserves_old_source(self):
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)/'home'
            old = Path(temp)/'old-source'
            shutil.copytree(self.source, old, ignore=shutil.ignore_patterns('.git'))
            installed = home/'.agents/skills/personal-sop-maintainer'
            installed.mkdir(parents=True)
            (installed/'SKILL.md').write_text('Old owned entry',encoding='utf-8')
            sop.write_json(installed/'.sop-root.json',{'root':str(old),'kind':'entry'})
            receipt = old/'.local/installations.json'
            receipt.parent.mkdir()
            old_child=home/'.agents/skills/old-child'
            old_child.mkdir(parents=True)
            (old_child/'SKILL.md').write_text('Old owned child',encoding='utf-8')
            sop.write_json(old_child/'.sop-root.json',{'root':str(old),'kind':'child'})
            sop.write_json(receipt,[{'agent':'codex','scope':'user','home':str(home),'target':None,
                                    'installed_skills':['personal-sop-maintainer','old-child']}])
            self.run_installer(home,'--agent','codex','--apply',ok=False)
            self.run_installer(home,'--agent','codex','--migrate-from',str(old),'--apply')
            self.assertEqual(sop.read_json(installed/'.sop-root.json')['root'],str(self.source))
            self.assertEqual(sop.read_json(receipt),[])
            self.assertFalse(old_child.exists())
            self.assertTrue(list((home/'.agents/.personal-sop-disabled').glob('old-child-*')))
            self.assertTrue((old/'rules.md').is_file())


if __name__ == '__main__':
    unittest.main()
