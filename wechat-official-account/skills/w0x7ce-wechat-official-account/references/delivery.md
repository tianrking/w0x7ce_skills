# 正文片段與打包

工作資料夾最少有 `article.md`、`body.html`、`images/cover.png`，正文圖片也放 images/。封面可用其他 PNG、JPEG、GIF 或 WebP 檔名。

`article.md` 第一行是 `# 完整題目`；正文片段不重複題目，使用 section、h2、p、ul、blockquote、figure、table 等語意結構，逐項加上適合文章的內嵌樣式。圖說用 figcaption，圖片 img src 指向 images/ 相對檔案。正文中不要放 script、外部 CSS 或網頁互動元件。

```sh
python SKILL_DIR/scripts/package_article.py --source /path/to/article-source --cover images/cover.png --output /path/to/new-delivery
```

輸出目錄必須不存在，避免覆寫已確認成果；修訂先生成新版本並比對，再替換交付檔。來源目錄、輸出目錄不得彼此包含。腳本只收文章、正文片段、images/ 及可選 sources.json／README.md；其他可編輯圖源請在 images/ 保存。

輸出包含：

- `article.html`：單檔 HTML，正文圖片內嵌，一鍵複製正文／題目，提供剪貼簿受限時的備援。
- `source/` 與 `source.zip`：Markdown、正文片段、原始圖片與封面、簡短說明及可選來源記錄；搬移後保留相對路徑。
- `cover.<副檔名>`：可獨立上傳的封面。
- `manifest.json`：交付檔案的 SHA-256，方便版本核對。

腳本會拒絕遺失圖片、遠端／絕對路徑／越界圖片、符號連結及正文腳本。圖片由本地可信來源取得後再打包；不靠遠端載入維持交付。它不驗證圖片授權、事實準確性、完整 Markdown 語法或微信實際保存效果。

首次驗收先檢查產出全文及圖說。開啟 article.html，複製正文到可檢查 HTML 與純文字的貼上區，確認沒有題目、工具列或狀態提示；再測題目按鈕只有題目。保留圖片原檔供平台補圖，不能保證 data URI 在平台保存後仍被接受。
