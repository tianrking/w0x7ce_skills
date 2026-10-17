# w0x7ce Skills — Personal SOP

[繁體中文](README.md)

Human-readable rules describe intent. Draft rules first, obtain explicit confirmation of the specific version, then implement and validate skills. Meaningful changes are committed locally and synced to registered installations. Remote pushes remain separately authorized.

Five existing publishing skills are preserved under x/, linkedin/, xiaohongshu/ and tencent-docs/. Newly extracted platform rules remain drafts; WeChat delivery rules are also included as a draft. The previously confirmed VPS initialization skill is preserved under vps/. The maintenance entry is skills/personal-sop-maintainer/.

## Install

Requires Python 3.10+ and Git; management scripts use only the standard library.

```sh
git clone https://github.com/tianrking/w0x7ce_skills.git
cd w0x7ce_skills
python scripts/install.py --agent codex --scope user --with-guidance
python scripts/install.py --agent codex --scope user --with-guidance --apply
```

The first install previews changes. The second installs the entry to ~/.agents/skills/ and adds an owned guidance block to ~/.codex/AGENTS.md. Use $personal-sop-maintainer. Existing conversations may need to reread instructions or restart.

Use --agent claude for Claude Code. The marketplace offers sop-maintenance, publishing-skills compatibility entries requiring confirmed rules, and infrastructure-skills for the existing VPS workflow. Plugin installation is not registered with the Python sync tool automatically.

## Maintain

```sh
python scripts/sop.py status
python scripts/sop.py init new-platform
python scripts/sop.py draft existing-platform
# Only after actual human confirmation:
python scripts/sop.py approve existing-platform --evidence "Explicit confirmation"
# Validate the skill, then record its full resource fingerprint:
python scripts/sop.py record-skill existing-platform skill-name
python scripts/finish.py --message "Describe the improvement" --files path/to/changed-file.md
```

Finish validates, commits explicit paths and syncs from HEAD. Unrelated staging is preserved. Drafts do not become active rules. Stale skills are moved outside discovery; failed sync keeps successful commits. Retry with python scripts/sync.py --apply.

Use --migrate-from /path/to/old-sop to transfer an owned installation and retire its matching receipt. Old source files are preserved.

## Verify

```sh
python scripts/check.py
python -m unittest discover -s tests -v
```

Tests are offline, not proof of account-side publishing. Publishing dependencies remain workflow-specific: Bun and Chrome for local CDP; Playwright for remote Python. Credentials and browser state stay local. See [migration notes](docs/migration.md). MIT and upstream attribution are preserved.
