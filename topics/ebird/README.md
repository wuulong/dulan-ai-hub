# 🦅 eBird & Merlin 都蘭在地鳥類生態系系觀測與分析

本單元專注於台東都蘭及東海岸鳥類公民科學（eBird API v2.0 與 Merlin Bird ID）的觀測大資料分析、專屬 CGS v2.0 工具鏈規格、在地指標鳥種比對，以及真實賞鳥足跡深度驗證報告。

---

## 📂 檔案目錄導覽

| 類型 | 檔案名稱 | 說明 |
| :--- | :--- | :--- |
| **CLI 規格書** | [ebird-dulan-cli-spec.md](ebird-dulan-cli-spec.md) | **eBird 在地鳥類生態系系觀測與即時鳥況 CLI (CGS v2.0 實作升級版)**：與 inat_cli 空間設定 100% 相容，支援近期鳥況、歷史查詢、熱點探勘、個人 CSV 空間篩選與旅行時間軸。 |
| **真實觀測報告** | [wulung-hsu-dulan-bird-verification.md](wulung-hsu-dulan-bird-verification.md) | **都蘭在地觀察家 (WuLung Hsu) eBird 個人真實觀測驗證報告**：利用 user-csv 還原 4/23 都蘭清晨臺灣竹雞與白腹秧雞目擊，以及 Merlin 辨識與公共 API 過濾機制深度技術解密。 |

---

## 🛠️ 配套工具與設定檔 (公開共享資產)

* **eBird CLI 核心工具**：`events/classes/dulan-ai-hub-private/dulan-ai-hub/scripts/ebird_cli.py`
* **使用說明手冊**：`events/classes/dulan-ai-hub-private/dulan-ai-hub/manuals/ebird_cli.md`
* **共用空間設定檔**：`events/classes/dulan-ai-hub-private/dulan-ai-hub/data/ecology/places.json` (與 iNat 雙向共用)
* **都蘭指標鳥類名錄**：`events/classes/dulan-ai-hub-private/dulan-ai-hub/data/ecology/dulan_birds.json` (12 種都蘭指標鳥)
