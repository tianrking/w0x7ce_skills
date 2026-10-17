# Agent 接手指南

保留完整 Git checkout。先讀根目錄 [AGENTS.md](../AGENTS.md)、[rules.md](../rules.md) 與 [shared-rules.md](../shared-rules.md)，再選本次任務入口；不需要載入所有平台。

在倉庫根目錄執行 `git status --short` 及 `python scripts/sop.py status`，保留既有修改。下表是導覽，確認狀態以實際檢查為準。

| 任務 | 直接入口 | 狀態 |
|---|---|---|
| 微信公眾號文章、封面、HTML 與來源包 | [Skill](../wechat-official-account/skills/w0x7ce-wechat-official-account/SKILL.md) | 已確認、有本地交付驗證 |
| VPS 初始化 | [Skill](../vps/skills/vps-initialize/SKILL.md) | 已確認、主機操作按當次授權 |
| X 貼文與長文 | [Skill](../x/skills/w0x7ce-post-to-x/SKILL.md) | rules 待確認 |
| LinkedIn 貼文 | [Skill](../linkedin/skills/w0x7ce-post-to-linkedin/SKILL.md) | rules 待確認 |
| 小紅書圖文 | [本地 Skill](../xiaohongshu/skills/w0x7ce-post-to-rednote/SKILL.md)、[Browserless Skill](../xiaohongshu/skills/w0x7ce-xhs-browserless/SKILL.md) | rules 待確認 |
| 騰訊文字文件 | [Skill](../tencent-docs/skills/w0x7ce-post-to-tencent-docs/SKILL.md) | rules 待確認 |
| 整理規範、完善 Skill、提交與同步 | [維護 Skill](../skills/personal-sop-maintainer/SKILL.md) | 根維護入口 |

按 Skill 指引閱讀所屬領域 rules，執行 `python scripts/sop.py check-skill DOMAIN NAME` 後使用。待確認平台先展示 rules，不自行批准或繞過檢查。原有 guides 是歷史材料，不代表目前介面與功能已實測。

## 直接使用或安裝

直接使用：從完整 checkout 閱讀來源 Skill 並通過檢查即可，不必改全域設定。單獨複製 SKILL.md 會缺少規範與相對資源。

全域使用：按 [README](../README.md) 執行 install 預覽、install --apply、sync --apply。install 安裝根入口及登記目標，sync 才安裝有效子入口；子入口仍指向來源，請長期保留 checkout。乾淨 clone 未登記目標時，sync 不會自行安裝。

Codex／Claude Code 的發現依各自宿主設定；其他 Agent 可以由使用者明確指示閱讀本入口，不能保證只給 Git 就自動載入。既有會話可能需要重新讀取或重開。

## 依賴、維護與驗收

管理與微信打包需 Python 3.10+、Git，只用標準庫。Windows 若 python 是 Store 佔位程式，改用有效的 py -3 或 Python 執行檔。舊發布流程依 Skill 需要 Bun、Chrome 或 Playwright／Browserless，不在接手時自動登入。

管理命令從倉庫根目錄執行；Skill 資源相對於來源 Skill 目錄。文章、圖片、憑證及瀏覽器狀態保存在獨立作品／工作區，不放進 SOP。

修改人的要求先 rules 草案與確認；已確認要求下改善實作，驗證後 record-skill，再 finish 限定檔案 commit 及同步。具體命令見 README 與維護 Skill，不重複維護另一套流程。不自動 push。

本地驗證：`python scripts/check.py`、`python -m unittest discover -s tests -v`；另有需 Bun 的 `python scripts/check_typescript.py`。CI 涵蓋 Ubuntu／Windows。離線通過不等於平台保存、發布或真實主機部署已成功。

交給新 Agent 時可以附上：

> 先讀這個倉庫的 AGENTS.md 和 docs/agent-handoff.md，查看 Git 與 SOP 狀態，只使用本次任務相關且有效的 Skill。保留已有修改。我的任務是：……
