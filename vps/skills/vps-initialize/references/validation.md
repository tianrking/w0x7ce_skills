# 腳本與 Skill 驗證

從來源 Skill 目錄執行：

```bash
bash -n scripts/bootstrap-vps.sh
bash -n scripts/preinstall-network-tools.sh
bash scripts/test-network-preinstall.sh
```

Windows 可使用 Git Bash。生命週期測試使用隔離的 apt/systemctl/版本命令替身，不安裝服務或連線；測試新裝 dormant、既有狀態與 mask 保留、pending 接續、失敗標記及自訂服務不被接管。

使用 skill-creator 的 `quick_validate.py` 檢查格式；完成後在 SOP 根目錄記錄完整資源指紋，執行既有 `finish.py`，只列本次明確檔案。

## 證據界線

核心代理/開發工具鏈的前身曾在 Ubuntu 24.04 amd64 完成實機、重跑及外部代理驗收。

三項預裝模組目前只有本機語法與隔離生命週期測試，尚未在真實新機驗證套件 post-install。Skill 包裝不擴大實機驗證範圍；首次部署仍須核對官方 APT 支援及安裝後服務狀態。

arm64 未實機驗證。服務 restart 不等於整台 VPS 重啟測試。不要為補齊此文件而操作未授權伺服器。
