import importlib.util
import os
import runpy
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
REMOTE = ROOT/'xiaohongshu/skills/w0x7ce-xhs-browserless'


class MigrationTests(unittest.TestCase):
    def test_metadata_is_trackable_but_real_session_files_are_ignored(self):
        for name in ['x/state.json', 'docs/skill-catalog.json', 'tests/fixtures/test-image.png']:
            result = subprocess.run(['git','-C',str(ROOT),'check-ignore','--no-index',name],capture_output=True)
            self.assertNotEqual(result.returncode,0,name)
        for name in ['xiaohongshu/skills/w0x7ce-xhs-browserless/.env',
                     'xiaohongshu/skills/w0x7ce-xhs-browserless/cookies.txt',
                     'xiaohongshu/skills/w0x7ce-xhs-browserless/xhs_browser_state.json',
                     '.local/installations.json']:
            result = subprocess.run(['git','-C',str(ROOT),'check-ignore','--no-index',name],capture_output=True)
            self.assertEqual(result.returncode,0,name)

    def test_missing_remote_endpoint_never_opens_a_browser(self):
        fake = types.ModuleType('playwright.sync_api')
        def forbidden(): raise AssertionError('No browser should be opened')
        fake.sync_playwright = forbidden
        with patch.dict(sys.modules,{'playwright':types.ModuleType('playwright'),'playwright.sync_api':fake}), \
             patch.dict(os.environ,{'XHS_WS_URL':'','XHS_SCREENSHOTS':''}):
            login = runpy.run_path(str(REMOTE/'xhs_login.py'),run_name='offline_fixture')
            publish = runpy.run_path(str(REMOTE/'scripts/xhs_publish.py'),run_name='offline_fixture')
            with self.assertRaises(ValueError): login['require_endpoint']()
            with self.assertRaises(ValueError): publish['publish_note']('title','body','missing.png')
            self.assertEqual(Path(login['STATE_FILE']).resolve(),Path(publish['STATE_FILE']).resolve())

    def test_invalid_plugin_path_is_rejected(self):
        spec=importlib.util.spec_from_file_location('sop_structure_check',ROOT/'scripts/check.py')
        module=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'.claude-plugin').mkdir()
            (root/'.claude-plugin/marketplace.json').write_text('{"plugins":[{"skills":["./missing-skill"]}]}',encoding='utf-8')
            with self.assertRaises(ValueError): module.validate(root)


if __name__=='__main__':
    unittest.main()
