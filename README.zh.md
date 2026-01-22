# w0x7ce-skills

[English](./README.md) | 中文

个人使用的内容发布和自动化技能集合，用于 Claude Code。

## 功能特性

- **发布到 X (Twitter)**：发布推文、图片、视频和长文章
- **多语言支持**：英语、简体中文、繁体中文
- **Chrome 自动化**：使用真实 Chrome 和 CDP 绕过反机器人检测

## 前置要求

- 已安装 Google Chrome
- 已安装 Node.js 环境
- 能够运行 `npx bun` 命令

## 安装

### 本地安装

```bash
# 将项目克隆或复制到本地
cd /path/to/w0x7ce-skills

# 在 Claude Code 中注册为插件市场
/plugin marketplace add /path/to/w0x7ce-skills
```

### 安装技能

```bash
# 安装发布技能
/plugin install publishing-skills@w0x7ce-skills
```

## 可用技能

### w0x7ce-post-to-x

发布内容、图片、视频和长文章到 X (Twitter)。

#### 普通推文

文字 + 最多 4 张图片。

```bash
# 预览模式（不会真正发布）
npx -y bun skills/w0x7ce-post-to-x/scripts/x-browser.ts "Hello from Claude!" --image ./screenshot.png

# 真正发布
npx -y bun skills/w0x7ce-post-to-x/scripts/x-browser.ts "Hello!" --image ./photo.png --submit

# 多张图片
npx -y bun skills/w0x7ce-post-to-x/scripts/x-browser.ts "Check this out" --image img1.png --image img2.png --submit
```

#### 视频推文

文字 + 视频文件（MP4、MOV、WebM）。

```bash
# 预览模式
npx -y bun skills/w0x7ce-post-to-x/scripts/x-video.ts "Check out this video!" --video ./clip.mp4

# 发布
npx -y bun skills/w0x7ce-post-to-x/scripts/x-video.ts "Amazing content" --video ./demo.mp4 --submit
```

#### X 长文章

需要 X Premium 订阅。

```bash
# 预览模式
npx -y bun skills/w0x7ce-post-to-x/scripts/x-article.ts article.md

# 带封面图
npx -y bun skills/w0x7ce-post-to-x/scripts/x-article.ts article.md --cover ./cover.jpg

# 发布
npx -y bun skills/w0x7ce-post-to-x/scripts/x-article.ts article.md --submit
```

## 使用方法

### 首次设置

1. 运行任意发布命令
2. Chrome 会打开并导航到 X (Twitter)
3. 使用你的 X 账号登录
4. 会话会被保存供后续使用

### 参数说明

| 参数 | 说明 |
|------|------|
| `<text>` | 推文内容（位置参数） |
| `--image <path>` | 图片文件路径（可重复，最多 4 张） |
| `--video <path>` | 视频文件路径 |
| `--submit` | 真正发布（默认为预览模式） |
| `--profile <dir>` | 自定义 Chrome 配置目录 |

## 语言支持

技能会自动检测并支持多种界面语言：

- 英语
- 简体中文
- 繁體中文
- 日本語
- 한국어

## 故障排除

- **未登录**：首次运行会打开 Chrome - 扫码登录，会话会被保存
- **找不到 Chrome**：设置 `X_BROWSER_CHROME_PATH` 环境变量
- **找不到编辑器（文章）**：确保你有 X Premium 且已登录

## 项目结构

```
w0x7ce-skills/
├── .claude-plugin/
│   └── marketplace.json          # 插件配置
├── skills/
│   └── w0x7ce-post-to-x/         # X (Twitter) 发布技能
│       ├── SKILL.md              # 技能文档
│       ├── scripts/              # TypeScript 脚本
│       │   ├── x-browser.ts      # 普通推文
│       │   ├── x-video.ts        # 视频推文
│       │   └── x-article.ts      # 长文章
│       └── references/           # 附加文档
├── README.md                     # 英文说明
└── README.zh.md                  # 中文说明（本文件）
```

## 免责声明

本项目使用 Chrome 自动化与社交媒体平台交互。请负责任地使用，并遵守平台的服务条款。

## 许可证

MIT

---

**注意**：这是从 [baoyu-skills](https://github.com/jimliu/baoyu-skills) 分支的个人项目，包含自定义修改。
