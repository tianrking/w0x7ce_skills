# w0x7ce-skills

English | [中文](./README.zh.md)

Personal skills for content publishing and automation with Claude Code.

## Features

- **Post to X (Twitter)**: Publish tweets, images, videos, and long-form articles
- **Multi-language Support**: English, Simplified Chinese, Traditional Chinese
- **Chrome Automation**: Uses real Chrome with CDP to bypass anti-bot detection

## Prerequisites

- Google Chrome installed
- Node.js environment installed
- Ability to run `npx bun` commands

## Installation

### Local Installation

```bash
# Clone or copy this project to your local machine
cd /path/to/w0x7ce-skills

# Register as plugin marketplace in Claude Code
/plugin marketplace add /path/to/w0x7ce-skills
```

### Install Skills

```bash
# Install publishing skills
/plugin install publishing-skills@w0x7ce-skills
```

## Available Skills

### w0x7ce-post-to-x

Post content, images, videos, and long-form articles to X (Twitter).

#### Regular Posts (Tweets)

Text + up to 4 images.

```bash
# Preview mode (doesn't post)
npx -y bun skills/w0x7ce-post-to-x/scripts/x-browser.ts "Hello from Claude!" --image ./screenshot.png

# Actually post
npx -y bun skills/w0x7ce-post-to-x/scripts/x-browser.ts "Hello!" --image ./photo.png --submit

# Multiple images
npx -y bun skills/w0x7ce-post-to-x/scripts/x-browser.ts "Check this out" --image img1.png --image img2.png --submit
```

#### Video Posts

Text + video file (MP4, MOV, WebM).

```bash
# Preview mode
npx -y bun skills/w0x7ce-post-to-x/scripts/x-video.ts "Check out this video!" --video ./clip.mp4

# Publish
npx -y bun skills/w0x7ce-post-to-x/scripts/x-video.ts "Amazing content" --video ./demo.mp4 --submit
```

#### X Articles (Long-form)

Requires X Premium subscription.

```bash
# Preview mode
npx -y bun skills/w0x7ce-post-to-x/scripts/x-article.ts article.md

# With cover image
npx -y bun skills/w0x7ce-post-to-x/scripts/x-article.ts article.md --cover ./cover.jpg

# Publish
npx -y bun skills/w0x7ce-post-to-x/scripts/x-article.ts article.md --submit
```

## Usage

### First Time Setup

1. Run any post command
2. Chrome will open and navigate to X (Twitter)
3. Log in with your X account
4. Session will be saved for future use

### Parameters

| Parameter | Description |
|-----------|-------------|
| `<text>` | Post content (positional argument) |
| `--image <path>` | Image file path (can repeat, max 4) |
| `--video <path>` | Video file path |
| `--submit` | Actually post (default: preview only) |
| `--profile <dir>` | Custom Chrome profile directory |

## Language Support

The skills automatically detect and support multiple interface languages:

- English
- Simplified Chinese (简体中文)
- Traditional Chinese (繁體中文)
- Japanese (日本語)
- Korean (한국어)

## Troubleshooting

- **Not logged in**: First run opens Chrome - scan QR code to log in, session is preserved
- **Chrome not found**: Set `X_BROWSER_CHROME_PATH` environment variable
- **Editor not found (Articles)**: Ensure you have X Premium and are logged in

## Project Structure

```
w0x7ce-skills/
├── .claude-plugin/
│   └── marketplace.json          # Plugin configuration
├── skills/
│   └── w0x7ce-post-to-x/         # X (Twitter) publishing skill
│       ├── SKILL.md              # Skill documentation
│       ├── scripts/              # TypeScript scripts
│       │   ├── x-browser.ts      # Regular posts
│       │   ├── x-video.ts        # Video posts
│       │   └── x-article.ts      # Long-form articles
│       └── references/           # Additional documentation
├── README.md                     # This file
└── README.zh.md                  # Chinese version
```

## Disclaimer

This project uses Chrome automation to interact with social media platforms. Use responsibly and in accordance with the platforms' terms of service.

## License

MIT

---

**Note**: This is a personal project forked from [baoyu-skills](https://github.com/jimliu/baoyu-skills) with custom modifications.
