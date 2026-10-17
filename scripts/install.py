"""Preview or install the entry skill for Codex / Claude Code without copying rules."""
import argparse
import json
import os
import shutil
import tempfile
import contextlib
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MIGRATE_FROM = None
NAME = 'personal-sop-maintainer'
START = '<!-- personal-sop:begin -->'
END = '<!-- personal-sop:end -->'


def guidance(agent):
    return (START + '\n# 個人 SOP 維護入口\n\n'
            f'個人 SOP 維護來源：`{ROOT}`。\n'
            '在使用者要求總結、抽象或記錄 SOP，或重複工作與明確回饋適合形成可重用流程時，'
            f'使用 {"$" if agent == "codex" else "/"}{NAME}，閱讀來源的 rules.md。'
            '先完成當前工作；先交付 rules 草案，人明確確認後再建立對應子 Skill。'
            '有意義的 SOP 完善在必要檢查通過後自動提交本機 Git，只提交本次變更並回報 commit ID，不自動 push。'
            '提交後執行來源 scripts/sync.py，同步已授權的安裝目標；rules 草案不因此生效。'
            '不要因一次性操作就強行抽象，也不把其他平台規範套用到當前任務。\n'
            + END + '\n')


def instruction_text(path, agent):
    if path.is_symlink():
        raise ValueError('Refusing to modify a symlinked instruction file: ' + str(path))
    old = path.read_text(encoding='utf-8-sig') if path.exists() else ''
    if old.count(START) != old.count(END) or old.count(START) > 1:
        raise ValueError('Ambiguous existing SOP guidance markers: ' + str(path))
    if START in old and old.index(END) < old.index(START):
        raise ValueError('Reversed SOP guidance markers: ' + str(path))
    block = guidance(agent)
    if START in old:
        start = old.index(START)
        end = old.index(END) + len(END)
        return old[:start] + block.rstrip('\n') + old[end:]
    return old.rstrip('\n') + ('\n\n' if old else '') + block


def check_destination(destination):
    if destination.is_symlink():
        raise ValueError('Refusing to overwrite a symlinked skill.')
    owner = destination / '.sop-root.json'
    if destination.exists():
        if not owner.is_file():
            raise ValueError('Refusing to overwrite an unrelated skill: ' + str(destination))
        data = json.loads(owner.read_text(encoding='utf-8'))
        previous = Path(data['root']).resolve()
        migrating = MIGRATE_FROM is not None and previous == MIGRATE_FROM
        if previous != ROOT and not migrating:
            raise ValueError('Refusing to overwrite an unrelated skill: ' + str(destination))


def publish(source, destination, metadata):
    check_destination(destination)
    # Stage outside the skills discovery directory, on the same filesystem.
    agent_root = destination.parent.parent.resolve()
    if destination.resolve().parent != destination.parent.resolve():
        raise ValueError('Invalid destination boundary.')
    staging = agent_root / '.personal-sop-staging'
    staging.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=staging) as temp:
        prepared = Path(temp) / destination.name
        for file in source.rglob('*'):
            if file.is_symlink():
                raise ValueError('Symlinked skill resources are not supported.')
        shutil.copytree(source, prepared, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '.sop-root.json'))
        (prepared / '.sop-root.json').write_text(json.dumps(metadata, ensure_ascii=False) + '\n', encoding='utf-8')
        def content(directory):
            return {file.relative_to(directory).as_posix(): file.read_bytes() for file in directory.rglob('*')
                    if file.is_file() and file.name != '.sop-root.json' and '__pycache__' not in file.parts and file.suffix != '.pyc'}
        if destination.exists() and content(destination) == content(prepared):
            (destination/'.sop-root.json').write_bytes((prepared/'.sop-root.json').read_bytes())
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        backup = None
        if destination.exists():
            backups = agent_root / '.personal-sop-backups'
            backups.mkdir(exist_ok=True)
            backup = backups / (destination.name + '-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
            if not backup.resolve().is_relative_to(agent_root) or not destination.resolve().is_relative_to(agent_root):
                raise ValueError('Unsafe backup boundary.')
            destination.rename(backup)
        try:
            prepared.rename(destination)
        except OSError:
            if backup is not None:
                backup.rename(destination)
            raise


def install(agent, scope, home, target, with_guidance, apply, source_root=None, revision=None):
    if scope == 'project':
        if target is None:
            raise ValueError('--target is required for project scope.')
        base = target.resolve()
        destination = base / ('.agents' if agent == 'codex' else '.claude') / 'skills' / NAME
        instructions = base / ('AGENTS.md' if agent == 'codex' else 'CLAUDE.md')
    else:
        destination = home / ('.agents' if agent == 'codex' else '.claude') / 'skills' / NAME
        codex_home = Path(os.environ.get('CODEX_HOME', str(home / '.codex'))) if home == Path.home() else home / '.codex'
        instructions = (codex_home / 'AGENTS.md') if agent == 'codex' else home / '.claude' / 'CLAUDE.md'
    check_destination(destination)
    updated = instruction_text(instructions, agent) if with_guidance else None
    result = {'agent': agent, 'skill': str(destination), 'guidance': str(instructions) if with_guidance else None,
              'mode': 'applied' if apply else 'preview', 'source': str(ROOT)}
    if apply:
        publish((source_root or ROOT) / 'skills' / NAME, destination,
                {'root': str(ROOT), 'revision': revision, 'kind': 'entry'})
        if with_guidance:
            instructions.parent.mkdir(parents=True, exist_ok=True)
            if instructions.exists() and instructions.read_text(encoding='utf-8-sig') == updated:
                return result
            if instructions.exists():
                stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
                shutil.copy2(instructions, instructions.with_name(instructions.name + '.' + stamp + '.bak'))
            instructions.write_text(updated, encoding='utf-8')
    return result


def main():
    global ROOT, MIGRATE_FROM
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--agent', choices=['codex', 'claude', 'both'], default='codex')
    parser.add_argument('--root', type=Path, default=ROOT, help='Maintained Git repository root.')
    parser.add_argument('--migrate-from', type=Path, help='Explicitly transfer an owned entry and its receipt from this previous SOP repository.')
    parser.add_argument('--scope', choices=['user', 'project'], default='user')
    parser.add_argument('--target', type=Path)
    parser.add_argument('--home', type=Path, default=Path.home(), help='Override home for isolated verification.')
    parser.add_argument('--with-guidance', action='store_true', help='Add an owned block to AGENTS.md / CLAUDE.md, preserving existing text.')
    parser.add_argument('--apply', action='store_true', help='Without this option, only preview paths.')
    parser.add_argument('--registry', type=Path, help='Local installation registry, excluded from Git.')
    args = parser.parse_args()
    ROOT = args.root.resolve()
    MIGRATE_FROM = args.migrate_from.resolve() if args.migrate_from else None
    args.registry = args.registry or ROOT/'.local/installations.json'
    agents = ['codex', 'claude'] if args.agent == 'both' else [args.agent]
    try:
        if MIGRATE_FROM is not None and (MIGRATE_FROM == ROOT or not (MIGRATE_FROM/'skills'/NAME/'SKILL.md').is_file()):
            raise ValueError('--migrate-from must identify a different, existing SOP source.')
        # Preflight both targets before mutating either.
        plans = [install(a, args.scope, args.home.resolve(), args.target, args.with_guidance, False) for a in agents]
        results = plans
        if args.apply:
            from sync import snapshot, register, installation_key
            from locks import lock
            with contextlib.ExitStack() as stack:
                stack.enter_context(lock(ROOT, 'install'))
                if MIGRATE_FROM is not None:
                    stack.enter_context(lock(MIGRATE_FROM, 'finish'))
                    stack.enter_context(lock(MIGRATE_FROM, 'sync'))
                with snapshot(ROOT) as (source, revision):
                    results = [install(a, args.scope, args.home.resolve(), args.target, args.with_guidance, True, source, revision) for a in agents]
                for agent in agents:
                    register(args.registry, agent, args.scope, args.home.resolve(), args.target, args.with_guidance)
                if MIGRATE_FROM is not None:
                    from sop import read_json, write_json
                    old_registry = MIGRATE_FROM/'.local/installations.json'
                    old_records = read_json(old_registry) if old_registry.exists() else []
                    target = str(args.target.resolve()) if args.target else None
                    wanted = {installation_key({'agent':agent,'scope':args.scope,'home':str(args.home),'target':target}) for agent in agents}
                    def transferred(record):
                        return installation_key(record) in wanted
                    # Preserve the old owned child inventory so removed/stale
                    # children can be deactivated instead of left discoverable.
                    current = read_json(args.registry)
                    for record in current:
                        for previous in old_records:
                            if transferred(previous) and installation_key(record)==installation_key(previous):
                                record['installed_skills'] = previous.get('installed_skills',[NAME])
                    write_json(args.registry,current)
                    from sync import sync_all
                    sync_all(ROOT,args.registry,True,migrate_from=MIGRATE_FROM)
                    if old_registry.exists():
                        records = [r for r in old_records if not transferred(r)]
                        write_json(old_registry, records)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError) as exc:
        parser.exit(1, str(exc) + '\n')


if __name__ == '__main__':
    main()
