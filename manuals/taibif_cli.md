# 🌿 taibif_cli 使用手冊 (CLI Governance Spec v2.1)

> **腳本路徑**：`scripts/gis/taibif_cli.py`  
> **CGS 版號**：`v2.1` (Spec-Driven Trinity Standard)  
> **規格來源**：`@dulan-ai-hub/topics/taibif/taibif-dulan-cli-spec.md`  
> **分類類別**：`gis` / `open_data`  
> **相依環境**：Python 標準函式庫 (`urllib`, `json`, `argparse`, `hashlib`)  
> **相容設定檔**：`data/ecology/places.json`, `data/ecology/indigenous_flora.json`, `data/ecology/dulan_birds.json`

---

## 🎯 1. 核心定位與國家級資料庫介紹

`taibif_cli.py` 是串接台灣國家級生物多樣性資料大腦 **TaiBIF（臺灣生物多樣性資訊機構）** 與 **TBIA（臺灣生物多樣性資訊聯盟）** 官方 OpenAPI (`tbiadata.tw`) 的 AI-Native 工具。

與 iNaturalist（公民隨手拍）及 eBird（鳥類清單與聽音辨識）互補，`taibif_cli` 提供**最權威、跨百年學術標本與林業法定調查資料**：
1. **100% 空間設定共用**：完全讀取 `places.json` 之 `dulan` 定義，自動映射縣市與鄉鎮（臺東縣東河鄉）。
2. **法定保育類與特有種鑑定**：一鍵檢索在地所有受法律保護之瀕臨絕種與珍貴稀有物種名冊。
3. **百年植物標本與採集歷史**：破案公民科學缺少記錄之傳統生活植物（如刺桐、芙蓉菊、檳榔）。
4. **TaiCOL 唯一物種分類身分證**：查詢 Taxon ID、正式學名與同物異名。
5. **CGS v2.1 標準相容**：支援 `-j` (JSON), `-q` (極簡), `--manual` 與標準管道輸出。

---

## 🚀 2. 常用命令範例

### ① 檢索都蘭指定物種的官方調查紀錄
```bash
python3 scripts/gis/taibif_cli.py search --name "烏頭翁" -n 10
python3 scripts/gis/taibif_cli.py search --group "被子植物" -n 5
```

### ② 產出都蘭在地【法定保育類動植物名冊】
```bash
python3 scripts/gis/taibif_cli.py protected
python3 scripts/gis/taibif_cli.py protected --group "哺乳類"
```

### ③ 比對阿美族生活植物在官方標本庫的採集點位 (二階段在地與全縣比對)
```bash
python3 events/classes/dulan-ai-hub-private/dulan-ai-hub/scripts/taibif_cli.py flora --match-flora
```
* **二階段自動升級**：優先搜尋都蘭在地（東河鄉），查無資料時自動擴展至台東全縣標本庫。
* **破案公民缺口**：自動標註 `⭐[iNat缺口破案]`，補齊 iNaturalist 因公民拍攝習慣遺漏的刺桐、檳榔、芙蓉菊等 6 大關鍵物種，命中率達 100%！

### ④ 查詢物種在 TaiCOL 的身分證與分類地位
```bash
python3 scripts/gis/taibif_cli.py taxon "烏頭翁"
```

### ⑤ 匯出調查點位為 GeoJSON 圖資
```bash
python3 scripts/gis/taibif_cli.py export --group "鳥類" --format geojson -o data/dulan_birds_tbia.geojson
```
