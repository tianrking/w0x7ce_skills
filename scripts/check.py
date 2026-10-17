"""Dependency-free structural checks; behavioral verification is done by tests."""
import re
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def validate(root):
    entries = list((root/'skills').rglob('SKILL.md'))
    for domain in root.iterdir():
        if domain.is_dir() and (domain/'state.json').is_file():
            entries.extend((domain/'skills').rglob('SKILL.md'))
    for entry in entries:
        text = entry.read_text(encoding='utf-8')
        header = re.match(r'\A---\n(.*?)\n---(?:\n|$)', text, re.S)
        if not header:
            raise ValueError('Missing frontmatter: ' + str(entry))
        if not re.search(r'^name:\s*' + re.escape(entry.parent.name) + r'\s*$', header.group(1), re.M):
            raise ValueError('Skill name must match folder: ' + str(entry))
        if not re.search(r'^description:\s*\S', header.group(1), re.M):
            raise ValueError('Missing description: ' + str(entry))
    manifest = root/'.claude-plugin/marketplace.json'
    if manifest.exists():
        for plugin in json.loads(manifest.read_text(encoding='utf-8'))['plugins']:
            for relative in plugin.get('skills', []):
                path = root/relative
                if not path.resolve().is_relative_to(root.resolve()) or not (path/'SKILL.md').is_file():
                    raise ValueError('Broken marketplace path: ' + relative)
    catalog = root/'docs/skill-catalog.json'
    if catalog.exists():
        for item in json.loads(catalog.read_text(encoding='utf-8')):
            path = root/item['path']
            if not path.resolve().is_relative_to(root.resolve()) or not (path/'SKILL.md').is_file():
                raise ValueError('Broken imported skill: ' + item['path'])
            for file in ['rules.md', 'state.json']:
                if not (root/item['platform']/file).is_file():
                    raise ValueError('Missing platform metadata: ' + item['platform'])
            if not (path/item['primary_script']).is_file():
                raise ValueError('Missing primary script: ' + item['name'])
    for entry in entries:
        for file in entry.parent.rglob('*.py'):
            if '__pycache__' not in file.parts:
                ast.parse(file.read_text(encoding='utf-8'), filename=str(file))
    print('Structural checks passed for', len(entries), 'skill(s).')


if __name__ == '__main__':
    validate(ROOT)
