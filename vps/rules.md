新 VPS 初始化操作規範（給 agent）
版本：2026-10-17

任務邊界
這份規範供每次初始化新伺服器使用。只有使用者明確要求部署到某台伺服器時，才連線並修改該伺服器。
若使用者只要求編輯規範或腳本，只修改交付檔案，不連線、不更動目前或歷史伺服器。
歷史驗收中的 IP、網域、帳號、路由與認證不得套用到新伺服器。
本套件不含 SSH 密碼、代理密碼、Tailscale auth key、Cloudflare token 或既有客戶端設定。

每次部署的輸入
1. SSH 主機、連接埠與登入帳號；確認 root 或可用 sudo。
2. 新 VPS 的實際網域或公網 IP；核對 DNS 與介面位址，區分 NAT 外部位址和本機已配置位址。
3. 系統版本與 CPU 架構；腳本目前支援 Ubuntu/Debian + systemd、amd64/arm64。
4. Hysteria2 預設 UDP 443；mieru 預設 TCP 8443。先確認埠未占用。
5. 是否有既有 WireGuard/Tailscale/其他 VPN、出口節點、策略路由或防火牆規則。
帳號認證透過當次安全管道提供，不要寫入可重用腳本、規範或公開驗收報告。

預設安裝範圍與完成狀態
Hysteria2：安裝、產生隨機獨立認證、配置服務、啟動、設為開機自啟動、驗證。
mieru/mita：安裝官方服務端及原生客戶端、產生獨立認證、啟動、設為開機自啟動、驗證。
nvm + Node.js：為指定開發帳號安裝；現有腳本為 root；選擇 LTS 並固定 default alias。
Go：官方 stable 發布包、校驗 SHA-256、設定 PATH、實際建置小程式。
Rust：rustup stable，minimal profile 加 rustfmt/Clippy；實際使用 Cargo 離線建置無外部依賴的小專案。
基礎編譯依賴：build-essential、pkg-config、libssl-dev 等。
時間同步：chrony，保留原有來源，確認同步正常。
小記憶體保護：RAM 小於 2 GiB 且無啟用 swap 時，在磁碟足夠時建立 2 GiB swap。
Tailscale：預裝官方套件；新安裝時保持停止且不自啟動，不登入、不加入 tailnet、不選出口節點。
Cloudflare Tunnel：預裝 cloudflared；不登入、不建立或執行 Tunnel、不執行 service install。
Cloudflare WARP：預裝 cloudflare-warp；新安裝時 warp-svc 保持停止且不自啟動，不註冊、不連線。
上述三項網路工具若已存在，保留原本服務啟動與自啟動狀態，不強制停止已運行的服務。
不得以「讓驗收通過」為由偷偷啟用 Tunnel、WARP 或 Tailscale。

部署前檢查與快照
記錄 uname、/etc/os-release、架構、CPU、磁碟、MemAvailable、swap、負載。
記錄監聽埠、既有代理服務的 ActiveState/NRestarts/啟動時間。
記錄 IPv4/IPv6 的 address、route、rule，以及 nftables/iptables/UFW 狀態。
只收集必要欄位；WireGuard private key、服務密碼、環境變數中的 token 不得出現在輸出或公開報告。
不要將低 CPU 使用率視為有足夠容量；查看服務 cgroup 記憶體、可用記憶體和 OOM 記錄。
不安裝桌面、瀏覽器、容器集群、大型資料庫或監控全家桶，除非使用者另有要求。

安裝與重跑原則
使用 bootstrap-vps.sh 及同目錄的 preinstall-network-tools.sh。
先核對當時官方文件、套件支援的發行版/架構、簽章金鑰與固定版本。
核心代理使用固定版本和官方 digest；Go 使用官方 SHA-256；APT 使用 signed-by 專用金鑰。
來源不支援目標架構/發行版時停止並報告，不改用第三方一鍵腳本或偽裝成其他發行版。
不要全系統升級、升級發行版、重啟整台 VPS，除非使用者要求或同意。
發現不由本腳本管理的既有代理配置時先檢查/遷移，不覆蓋。
重跑應保留代理認證、憑證私鑰、既有 tailnet 與 Cloudflare 身分。
網路工具的新安裝以 systemd 持久 mask 阻止套件 post-install 啟動；成功停用後解除本次 mask。
若網路工具安裝中斷，保留 pending 標記及本次 mask；重跑只接續本模組擁有的 pending 項目。
不解除使用者原先設定的 mask，不接管未知自訂服務。
下載大型檔案失敗或過慢時，可以本機下載並校驗後透過 SSH 傳入快取；不能略過校驗。
Rustup 使用單一 I/O 執行緒、210 MiB 解包記憶體上限與單一下載併發。
半安裝的 Rust 工具鏈須同時檢查 rustc 與 rustup component manifest，不能只看版本字串。

網路處理
不要把舊伺服器的 WireGuard 出口、主路由或 nftables 規則複製到新機。
Hysteria2 允許用 --hy-bind 明確綁定已配置到介面的公網 IP。
只有確認現有策略路由導致 UDP 回程問題時，才使用 --hy-direct-replies。
該選項僅對綁定位址與 Hysteria2 UDP 來源埠建立主表規則；優先序 4991 衝突時停止。
對本機 Fake-IP DNS 問題，可用 --client-address 指定真實入口，同時保留 TLS SNI 與指紋。
UFW 已啟用時加入必要埠規則；雲安全組需另外驗證，不能把主機監聽當成公網已通。
保留既有 SSH 管理路徑；未來啟用 WARP/出口節點應另作具備回復路徑的網路變更。

驗收標準
核心服務：active、enabled；mita status 為 RUNNING。
開發環境：全新互動登入能找到 nvm/Node/Go/Rust/Cargo；Node 執行、Go 建置、Cargo 建置執行成功。
時間：chronyc tracking 顯示正常同步；swap 持久化且磁碟空間足夠。
網路預裝：tailscale version、cloudflared --version、warp-cli --version 成功；APT 套件狀態為 installed。
新裝網路工具應 inactive/not-found 且 disabled/not-found；已存在工具應保持檢查前狀態。
網路工具驗收不要求登入、warp=on、Tunnel 健康或 tailnet 已連線；這些在本次預裝範圍之外。
完整代理：從外部客戶端經 VPS 存取 HTTPS 網站；Hysteria2 的錯誤憑證指紋必須被拒絕。
若沒有外部客戶端測試條件，明確列為未驗證，不以服務 active 代替。
同參數重跑，比對認證/私鑰/服務設定雜湊，確認不變。
服務重啟與回程規則重建測試應在可控時段執行，並確認既有服務不受影響。
本機語法/模擬測試、實機安裝、外部連線、完整重啟是不同證據，不可混稱全部驗證。

交付與收尾
提供腳本、通用說明、版本清單、服務/埠清單、驗收記錄與尚未驗證項目。
私人客戶端設定與分享連結分開交付，不放入供未來 agent 使用的通用套件。
可重用套件只包含：本規範、兩個腳本、通用使用說明與套件自身的本機驗證記錄。
移除本次專用的臨時 SSH 金鑰和臨時憑證檔，保留使用者原有金鑰。
不要把本次伺服器資訊自動寫入跨會話記憶；另有使用者明確要求時才處理記憶更新。

供使用者每次貼給 agent 的任務範本
請依附件 AGENT-VPS-BASELINE.txt 初始化我這次指定的新 VPS。
SSH：<主機>，連接埠：<埠>，帳號：<帳號>；認證另行提供。
服務入口：<本次的網域/公網IP>。
請安裝並啟動 Hysteria2、mieru，安裝 nvm/Node LTS、Go、Rust 開發環境；
預裝 Tailscale、cloudflared、Cloudflare WARP，這三項新安裝後先不要運行、登入或連線。
先檢查既有服務及策略路由，保留現有設定；完成驗收並交付私人連線設定與結果。

官方參考
https://v2.hysteria.network/docs/getting-started/Installation/
https://github.com/enfein/mieru/blob/main/docs/server-install.md
https://github.com/nvm-sh/nvm
https://go.dev/doc/install
https://rust-lang.github.io/rustup/environment-variables.html
https://pkgs.tailscale.com/stable/
https://pkg.cloudflare.com/
https://pkg.cloudflareclient.com/
