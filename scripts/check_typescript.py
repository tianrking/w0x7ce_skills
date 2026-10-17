"""Compile existing TypeScript without executing browser/publishing scripts."""
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    bun=shutil.which('bun')
    if not bun:
        raise SystemExit('Bun is required for this separate TypeScript syntax check.')
    entries=[]
    for name in ['x','linkedin','xiaohongshu','tencent-docs']:
        entries.extend(sorted((ROOT/name).rglob('*.ts')))
    with tempfile.TemporaryDirectory(prefix='w0x7ce-ts-check-') as temp:
        subprocess.run([bun,'build',*[str(file) for file in entries],'--target=bun','--packages=external','--outdir',temp],
                       cwd=ROOT,check=True)
    print('Compiled',len(entries),'TypeScript files without running them.')


if __name__=='__main__':
    main()
