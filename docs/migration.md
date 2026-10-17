# 2.0 遷移記錄

原 GitHub 倉庫起點為 687db0e。SOP 工具及規範匯入自先前本機專案 77105ad；這兩個識別屬於不同提交鏈，不混稱本倉庫同一段歷史。

遷移期間，本機來源新增並提交了 6602b92 的 VPS 初始化規範及 Skill。本專案一併保留它的既有確認記錄、腳本及版本指紋，不將已確認領域降級為新草案。

## 原有目錄對照

| 舊目錄 | 新目錄 |
|---|---|
| skills/w0x7ce-post-to-x | x/skills/w0x7ce-post-to-x |
| skills/w0x7ce-post-to-linkedin | linkedin/skills/w0x7ce-post-to-linkedin |
| skills/w0x7ce-post-to-rednote | xiaohongshu/skills/w0x7ce-post-to-rednote |
| skills/w0x7ce-xhs-browserless | xiaohongshu/skills/w0x7ce-xhs-browserless |
| skills/w0x7ce-post-to-tencent-docs | tencent-docs/skills/w0x7ce-post-to-tencent-docs |

五個名稱保持不變，腳本與原有 references 保留；原 SKILL 背景收錄為 references/legacy-guide.md，標示為歷史材料。test-image.png 搬至 tests/fixtures/。MIT、上游致謝及既有 Git 歷史保留。

## 規範狀態

X、LinkedIn、小紅書及騰訊文件的規範由舊工作流抽象成草案，微信規範沿用先前收集的草案；均未宣稱取得完整版本確認。結構整理、commit 或本次推送授權不代表規範批准。

原有 Skill 檢查 rules 與完整資源版本。人確認後再驗證、記錄及同步。Marketplace 保留 publishing-skills 名稱並補齊 Browserless；插件安裝不跳過確認。

## 修正

- 提供共用規範、平台 rules、根維護 Skill、Agent 入口與完整管理工具；不限制只能用 TypeScript。
- 精確忽略本機會話與憑證，讓 state.json、插件 metadata 及必要素材可正常追蹤。
- 騰訊文件文件只描述程式已支援的參數，交代預覽仍可能建立雲端文件，submit 不等於分享權限。
- Browserless 移除私人端點及憑據式預設，Cookie 示例改成佔位值；不在連線日誌輸出端點憑證，Python 與 TypeScript 共用預設會話位置。
- 安裝器支援明確來源遷移，轉移自有入口與登記，保留舊檔案。

## 驗證範圍

以隔離 Git 倉庫驗證確認、提交及同步流程，檢查 Skill、插件路徑、Python 語法及 TypeScript 轉譯。CI 在 Linux 和 Windows 執行離線檢查。

沒有重新登入平台或實際發布；舊介面、限額及帳號能力未因目錄遷移獲得驗證。歷史憑據式示例不會因清理現行檔案而消失；本次不重寫歷史，若曾是有效憑證應另行輪換。

## 微信公眾號領域命名

2026-10-17：使用者要求名稱明確為微信公眾號，並按已展示 rules 建立對應 Skill。活動目錄由 `wechat/` 改為 `wechat-official-account/`；R1 審閱快照保留原路徑作為歷史，不代表新活動路徑。其他四平台仍待確認。
