"""Track human-reviewed rules and the skills derived from their exact versions."""
import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESERVED = {'skills', 'scripts', 'tests', 'exports', 'tmp', 'docs'}


def digest(path):
    # Normalize text line endings so a Git checkout on another OS does not
    # invalidate an otherwise unchanged reviewed document.
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def tree_digest(path):
    hasher = hashlib.sha256()
    for file in sorted(path.rglob('*')):
        if '__pycache__' in file.parts or file.suffix == '.pyc':
            continue
        if file.is_symlink():
            raise ValueError('Skill resources must be regular files, not symlinks.')
        if file.is_file():
            hasher.update(file.relative_to(path).as_posix().encode('utf-8') + b'\0')
            data = file.read_bytes()
            try:
                data.decode('utf-8')
                if b'\0' not in data:
                    data = data.replace(b'\r\n', b'\n')
            except UnicodeDecodeError:
                pass
            hasher.update(hashlib.sha256(data).digest())
    return hasher.hexdigest()


def shared_digest(root):
    file = root / 'shared-rules.md'
    return digest(file) if file.exists() else None


def skill_current(root, path, skill, record, state):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', skill):
        return False
    entry = path / 'skills' / skill / 'SKILL.md'
    return (entry.is_file() and record.get('rules_sha256') == state['rules_sha256']
            and record.get('shared_rules_sha256') == shared_digest(root)
            and record.get('entry_sha256') == digest(entry)
            and record.get('tree_sha256') == tree_digest(entry.parent))


def checked_skill(root, name, skill):
    path = folder(root, name)
    state = confirmed(path)
    record = read_json(path/'skills-state.json').get(skill, {})
    if not skill_current(root, path, skill, record, state):
        raise ValueError('Child skill is stale or has unrecorded changes.')
    relevant = ['rules.md', 'shared-rules.md', name+'/rules.md', name+'/state.json',
                name+'/skills-state.json', name+'/skills/'+skill]
    result = subprocess.run(['git', '-C', str(root), 'status', '--porcelain', '--untracked-files=all',
                             '--', *relevant], capture_output=True, check=True)
    if result.stdout.strip():
        raise ValueError('Relevant source changes are not committed; finish validation and commit before using the global child skill.')
    return {'status': 'current', 'skill': skill}


def folder(root, name):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name) or name in RESERVED:
        raise ValueError('Use a non-reserved lowercase domain name, such as wechat or research-notes.')
    path = root / name
    if path.is_symlink() or path.resolve().parent != root.resolve():
        raise ValueError('Domain must be a direct, non-symlink child of the SOP root.')
    return path


def confirmed(path):
    state = read_json(path / 'state.json')
    if state.get('status') != 'approved' or state.get('rules_sha256') != digest(path / 'rules.md'):
        raise ValueError('Rules are draft or differ from the confirmed version; human review is required.')
    if not state.get('confirmation', {}).get('evidence', '').strip():
        raise ValueError('Missing human confirmation evidence.')
    return state


def init(root, name):
    path = folder(root, name)
    if path.exists():
        raise ValueError('Domain already exists. Review it or use draft; do not overwrite it.')
    path.mkdir()
    (path / 'rules.md').write_text(
        '# ' + name + ' 規範草案\n\n'
        '> 尚未經使用者確認，不能據此建立子 Skill。\n\n'
        '## 適用範圍\n\n待填寫：平台或任務領域，及不適用的情況。\n\n'
        '## 人的目標與偏好\n\n待填寫：已有依據的要求，避免把 AI 建議寫成定論。\n\n'
        '## 交付與驗收\n\n待填寫：完整輸出、資產與可觀察的驗收方式。\n\n'
        '## 待確認事項\n\n待填寫：未知事項、規範變更或需要人決定的取捨。\n', encoding='utf-8')
    write_json(path / 'state.json', {'status': 'draft', 'rules_sha256': None, 'confirmation': None})
    return {'status': 'draft', 'file': str(path / 'rules.md')}


def draft(root, name):
    path = folder(root, name)
    state = read_json(path / 'state.json')
    if state.get('status') != 'approved':
        return {'status': 'draft', 'file': str(path / 'rules.md')}
    confirmed(path)
    target = path / 'rules.draft.md'
    if not target.exists():
        target.write_bytes((path / 'rules.md').read_bytes())
    return {'status': 'pending-review', 'file': str(target)}


def approve(root, name, evidence):
    path = folder(root, name)
    evidence = evidence.strip()
    if not evidence:
        raise ValueError('Record actual explicit user confirmation, not a fabricated approval.')
    state = read_json(path / 'state.json')
    candidate = path / 'rules.draft.md'
    if not candidate.exists():
        candidate = path / 'rules.md'
        if state.get('status') == 'approved' and state.get('rules_sha256') == digest(candidate):
            raise ValueError('Already approved; no pending draft to approve.')
    text = candidate.read_text(encoding='utf-8')
    if '待填寫：' in text:
        raise ValueError('Complete the rules draft before presenting it for approval.')
    data = candidate.read_bytes()
    (path / 'rules.md').write_bytes(data)
    write_json(path / 'state.json', {
        'status': 'approved', 'rules_sha256': digest(path / 'rules.md'),
        'confirmation': {'evidence': evidence, 'recorded_at': datetime.now(timezone.utc).isoformat()}
    })
    if candidate.name == 'rules.draft.md':
        candidate.unlink()
    return {'status': 'approved', 'rules_sha256': digest(path / 'rules.md'), 'next': 'Build or update the child skill after validation.'}


def record_skill(root, name, skill):
    path = folder(root, name)
    state = confirmed(path)
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', skill):
        raise ValueError('Invalid skill name.')
    entry = path / 'skills' / skill / 'SKILL.md'
    if not entry.is_file() or not entry.resolve().is_relative_to(path.resolve()):
        raise ValueError('Create a child SKILL.md inside this domain first.')
    index = path / 'skills-state.json'
    records = read_json(index) if index.exists() else {}
    records[skill] = {'rules_sha256': state['rules_sha256'], 'entry_sha256': digest(entry),
                      'tree_sha256': tree_digest(entry.parent), 'shared_rules_sha256': shared_digest(root)}
    write_json(index, records)
    return {'skill': skill, 'status': 'recorded', 'behavior_tested': False}


def status(root):
    rows = []
    for path in sorted(root.iterdir()):
        if not path.is_dir() or not (path / 'state.json').is_file():
            continue
        try:
            state = confirmed(path)
            skills = read_json(path / 'skills-state.json') if (path / 'skills-state.json').exists() else {}
            rows.append({'domain': path.name, 'status': 'approved',
                         'pending_draft': (path / 'rules.draft.md').exists(),
                         'skills': {key: 'current' if skill_current(root, path, key, value, state)
                                    else 'needs-sync' for key, value in skills.items()}})
        except (ValueError, KeyError, OSError) as exc:
            rows.append({'domain': path.name, 'status': 'draft-or-unconfirmed', 'detail': str(exc)})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT, help='SOP repository root (also useful for isolated testing).')
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('status')
    for name in ['init', 'draft', 'check', 'check-skill', 'approve', 'record-skill']:
        command = commands.add_parser(name)
        command.add_argument('domain')
        if name == 'approve':
            command.add_argument('--evidence', required=True)
        if name in {'record-skill', 'check-skill'}:
            command.add_argument('skill')
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.command == 'status': result = status(root)
        elif args.command == 'init': result = init(root, args.domain)
        elif args.command == 'draft': result = draft(root, args.domain)
        elif args.command == 'approve': result = approve(root, args.domain, args.evidence)
        elif args.command == 'record-skill': result = record_skill(root, args.domain, args.skill)
        elif args.command == 'check-skill':
            if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', args.skill):
                raise ValueError('Invalid skill name.')
            result = checked_skill(root, args.domain, args.skill)
        else: result = confirmed(folder(root, args.domain))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
