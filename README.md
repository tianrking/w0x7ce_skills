# w0x7ce Skills｜個人 SOP 與平台工作流程

繁體中文 · [English](README.en.md) · [遷移記錄](docs/migration.md)

人描述工作規範，Agent 將已確認規範落實為 Skill。先從實際需求整理 rules，確認具體版本後再完善流程，不將單篇案例當成所有平台的固定模板。

```text
實際任務 → rules 草案 → 人確認 → Skill 實作與驗證
                                      ↓
                         本機 commit → 同步已授權全域目標
```

## 專案結構

```text
w0x7ce_skills/
├── AGENTS.md、CLAUDE.md         Agent 閱讀入口
├── rules.md                    SOP 維護規範
├── shared-rules.md             跨平台共同原則
├── skills/personal-sop-maintainer/
├── scripts/                    確認、驗證、提交、安裝與同步
├── x/                          X 文字、圖片、影片及長文
├── linkedin/                   LinkedIn 文字及圖片
├── xiaohongshu/                本機 Chrome／遠端 Browserless
├── tencent-docs/               騰訊文字文件
├── wechat/                     微信文章交付規範
├── vps/                        已確認的 VPS 初始化基線
├── docs/                       遷移記錄及原有 Skill 目錄
├── tests/                      離線測試及素材
└── .claude-plugin/marketplace.json
```

各平台或任務領域有 `rules.md`、`state.json` 及自己的 `skills/`。五個既有發布 Skill 名稱與實作保留，新的平台發布 Skill 延用 `w0x7ce-` 前綴；根維護入口及既有 `vps-initialize` 保持原名。

## 目前狀態

| 平台 | 原有流程 | 規範狀態 |
|---|---|---|
| X | w0x7ce-post-to-x | 匯入待確認 |
| LinkedIn | w0x7ce-post-to-linkedin | 匯入待確認 |
| 小紅書 | w0x7ce-post-to-rednote、w0x7ce-xhs-browserless | 匯入待確認 |
| 騰訊文件 | w0x7ce-post-to-tencent-docs | 匯入待確認 |
| 微信公眾號 | 完整 HTML、複製按鈕、Markdown＋相對圖片及封面 | 待確認；尚無子 Skill |
| VPS | vps-initialize：初始化及網路工具僅預裝 | 沿用已確認版本與資源記錄 |

結構遷移與 Git 提交不代表規範獲批，也不代表已重新登入或驗證發布。初次 install 建立根維護入口，後續 sync 會發布已確認且版本有效的子 Skill，目前包括 VPS；新發布平台子 Skill 須先確認。

## 安裝到 Codex

SOP 工具需要 Python 3.10+ 與 Git，只使用 Python 標準函式庫。clone 到長期保存的位置：

```sh
git clone https://github.com/tianrking/w0x7ce_skills.git
cd w0x7ce_skills
python scripts/install.py --agent codex --scope user --with-guidance
python scripts/install.py --agent codex --scope user --with-guidance --apply
```

第一條 install 只預覽，第二條執行。入口放入 `~/.agents/skills/personal-sop-maintainer/`，短閱讀指令加入 `~/.codex/AGENTS.md`（跟隨 CODEX_HOME），保留既有內容。省略 `--with-guidance` 可只安裝 Skill。

以 `$personal-sop-maintainer` 明確呼叫。自動選用取決於宿主與描述匹配；既有對話可能需要重新讀取或重開，這不是背景監控服務。

安裝副本指向唯一的 Git 維護來源。從先前 SOP 倉庫遷移時：

```sh
python scripts/install.py --agent codex --scope user --with-guidance --migrate-from /path/to/old-sop --apply
```

只接管舊來源擁有的同名入口，保留舊檔案，移除舊來源相應同步登記，避免兩個倉庫覆蓋同一入口。非本專案 Skill 不覆蓋。

## Claude Code

可另行使用 `--agent claude --scope user --with-guidance --apply` 安裝並登記同步。也保留 marketplace：

```text
/plugin marketplace add tianrking/w0x7ce_skills
/plugin install sop-maintenance@w0x7ce-skills
```

原 `publishing-skills` 插件名稱保留，包含五個遷移入口，執行前仍檢查規範狀態。插件安裝不等於規範確認，也不會自動加入 Python 同步器的登記。不要在同一宿主重複安裝同名入口。

## 建立及維護規範

```sh
python scripts/sop.py status
python scripts/sop.py init new-platform
python scripts/sop.py draft existing-platform
```

新增先寫完整草案；既有規範的變更寫入 `rules.draft.md`，保留生效版本。向人展示具體版本，只有明確確認後才記錄：

```sh
python scripts/sop.py approve x --evidence "對完整規範的明確確認依據"
# 驗證並完善 Skill，再記錄全部資源與規範版本
python scripts/sop.py record-skill x w0x7ce-post-to-x
```

指紋不是人類身分驗證。Agent 不得捏造確認，不能把沉默、文章認可或一次性安排當成新規範批准。

## 完善、驗證、commit、同步

```sh
python scripts/finish.py --message "Improve the X workflow" --files x/skills/w0x7ce-post-to-x/SKILL.md x/skills-state.json
```

明確列出本次新增、修改或刪除的檔案，不能以目錄代替。finish 執行結構檢查與離線測試、限定路徑 commit，再同步本機 `.local/installations.json` 中的授權目標。保留其他暫存內容，不自動 push；同檔案內混有他人修改時仍需先分離。

同步使用已提交 Git 快照，核對 rules、共用規範及完整資源指紋。草案可保存，但不生效；過期子 Skill 移到發現目錄外保留。相同內容不重複增加備份。

commit 失敗不繼續同步；同步失敗保留成功 commit，可修正後重試：

```sh
python scripts/sync.py
python scripts/sync.py --apply
```

第一條預覽、第二條執行。同時操作有鎖保護；鎖不能替代多個對話的檔案編輯協調。解除安裝時先移除本機登記，再移除自有入口及全域指令自有區塊，保留其他設定。

## 原有腳本與限制

TypeScript 發布工具需要 Bun，本機 CDP 還需要 Chrome／Chromium。Browserless Python 工具需要 Playwright，TypeScript 工具需要 playwright-core；設定見 [Browserless 說明](xiaohongshu/skills/w0x7ce-xhs-browserless/README.md)。

各 Skill 的 `scripts/` 和原有 references 仍保留。先讀入口 `--help`，歷史指南位於 `references/legacy-guide.md`，其中舊限額與介面描述不當成目前保證。

騰訊文件現有 CLI 只有 title、content、submit、profile；未傳 submit 仍可能建立自動保存的雲端文件。預覽、填入、保存與公開發布是不同結果，操作前核對實際授權。

## 驗證與資產

```sh
python scripts/check.py
python -m unittest discover -s tests -v
python scripts/sop.py status
```

CI 在 Linux、Windows 執行離線檢查；測試不登入或發布，不聲稱帳號端可用性。平台實測需在具體任務另行完成。

規範、Skill、必要腳本及素材進 Git。文章、Cookie、.env、瀏覽器狀態及個人安裝登記另行保存；不再用 `*.json` 或所有圖片副檔名一概忽略。MIT 授權及原 [baoyu-skills](https://github.com/jimliu/baoyu-skills) 致謝保留。
