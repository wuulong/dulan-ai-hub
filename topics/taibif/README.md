# 🌿 TaiBIF & TBIA 台灣生物多樣性國家級生態系系調查與保育分析

本單元專注於中研院 TaiBIF（臺灣生物多樣性資訊機構）與 TBIA（臺灣生物多樣性資訊聯盟）官方 OpenAPI 的整合應用，為都蘭社區 AI Hub 提供國家級權威調查資料、學術標本、特有種鑑定與法定保育類生物多樣性分析支援。

---

## 📂 檔案目錄導覽

| 類型 | 檔案名稱 | 說明 |
| :--- | :--- | :--- |
| **CLI 規格書** | [taibif-dulan-cli-spec.md](taibif-dulan-cli-spec.md) | **TaiBIF / TBIA 台灣生物多樣性在地生態系與保育調查 CLI 規格書 (CGS v2.1)**：與 inat_cli 空間設定 100% 相容，支援物種出沒紀錄檢索、都蘭法定保育類名冊、原民植物標本比對與物種身分證查詢。 |
| **實機驗證報告** | [taibif-dulan-verification.md](taibif-dulan-verification.md) | **都蘭在地國家級生態系大數據實機驗證報告**：調閱東河鄉 1,316 筆烏頭翁歷史穿越線、法定保育類食蟹獴/瓜頭鯨實體監測，以及 TaiCOL 物種身分證技術驗證。 |
| **文化植物厚化** | [dulan-ethnobotany-tbia-enrichment.md](dulan-ethnobotany-tbia-enrichment.md) | **阿美族生活植物名錄 ╳ TBIA 國家級標本厚化報告**：達成 18/18 種 100% 官方破案，補齊刺桐、檳榔、芙蓉菊等 iNaturalist 公民觀察盲點。 |

---

## 🛠️ 配套工具與設定檔 (規劃中)

* **TaiBIF CLI 核心工具**：`events/classes/dulan-ai-hub-private/dulan-ai-hub/scripts/taibif_cli.py` (即將實作)
* **使用說明手冊**：`events/classes/dulan-ai-hub-private/dulan-ai-hub/manuals/taibif_cli.md` (即將實作)
* **共用空間設定檔**：`events/classes/dulan-ai-hub-private/dulan-ai-hub/data/ecology/places.json` (與 iNat、eBird 三者共用)
* **原民植物名錄**：`events/classes/dulan-ai-hub-private/dulan-ai-hub/data/ecology/indigenous_flora.json` (18 種指標植物)
