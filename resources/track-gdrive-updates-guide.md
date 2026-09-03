# 📄 Google Drive 更新追蹤工具使用說明書 (`track_gdrive_updates.py`)

本工具用於自動分析指定的 Google Drive 資料夾，篩選出在指定日期或時間之後曾被修改或新增的學員筆記與檔案，並輸出其檔名、修改時間與連結，非常適合用於「都蘭 AI 慢活共創營」中講師掌握學員最新填寫狀況。

---

## 🛠️ 命令列參數說明

本腳本可傳入以下參數：

| 參數選項 | 縮寫 | 預設值 | 說明 |
| :--- | :--- | :--- | :--- |
| `--folder-id` | `-f` | `1IrM_8cMWQZb-oeFCSHJ4qMZ5pVihv2fs` | 要追蹤的 Google Drive 資料夾 ID (預設為本課程學員筆記目錄) |
| `--since` | `-s` | *(必填)* | 篩選時間起點。可填寫「天數」(例如 `3` 代表近 3 天)、「日期」(如 `2026-07-08`) 或完整 ISO-8601 時間字串 |
| `--credentials` | `-c` | `credentials.json` | Google OAuth2 憑證金鑰檔路徑 |
| `--token` | `-t` | `token.json` | OAuth 授權後的快取權杖檔路徑 |

---

## 🔑 認證機制設定

本工具支援三種認證方式：

1. **Token 快取 (優先使用)**：若目錄下存在 `token.json`，將直接載入並驗證，免去重複認證的流程。
2. **OAuth 2.0 Client Secrets 憑證**：若沒有 Token，但專案目錄下有 `credentials.json`，腳本會自動打開本機瀏覽器讓您進行 Google 帳號授權，成功後會自動生成並快取 `token.json`。
3. **Application Default Credentials (ADC) 備用方案**：若兩者皆無，會嘗試載入環境變數中的 ADC（例如已在終端機執行過 `gcloud auth application-default login` ）。

---

## 💡 使用範例

請在 `dulan-ai-hub` 根目錄或其 submodule 目錄下執行：

### 範例 1：查詢預設學員筆記目錄中，近 2 天內的所有更新
```bash
./scripts/track_gdrive_updates.py -s 2
```

### 範例 2：查詢預設目錄中，自 2026-07-08 之後的所有更新
```bash
./scripts/track_gdrive_updates.py -s 2026-07-08
```

### 範例 3：指定特定資料夾 ID，查詢特定時間點後的更新
```bash
./scripts/track_gdrive_updates.py -f "YOUR_FOLDER_ID" -s "2026-07-08T12:00:00Z"
```

---

## 🐍 Python API 導入調用

您也可以在其他 Python 腳本中直接 Import 調用此核心函式：

```python
from scripts.track_gdrive_updates import track_gdrive_updates

result = track_gdrive_updates(
    folder_id="1IrM_8cMWQZb-oeFCSHJ4qMZ5pVihv2fs",
    since="2026-07-08"
)

for file in result["files"]:
    print(f"檔案：{file['name']}，修改時間：{file['modifiedTime']}")
```
