# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

w0x7ce-skills is a personal Claude Code marketplace plugin for content publishing and automation. Skills use Chrome CDP for browser automation to post content to social platforms.

## Architecture

Skills are organized in `marketplace.json`:

```
skills/
└── w0x7ce-post-to-x/           # X (Twitter) publishing
    ├── SKILL.md                # Skill documentation
    ├── scripts/                # TypeScript implementations
    │   ├── x-browser.ts        # Regular posts (text + images)
    │   ├── x-video.ts          # Video posts
    │   └── x-article.ts        # Long-form articles
    └── references/             # Additional documentation
```

## Running Skills

All scripts run via Bun (no build step required):

```bash
# Regular tweet
npx -y bun skills/w0x7ce-post-to-x/scripts/x-browser.ts "Hello World!" --submit

# Tweet with images
npx -y bun skills/w0x7ce-post-to-x/scripts/x-browser.ts "Check this out" --image photo.png --submit

# Video tweet
npx -y bun skills/w0x7ce-post-to-x/scripts/x-video.ts "Amazing video" --video clip.mp4 --submit

# Long-form article (requires X Premium)
npx -y bun skills/w0x7ce-post-to-x/scripts/x-article.ts article.md --submit
```

## Key Dependencies

- **Bun**: TypeScript runtime (via `npx -y bun`)
- **Chrome**: Required for all posting skills (uses CDP automation)
- **No npm packages**: Self-contained TypeScript

## Authentication

All posting skills use Chrome CDP automation:
- First run opens Chrome for login
- Cookies/session cached in data directory
- No manual login required after first run

## Plugin Configuration

`.claude-plugin/marketplace.json` defines plugin metadata and skill paths. Version follows semver.

## Adding New Skills

**IMPORTANT**: All new skills MUST use `w0x7ce-` prefix to avoid conflicts.

1. Create `skills/w0x7ce-<name>/SKILL.md` with YAML front matter
   - Directory name: `w0x7ce-<name>`
   - SKILL.md `name` field: `w0x7ce-<name>`
2. Add TypeScript in `skills/w0x7ce-<name>/scripts/`
3. Add prompt templates in `skills/w0x7ce-<name>/prompts/` if needed
4. Register in `marketplace.json`

## Script Directory Template

Every SKILL.md with scripts MUST include this section:

```markdown
## Script Directory

**Important**: All scripts are located in the `scripts/` subdirectory.

**Agent Execution Instructions**:
1. Determine this SKILL.md file's directory path as `SKILL_DIR`
2. Script path = `${SKILL_DIR}/scripts/<script-name>.ts`
3. Replace all `${SKILL_DIR}` in this document with the actual path
```

## Code Style

- TypeScript throughout
- Async/await patterns
- Short variable names
- Type-safe interfaces
- Chrome CDP for automation

## Multi-language Support

All skills should support multiple interface languages. Include selectors for:
- English
- Simplified Chinese (简体中文)
- Traditional Chinese (繁體中文)
- Japanese (日本語)
- Korean (한국어)

Example:
```typescript
const I18N_SELECTORS = {
  titleInput: [
    'textarea[placeholder="Add a title"]',
    'textarea[placeholder="添加标题"]',
    'textarea[placeholder="加入標題"]',
  ],
};
```

## Extension Support

Every SKILL.md MUST include an Extension Support section:

```markdown
## Extension Support

Custom configurations via EXTEND.md.

**Check paths** (priority order):
1. `.w0x7ce-skills/<skill-name>/EXTEND.md` (project)
2. `~/.w0x7ce-skills/<skill-name>/EXTEND.md` (user)

If found, load before workflow. Extension content overrides defaults.
```

## Credits

This project is forked from [baoyu-skills](https://github.com/jimliu/baoyu-skills) with custom modifications for personal use.
