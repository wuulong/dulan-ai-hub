# 🌿 inat_cli 使用手冊 (CLI Governance Spec v2.0)

> **腳本路徑**：`scripts/gis/inat_cli.py`  
> **CGS 版號**：`v2.0`  
> **分類類別**：`gis` / `open_data`  
> **相依環境**：Python 標準函式庫 (`urllib`, `json`, `argparse`, `hashlib`)

---

## 🎯 1. 核心功能與設計哲學

`inat_cli.py` 是針對 iNaturalist 公民科學觀測資料打造的 AI-Native、管線友善 (Pipeline-Friendly) 的專業命令列工具。
核心特色：
1. **完全由設定檔驅動 (Config-Driven)**：無任何寫死的地區 Flag（如無 `--dulan`），預設載入都蘭空間範圍 (`places.json`) 與 18 種阿美族傳統原住民植物名錄 (`indigenous_flora.json`)，亦支援任意自訂檔案。
2. **二階段下鑽與 Token 節省 (Two-Stage Drilldown)**：`search` 預設提供單行極簡摘要；`fetch` 深入查詢單筆完整照片、經緯度與鑑定歷程。
3. **原住民生活植物名錄對照整合比對 (`match-flora`)**：以拉丁學名為主要鍵，一鍵比對在地觀察者是否記錄過飲食、香草、工藝、節氣與祭儀等民族植物，並指出「生態系系空缺物種」。
4. **多維度生態系分析 (`analyze`)**：支援海岸至中高山林的海拔垂直梯度分析，以及 1~12 月物候季節性熱力分佈。
5. **空間圖資匯出 (`export`)**：支援將觀測成果直接匯出為標準 GeoJSON 或 CSV。

---

## 🚀 2. 常用命令範例 (Quick Start)

### ① 查詢觀察者畫像 (User Profile)
```bash
python scripts/gis/inat_cli.py user jimchen1
```

### ② 檢索觀測紀錄 (二階段下鑽之第一階段)
```bash
# 查詢 jimchen1 在預設地區 (都蘭) 的最新 10 筆紀錄
python scripts/gis/inat_cli.py search --user jimchen1 -n 10

# 單行緊湊 JSON 輸出 (Token-Saving 模式)
python scripts/gis/inat_cli.py search --user jimchen1 -n 5 -j
```

### ③ 單筆紀錄下鑽 (二階段下鑽之第二階段)
```bash
python scripts/gis/inat_cli.py fetch 396794765
```

### ④ 原住民生活植物名錄對照整合比對
```bash
# 使用預設都蘭名錄比對 jimchen1
python scripts/gis/inat_cli.py match-flora --user jimchen1

# 搭配自訂名錄與自訂區域
python scripts/gis/inat_cli.py match-flora --user jimchen1 --place any --flora-file my_flora.json
```

### ⑤ 生態系多維度分析 (海拔梯度與物候季節性)
```bash
python scripts/gis/inat_cli.py analyze --user jimchen1 --mode both
```

### ⑥ 空間圖資匯出 (GeoJSON / CSV)
```bash
# 匯出都蘭觀測點 GeoJSON
python scripts/gis/inat_cli.py export --user jimchen1 --format geojson -o data/dulan_jimchen.geojson
```

---

## ⚙️ 3. 參數對照表

| 旗標 / 參數 | 型態 | 說明 |
| :--- | :--- | :--- |
| `-j, --json` | Flag | 啟用單行緊湊 JSON 輸出 |
| `-q, --quiet` | Flag | 極簡純文字輸出 |
| `-v, --verbose` | Flag | 輸出詳細除錯 Log 至 `stderr` |
| `-n, --limit` | Integer | 限制回傳筆數 (預設: 20) |
| `-o, --output` | String | 輸出檔案路徑 (支援 `-` 代表 stdout) |
| `--place` | String | 區域代號 (預設為 `dulan`，傳入 `any` 為不限區域) |
| `--place-config` | Path | 自訂區域設定檔 (預設 `data/ecology/places.json`) |
| `--flora-file` | Path | 自訂植物名錄設定檔 (預設 `data/ecology/indigenous_flora.json`) |
| `--bbox` | String | 四角座標涵蓋: `nelat,nelng,swlat,swlng` |
| `--no-cache` | Flag | 停用本機快取目錄 (`.cache/inat/`) |
| `--schema` | Command | 輸出自我描述 JSON Schema |
| `--manual` | Flag | 檢視本說明手冊 |
