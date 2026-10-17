---
name: w0x7ce-xhs-browserless
description: "小紅書遠端 Browserless 圖文的既有發布流程；使用前先檢查平台規範確認狀態。"
---

# 小紅書遠端 Browserless 圖文

這是原有 Skill 的結構遷移，腳本保留在本目錄；不是新增並已驗證的平台發布能力。

## 先確認規範版本

以此檔案目錄為 `SKILL_DIR`。在本專案來源中，根目錄是 `SKILL_DIR/../../..`，平台規範是 `SKILL_DIR/../../rules.md`。

先讀根目錄 `rules.md`、`shared-rules.md` 及平台 `rules.md`。執行根目錄的 `python scripts/sop.py check-skill xiaohongshu w0x7ce-xhs-browserless`。

目前遷移的 rules 為待確認草案；檢查失敗時展示規範及原因，停止此 Skill 的平台操作。不要自行記錄使用者已確認。人確認後，驗證原有流程、記錄規範與完整資源指紋，再以 finish 提交及同步。

## 執行原有流程

確認及版本檢查通過後，先核對本次內容、帳號、圖片和動作授權。預覽與發布分開；沒有明確的發布或文件建立授權，不進行外部寫入。

腳本以 `SKILL_DIR/scripts/` 為基準，主要入口是 `publish.ts`。先閱讀腳本 `--help` 及必要參考；不要把歷史指南描述但程式未實作的參數當成可用功能。

使用者要求預覽時，說清楚它是否仍會在平台建立草稿或雲端文件。執行結果須區分本機填入、平台保存及公開發布；未做帳號端驗證時如實說明。

## 延伸與參考

原有指南保留於 `references/legacy-guide.md`，只作背景。原有額外 references 與腳本仍保留。平台額度、帳號能力及 UI 可能變動，使用時另行核對。

延用原有 EXTEND.md 查找方式：先看工作專案的 `.w0x7ce-skills/w0x7ce-xhs-browserless/EXTEND.md`，再看使用者主目錄同路徑。擴充可補充任務細節，不自行覆寫人的規範確認或擴大發布授權。
