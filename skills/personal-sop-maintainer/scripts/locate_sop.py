"""Resolve the maintained repository from source or an installed entry skill."""
import json
from pathlib import Path


def locate():
    skill = Path(__file__).resolve().parents[1]
    config = skill / '.sop-root.json'
    root = Path(json.loads(config.read_text(encoding='utf-8'))['root']) if config.exists() else skill.parents[1]
    root = root.resolve()
    if not (root / 'rules.md').is_file() or not (root / 'scripts' / 'sop.py').is_file():
        raise SystemExit('SOP source is unavailable; reinstall the entry skill from the maintained repository.')
    return root


if __name__ == '__main__':
    print(json.dumps({'root': str(locate())}, ensure_ascii=False))
