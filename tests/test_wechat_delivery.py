import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT/'wechat-official-account/skills/w0x7ce-wechat-official-account'
spec = importlib.util.spec_from_file_location('wechat_packager', SKILL/'scripts/package_article.py')
packager = importlib.util.module_from_spec(spec)
spec.loader.exec_module(packager)


class WechatDeliveryTests(unittest.TestCase):
    def prepare(self, root):
        source = root/'input'
        (source/'images').mkdir(parents=True)
        shutil.copy2(ROOT/'tests/fixtures/test-image.png', source/'images/cover.png')
        (source/'article.md').write_text('# 測試題目 & 條件\n\n完整正文。\n\n![圖說](images/cover.png)\n', encoding='utf-8')
        (source/'body.html').write_text('<p style="line-height:1.8">完整正文。</p><figure><img src="images/cover.png"><figcaption>圖說</figcaption></figure>', encoding='utf-8')
        return source

    def test_portable_package_survives_relocation_and_keeps_original_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.prepare(root)
            output = root/'delivery'
            packager.package(source, 'images/cover.png', output)
            page = (output/'article.html').read_text(encoding='utf-8')
            self.assertIn('data:image/png;base64,', page)
            self.assertNotIn('src="images/', page)
            self.assertIn('測試題目 &amp; 條件', page)
            with zipfile.ZipFile(output/'source.zip') as archive:
                archive.extractall(root/'relocated')
            moved = root/'relocated/source'
            self.assertEqual((source/'article.md').read_bytes(), (moved/'article.md').read_bytes())
            self.assertEqual((source/'images/cover.png').read_bytes(), (moved/'images/cover.png').read_bytes())
            self.assertEqual((output/'cover.png').read_bytes(), (moved/'images/cover.png').read_bytes())
            manifest = json.loads((output/'manifest.json').read_text(encoding='utf-8'))
            for name, digest in manifest['sha256'].items():
                self.assertEqual(packager.hashlib.sha256((output/name).read_bytes()).hexdigest(), digest)

    def test_invalid_assets_and_executable_fragments_fail_without_output(self):
        for fragment in ['<img src="https://example.com/a.png">', '<img src="../secret.png">',
                         '<img src="images/missing.png">', '<script>alert(1)</script>',
                         '<p onclick="alert(1)">bad</p>', '<p style="background:url(https://example.com)">bad</p>']:
            with self.subTest(fragment=fragment), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                source = self.prepare(root)
                (source/'body.html').write_text(fragment, encoding='utf-8')
                with self.assertRaises(ValueError):
                    packager.package(source, 'images/cover.png', root/'delivery')
                self.assertFalse((root/'delivery').exists())

    def test_existing_delivery_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = self.prepare(root)
            output = root/'delivery'
            output.mkdir()
            (output/'keep.txt').write_text('keep', encoding='utf-8')
            with self.assertRaises(ValueError):
                packager.package(source, 'images/cover.png', output)
            self.assertEqual((output/'keep.txt').read_text(), 'keep')


if __name__ == '__main__':
    unittest.main()
