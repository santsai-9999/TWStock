# 台股即時五檔

輸入股票代號，就能顯示該檔台股的即時買賣五檔，每 5 秒自動更新。上市、上櫃股票都可以查。

## 網址

- **線上版**：https://twstock-6zfs.onrender.com/
- **原始資料（除錯用）**：https://twstock-6zfs.onrender.com/api/raw/2330
- **整理後的報價**：https://twstock-6zfs.onrender.com/api/quote/2330

## 部署資訊

| 項目 | 內容 |
|---|---|
| 程式碼 | GitHub `santsai-9999/TWStock`（main 分支） |
| 主機 | Render，免費方案，新加坡機房 |
| Render 服務名稱 | `twstock`（Blueprint 名稱：`colewa01`） |
| 部署設定 | `render.yaml` |
| 資料來源 | 證交所「基本市況報導」`mis.twse.com.tw`，約 5 秒更新一次 |
| 完成部署 | 2026-11-20 |

## 檔案說明

| 檔案 | 用途 |
|---|---|
| `app.py` | 後端（Python Flask）：向證交所抓資料、整理五檔，並快取 3 秒 |
| `index.html` | 前端畫面：輸入股票代號、顯示五檔、每 5 秒自動更新 |
| `requirements.txt` | 需要的套件：flask、requests、gunicorn |
| `render.yaml` | Render 部署設定 |

## 如何修改程式

1. 在 GitHub 的 `santsai-9999/TWStock` 修改或上傳檔案，再按「Commit changes」。
2. Render 會自動重新部署，大約需要 2～3 分鐘。
3. 可以在 Render 的服務頁面左側點「Events」或「Logs」查看部署進度。

## 在自己電腦上執行

```bash
pip install -r requirements.txt
```
```bash
python app.py
```
執行後，用瀏覽器打開 http://127.0.0.1:5000

- 示範模式（使用模擬資料，用來測試畫面）：`python app.py --demo`
- Mac 上請改用 `pip3` 和 `python3`。

## 免費方案限制

- 閒置 15 分鐘後主機會休眠，下次打開要等 30～60 秒才會醒來。
- 網址是公開的，任何知道網址的人都看得到這個頁面。

## 問題排除紀錄

| 問題 | 原因 | 解法 |
|---|---|---|
| 沒有顯示真實價格 | 證交所需要先取得 cookie；盤中成交價欄位 `z` 可能是 `-` | 先連證交所首頁取得 cookie；`z` 沒有值時改用 `pz` |
| 2308 出現 `invalid literal for int()` | 五檔的量有 `-` | 解析時把 `-` 當成 0；價格為 0 的顯示「市價」 |
| Render 顯示「render.yaml not found」 | 檔案沒有放在專案的最外層 | 把 `render.yaml` 放到 repository 根目錄 |
| 在 Render 找不到網址 | 停留在 Blueprint 頁面 | 點進 `twstock` 服務頁面，網址就在名稱下方 |

## 注意事項

- 前端更新間隔請不要短於 5 秒，以免被證交所暫時封鎖 IP。
- 證交所資料只限個人使用。如果要對外公開提供，需要向證交所申請資訊授權。
- 如果需要更即時的資料（逐筆），可以考慮改接券商 API（例如永豐 Shioaji）或富果 Fugle API。
