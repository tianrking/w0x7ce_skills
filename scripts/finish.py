"""Validate, commit explicit SOP files, then sync authorized installations from HEAD."""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import sop
from sync import git, sync_all
from locks import lock

ROOT = Path(__file__).resolve().parents[1]


def validate(root):
    subprocess.run([sys.executable, str(root/'scripts/check.py')], cwd=root, check=True)
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=root, check=True)


def finish(root, files, message, registry=None, validator=validate):
    with lock(root, 'finish'):
        return _finish(root, files, message, registry, validator)


def _finish(root, files, message, registry, validator):
    root = root.resolve()
    if Path(git(root, 'rev-parse', '--show-toplevel')).resolve() != root:
        raise ValueError('Run against the SOP Git root, not an enclosing repository.')
    if not message.strip():
        raise ValueError('A meaningful commit message is required.')
    paths = []
    for name in files:
        file = root/name
        if (Path(name).is_absolute() or not file.resolve().is_relative_to(root)
                or file.is_dir() or file.is_symlink()
                or any(part in {'.git', '.local', '__pycache__', 'exports', 'tmp'} for part in Path(name).parts)):
            raise ValueError('Select explicit SOP files inside this repository: ' + name)
        if not file.exists():
            git(root, 'ls-files', '--error-unmatch', '--', ':(literal)' + name)
        paths.append(file.relative_to(root).as_posix())
    if not paths:
        raise ValueError('Explicit --files are required; do not stage the whole repository.')
    literals = [':(literal)' + name for name in sorted(set(paths))]
    before = {name: (root/name).read_bytes() if (root/name).exists() else None for name in paths}
    subprocess.run(['git', '-C', str(root), 'diff', '--check', 'HEAD', '--', *literals], check=True)
    validator(root)
    if any(((root/name).read_bytes() if (root/name).exists() else None) != data for name, data in before.items()):
        raise ValueError('Validation changed selected files; inspect and rerun before committing.')
    changed = git(root, 'status', '--porcelain', '--', *literals)
    if changed:
        # --only preserves unrelated staged content instead of including it.
        subprocess.run(['git', '-C', str(root), 'var', 'GIT_AUTHOR_IDENT'], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(['git', '-C', str(root), 'add', '--', *literals], check=True)
        subprocess.run(['git', '-C', str(root), 'commit', '--only', '-m', message, '--', *literals], check=True)
    # If synchronization fails the successful commit remains; retry sync.py.
    result = sync_all(root, registry, True)
    result['committed'] = bool(changed)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--message', required=True)
    parser.add_argument('--files', nargs='+', required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(finish(ROOT, args.files, args.message), ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        parser.exit(1, 'Finish failed; preserve changes and inspect the cause: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
