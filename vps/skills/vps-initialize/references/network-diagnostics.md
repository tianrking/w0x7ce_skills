# 按證據選擇網路適配

這些是診斷方法，不是每台新 VPS 必須套用的設定。

## 入口與 DNS

分別核對 SSH 主機解析、公網位址及本機介面位址。本機代理的 Fake-IP 解析可能使客戶端連不到真實主機；可用當次已驗證 IP 作為 `--client-address`，保留 TLS SNI 與憑證指紋。

只有 AAAA 的入口需要客戶端 IPv6 路徑。入口是 IPv6 不代表出口也是 IPv6；NAT 外部公網 IP 不能作為未配置本機介面的監聽位址。

## 多出口與 QUIC 回程

監聽正常但握手失敗時，對照入站/出站介面、來源位址及策略路由。抓包限制介面、埠和時長，不收集無關流量。

有 wildcard UDP 回包選錯來源的證據時，可用 `--hy-bind` 綁定已配置到介面的 IP。策略路由仍導向隧道且需要限定回包走主表時，可選 `--hy-direct-replies`；它只匹配綁定位址與 Hysteria2 UDP 來源埠，優先序 4991 衝突則停止。

使用 `ip route get` / `ip -6 route get`、封包及外部握手驗證效果。不刪除原有 WireGuard/Tailscale、防洩漏規則或整套防火牆，不把直接回程誤做成代理出站全部改走直接出口。

GSO/ECN、MTU、混淆只在有相應證據時調整；一次改可判斷的一組條件，無效測試設定應回復。

## 僅預裝工具

CLI 可用，但新服務保持 dormant。不為診斷而順便 login、registration、connect、tailscale up 或切換 DNS/出口。

預裝模組以自己的 pending 標記及 systemd mask 管理中斷恢復。辨識標記歸屬，不解除使用者 mask，不停用原有已運行的 VPN。
