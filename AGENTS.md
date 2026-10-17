# 個人 SOP 專案閱讀入口

先讀根目錄 `rules.md`，再讀 `shared-rules.md`，最後只讀本次相關領域的 `rules.md` 及 `state.json`。

要總結、抽象或完善 SOP 時，讀 `skills/personal-sop-maintainer/SKILL.md`。新增或實質修訂領域規範先形成草案，交給人明確確認，再建立或更新對應子 Skill。不得自行宣稱使用者已確認。

既有規範確認指紋不符時，不使用它產生子 Skill。已有確認版的變更寫入 `rules.draft.md`，保留目前生效的 `rules.md`。

安裝副本、壓縮包是匯出成果；本專案是單一維護來源。不要將本目錄內的規則自動套用到無關任務。文件及腳本不得存入密碼、Token、私鑰或私人服務端點。

有意義的 SOP 修改完成且必要檢查通過後，自動做本機 Git 提交，只提交本次變更並回報 commit ID。草案提交不代表人已確認；不得順便 push 或提交無關暫存內容。具體提交流程遵循根目錄維護 Skill。

使用 `scripts/finish.py` 完成驗證、限定檔案 commit 和同步已登記目標。同步從已提交快照產生，子 Skill 必須通過已確認規範與完整資源指紋檢查。同步失敗時如實回報，不把 commit 成功當成全域更新成功。
