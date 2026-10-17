# 小紅書 Browserless 既有流程

保留遠端 CDP 的 Cookie／掃碼登入及圖文發布。平台 rules 仍待確認；本次只完成來源整理與離線檢查。

將本目錄 .env.example 複製為 .env，填入自己的 XHS_WS_URL；環境變數優先。沒有配置時拒絕連線，不內建私人伺服器或憑證。

Python 入口需要 playwright；TypeScript 入口需要 Bun 及 playwright-core。遠端 Chrome 由 Browserless 提供。預設會話為本目錄 xhs_browser_state.json，兩種語言共用此位置；可用 XHS_STATE_FILE 指定相同私人路徑。Cookie 可用 XHS_COOKIE_FILE 指定。

在本目錄執行原有命令：

```sh
python xhs_login.py --file
python scripts/xhs_publish.py --title "標題" --content "正文" --image /path/to/image.png
bun scripts/publish.ts --title "標題" --content "正文" --image /path/to/image.png
```

Python 發布入口一次一張圖，TypeScript 接受重複 --image 或 --images 目錄。實際發布須獲准後才加 --submit；預覽仍會與平台互動，可能影響草稿。

Cookie、.env、會話與截圖留在本機，不提交。示例全部為佔位值。登入、圖片上傳、會話有效性及公開發布需在具體帳號另行驗證，不能將語法檢查當成平台測試。
