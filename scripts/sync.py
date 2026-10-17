"""Publish committed SOP entrypoints only to previously authorized installations."""
import argparse
import contextlib
import io
import json
import re
import subprocess
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

import install as installer
import sop
from locks import lock

ROOT = Path(__file__).resolve().parents[1]


def git(root, *args, binary=False):
    result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, check=True)
    return result.stdout if binary else result.stdout.decode('utf-8').strip()


@contextlib.contextmanager
def snapshot(root):
    revision = git(root, 'rev-parse', 'HEAD')
    archive = git(root, 'archive', '--format=tar', revision, binary=True)
    with tempfile.TemporaryDirectory(prefix='personal-sop-snapshot-') as temp:
        destination = Path(temp)
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            for member in tar:
                file = destination / member.name
                if not file.resolve().is_relative_to(destination.resolve()):
                    raise ValueError('Unsafe Git archive member.')
                if member.isdir():
                    file.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    file.parent.mkdir(parents=True, exist_ok=True)
                    file.write_bytes(tar.extractfile(member).read())
                else:
                    raise ValueError('Git snapshots must not contain symlinks or special files.')
        yield destination, revision


def installation_key(record):
    return (record['agent'], record['scope'], str(Path(record['home']).resolve()),
            str(Path(record['target']).resolve()) if record['target'] else None)


def register(registry, agent, scope, home, target, with_guidance):
    records = sop.read_json(registry) if registry.exists() else []
    record = {'agent': agent, 'scope': scope, 'home': str(home.resolve()),
              'target': str(target.resolve()) if target else None, 'with_guidance': with_guidance}
    key = installation_key(record)
    for previous in records:
        if installation_key(previous) == key:
            record['installed_skills'] = previous.get('installed_skills', [installer.NAME])
            records.remove(previous)
            break
    record.setdefault('installed_skills', [installer.NAME])
    records.append(record)
    registry.parent.mkdir(parents=True, exist_ok=True)
    sop.write_json(registry, records)


def available(source):
    active = {}
    blocked = []
    for domain in sorted(source.iterdir()):
        if not domain.is_dir() or not (domain / 'state.json').is_file():
            continue
        try:
            state = sop.confirmed(domain)
        except (ValueError, OSError, KeyError) as exc:
            blocked.append({'domain': domain.name, 'reason': str(exc)})
            continue
        records = sop.read_json(domain/'skills-state.json') if (domain/'skills-state.json').exists() else {}
        for name, record in records.items():
            if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name) or name == installer.NAME:
                raise ValueError('Invalid or reserved child skill name: ' + name)
            if not sop.skill_current(source, domain, name, record, state):
                blocked.append({'domain': domain.name, 'skill': name, 'reason': 'Unrecorded changes or stale rules/resources.'})
                continue
            if name in active:
                raise ValueError('Two domains publish the same global skill name: ' + name)
            active[name] = domain.name
    return active, blocked


def child_wrapper(source, root, domain, name):
    original = source/domain/'skills'/name/'SKILL.md'
    text = original.read_text(encoding='utf-8')
    front = re.match(r'\A---\r?\n.*?\r?\n---(?:\r?\n|$)', text, re.S)
    if not front:
        raise ValueError('Missing skill frontmatter: ' + name)
    directory = source/'.wrappers'/name
    directory.mkdir(parents=True, exist_ok=True)
    content = (front.group(0) + '\n# 個人 SOP 子 Skill 入口\n\n'
               f'維護來源：`{root}`。先執行來源的 `scripts/sop.py check-skill {domain} {name}`，'
               '確認失敗則說明狀態並停止使用此子 Skill，不將草案視為已確認。\n\n'
               f'檢查通過後閱讀 `{root / "rules.md"}`、`{root / "shared-rules.md"}`、'
               f'`{root / domain / "rules.md"}` 和 `{root / domain / "skills" / name / "SKILL.md"}`。'
               '依來源最新流程執行，所有 Skill 相對資源路徑以來源 Skill 目錄為基準。'
               '需要完善 SOP 時使用根目錄維護 Skill；rules 仍先由人確認。\n')
    (directory/'SKILL.md').write_text(content, encoding='utf-8')
    return directory


def deactivate(destination):
    installer.check_destination(destination)
    if not destination.exists():
        return
    agent_root = destination.parent.parent.resolve()
    disabled = agent_root/'.personal-sop-disabled'
    disabled.mkdir(exist_ok=True)
    target = disabled/(destination.name + '-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    if not destination.resolve().is_relative_to(agent_root) or not target.resolve().is_relative_to(agent_root):
        raise ValueError('Unsafe deactivation boundary.')
    destination.rename(target)


def sync_all(root=ROOT, registry=None, apply=False, migrate_from=None):
    with lock(root, 'sync'):
        return _sync_all(root, registry, apply, migrate_from)


def _sync_all(root, registry, apply, migrate_from):
    root = root.resolve()
    registry = registry or root/'.local/installations.json'
    records = sop.read_json(registry) if registry.exists() else []
    old_root = installer.ROOT
    old_migration = installer.MIGRATE_FROM
    installer.ROOT = root
    installer.MIGRATE_FROM = Path(migrate_from).resolve() if migrate_from else None
    try:
        with snapshot(root) as (source, revision):
            active, blocked = available(source)
            wrappers = {name: child_wrapper(source, root, domain, name) for name, domain in active.items()}
            plans = []
            for record in records:
                args = (record['agent'], record['scope'], Path(record['home']),
                        Path(record['target']) if record['target'] else None, record['with_guidance'])
                plan = installer.install(*args, False)
                base = Path(plan['skill']).parent
                retired = set(record.get('installed_skills', [])) - {installer.NAME} - set(active)
                for name in set(active) | retired:
                    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name):
                        raise ValueError('Invalid installed skill name.')
                    installer.check_destination(base/name)
                plans.append((record, args, plan, base, retired))
            # All ownership/conflict checks above happen before publishing.
            output = []
            for record, args, plan, base, retired in plans:
                if apply:
                    installer.install(*args, True, source, revision)
                    for name, directory in wrappers.items():
                        installer.publish(directory, base/name,
                                          {'root': str(root), 'revision': revision, 'kind': 'child', 'domain': active[name]})
                    for name in retired:
                        deactivate(base/name)
                    record['installed_skills'] = [installer.NAME, *sorted(active)]
                    record['revision'] = revision
                output.append({'agent': record['agent'], 'scope': record['scope'], 'entry': plan['skill'],
                               'child_skills': sorted(active), 'deactivated': sorted(retired)})
            if apply and records:
                sop.write_json(registry, records)
            return {'revision': revision, 'applied': apply, 'targets': output, 'blocked': blocked}
    finally:
        installer.ROOT = old_root
        installer.MIGRATE_FROM = old_migration


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--registry', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(sync_all(registry=args.registry, apply=args.apply), ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
