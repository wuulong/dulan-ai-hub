# 🏛️ 都蘭在地國家級生態系系大資料 (TaiBIF / TBIA) 實機驗證報告

> **驗證日期**：2026-09-04  
> **核心工具**：`scripts/gis/taibif_cli.py` (CGS v2.1 合規)  
> **資料來源**：中研院 TaiBIF / TBIA 官方 OpenAPI (`tbiadata.tw`)  
> **歸檔路徑**：`events/classes/dulan-ai-hub-private/dulan-ai-hub/topics/taibif/taibif-dulan-verification.md`

---

## 🎯 1. 實機執行成果與破案亮點

我們透過新開發之 CGS v2.1 工具 `taibif_cli.py`，直接調閱中研院與台灣生物多樣性資訊聯盟（TBIA）之國家級調查資料庫：

### ① 都蘭烏頭翁歷史調查穿越線檢索
```bash
python3 scripts/gis/taibif_cli.py search --name "烏頭翁" -n 3
```
* **成果**：光是東河鄉境內，官方調查就累積了 **1,316 筆**烏頭翁穿越線調查紀錄！
* **歷史深核**：調閱出 2000 年與 2001 年林保署「生物資源資料庫」在都蘭北側坐標 (`23.0300, 121.2800`) 的樣區實體監測紀錄。

### ② 都蘭在地法定保育類名冊一鍵產出
```bash
python3 scripts/gis/taibif_cli.py protected --group "哺乳類"
```
* **成果**：東河鄉境內官方記錄到 53 筆法定保育類哺乳動物調查資料！
  1. **食蟹獴 (*Urva urva formosana*)**：二級珍貴稀有保育類，記錄於東河鄉山林（臺灣獼猴族群估算計畫紅外線自動相機）。
  2. **瓜頭鯨 (*Peponocephala electra*)**：保育類海洋哺乳動物，記錄於東海岸海域（台灣鯨豚擱淺與出沒監測）。

### ③ TaiCOL 唯一物種分類身分證
```bash
python3 scripts/gis/taibif_cli.py taxon "烏頭翁"
```
* **成果**：精確調出 TaiCOL 官方唯一 Taxon ID `t0037457`、同物異名 (*Pycnonotus hainanus taivanus*) 與全台灣官方庫存 **127,778 筆**分佈紀錄。

---

## 🔬 2. 公民科學「生態系三核心」實踐拼圖完成

至此，都蘭社區 AI Hub 已具備三位一體的完整生態系走讀科技兵器庫：
1. **iNaturalist (`inat_cli.py`)**：走讀拍照、隨手打卡、植物微觀辨識。
2. **eBird (`ebird_cli.py`)**：晨間聽音、鳥類即時動態、個人賞鳥旅行時間軸。
3. **TaiBIF / TBIA (`taibif_cli.py`)**：國家級百年調查穿越線、法定保育類名錄、學術標本厚化。
