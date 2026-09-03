# 🦅 ebird_cli 使用手冊 (CLI Governance Spec v2.0)

> **腳本路徑**：`scripts/gis/ebird_cli.py`  
> **CGS 版號**：`v2.0`  
> **分類類別**：`gis` / `open_data`  
> **相依環境**：Python 標準函式庫 (`urllib`, `json`, `argparse`, `hashlib`, `csv`)  
> **相容設定檔**：`data/ecology/places.json`, `data/ecology/dulan_birds.json`

---

## 🎯 1. 核心功能與定位

`ebird_cli.py` 是串接全球最大賞鳥平台 **eBird API v2.0** 的 AI-Native 命令列工具。
與 `inat_cli.py` 形成專案生態系系觀測的「動植物雙核心」：
1. **100% 共用空間設定**：直接使用 `places.json` 中的 `dulan` 坐標與半徑，零重複維護。
2. **安全憑證讀取**：支援 `EBIRD_API_KEY` 環境變數、`~/.ebird_api_key` 或 `--api-key` 旗標。
3. **即時鳥況與熱點查詢**：查詢半徑內近期 1~30 天目擊紀錄（支援 `--user` 觀察者過濾）、官方認證賞鳥熱點。
4. **歷史特定日期區間查詢 (`historic`)**：突破 30 天限制，查詢過去特定歷史區間（如 4/13~4/26）的公共觀測。
5. **指標鳥類名錄比對 (`match`)**：一鍵比對都蘭 12 種指標鳥種目擊率與最新時間地點。
6. **個人歷史觀察篩選 (`user-csv`)**：匯入官方下載的 `MyEBirdData.csv`，支援「空間 + 日期區間 + 指標鳥名錄 (`--match-birds`)」三位一體篩選。
7. **旅行足跡時間軸 (`trip`)**：一鍵還原特定旅程日期區間的按日賞鳥足跡、地點與坐標。
8. **GIS 圖資匯出 (`export`)**：支援一鍵匯出 GeoJSON / CSV。

---

## 🚀 2. 常用指令範例

### ① 設定 API Key (一次性)
```bash
echo "your_ebird_api_token" > ~/.ebird_api_key
```

### ② 查詢都蘭近期鳥況 (支援限定觀察者)
```bash
python3 scripts/gis/ebird_cli.py recent -n 10
python3 scripts/gis/ebird_cli.py recent --user "jason wu"
```

### ③ 查詢歷史特定日期區間鳥況
```bash
python3 scripts/gis/ebird_cli.py historic --date 2026-04-20 --end-date 2026-04-26
```

### ④ 匯入個人 CSV 分析特定旅程 (含指標鳥對照)
```bash
python3 scripts/gis/ebird_cli.py user-csv MyEBirdData.csv \
  --place dulan \
  --start-date 2026-04-13 \
  --end-date 2026-04-26 \
  --match-birds
```

### ⑤ 產出個人旅行足跡時間軸 (Trip Summary)
```bash
python3 scripts/gis/ebird_cli.py trip MyEBirdData.csv \
  --start-date 2026-04-13 \
  --end-date 2026-04-27
```

### ⑥ 依清單編號下鑽查看觀察者與完整鳥種
```bash
python3 scripts/gis/ebird_cli.py checklist S325666633
```
