---
name: vps-initialize
description: "初始化新 VPS 或完善此初始化流程：檢查現有網路與資源、部署 Hysteria2/mieru 和 Node/Go/Rust 開發環境，預裝但不啟用 Cloudflare Tunnel、WARP 與 Tailscale。只編輯規範或 Skill 時不操作伺服器。"
---

# 新 VPS 初始化

## 規範與來源

先閱讀唯一生效規範 [vps/rules.md](../../rules.md)。它定義結果與驗收，本 Skill 定義執行方法；不在 Skill 內另養一份規範。

全域安裝副本是個人 SOP 的入口，依其指引先執行來源 `scripts/sop.py check-skill vps vps-initialize`，再讀取來源最新已提交的本 Skill。檢查失敗時說明具體原因，不以工作中的草案或過期副本繼續部署。

## 判斷任務範圍

- 部署新 VPS：使用者已指定要初始化的主機，才建立 SSH 連線並執行安裝。從當次輸入取得主機、帳號、埠及服務入口，不套用歷史伺服器資訊。
- 修改規範、腳本或 Skill：只修改維護來源與交付資料，先做隔離驗證；這不授權修改任何舊 VPS。
- 後續啟用網路工具：本基線只含預裝。使用者另外要求啟用時，核對當次帳號、網路效果及 SSH 回復路徑；不把一次啟用改成所有新機的預設。

## 部署流程

1. 取得必要 SSH 與入口資訊，做只讀檢查及快照。辨識 OS、架構、NAT、IPv6、既有服務、資源、DNS、路由、VPN 與防火牆；只詢問確實缺失且會影響下一步的資訊。
2. 按規範判斷適用性。內附腳本針對 Ubuntu/Debian + systemd；其他系統按官方文件適配，不能假裝相容。核對官方支援、APT 金鑰與固定版本，不把歷史版本當成永遠最新。
3. 檢查 [scripts/bootstrap-vps.sh](scripts/bootstrap-vps.sh) 與同目錄 [scripts/preinstall-network-tools.sh](scripts/preinstall-network-tools.sh)，一起上傳到本次主機的私有工作目錄。依檢查結果選參數，執行並保留日誌。
4. 驗證核心服務、開發工具鏈及時間同步。對預裝工具只驗證套件、版本與停止/自啟動狀態，不以登入或連線作驗收條件。
5. 用外部原生客戶端驗證代理與錯誤指紋拒絕行為；沒有外部條件就明確列為未驗證。重跑/重啟測試要避開既有負載，並比對設定與認證。
6. 交付版本、服務埠、證據、限制及私人客戶端設定。認證不收入 Skill 或通用套件。移除本次臨時登入金鑰，保留原有金鑰。

典型呼叫（值從當次輸入取得）：

```bash
bash bootstrap-vps.sh --host SERVER_HOST
```

兩個腳本須在同一目錄。預設包含三項網路工具的僅預裝；當次使用者明確省略時才使用 `--skip-network-preinstall`。

## 按需讀取

- IPv6、Fake-IP、多出口或 QUIC 回程問題：讀 [references/network-diagnostics.md](references/network-diagnostics.md)。
- 修改內附腳本或驗證 Skill：讀 [references/validation.md](references/validation.md)。

## 維護

沿用 `$personal-sop-maintainer` 與來源 SOP 管理流程，不另建第二個規範倉庫。

已確認規範內的實作修復：修改來源、必要驗證、`record-skill vps vps-initialize` 記錄完整資源指紋，再使用來源 `scripts/finish.py --message ... --files 明確檔案清單` 完成本機 commit 與已授權目標同步。不 push，不把其他會話的修改納入提交。

人的目標、啟用預設、交付或驗收要求有實質變更：先形成 `vps/rules.draft.md` 供確認，保留現行規範。草案可以提交保存，但未確認時不能用它發布生效子 Skill。

只修改全域副本不算維護完成。只同步已提交且規範/資源指紋有效的來源；同步成功不代表其他進行中的會話已立即重新載入。
