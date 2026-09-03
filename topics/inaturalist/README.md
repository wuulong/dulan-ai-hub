# 🌿 iNaturalist 都蘭生態系系走讀與植物觀測分析

本單元專注於台東都蘭公民科學（iNaturalist）觀測資料的完整系統架構、規格書、精準比對演演算法、在地代表性觀察家（`jimchen1` 陳豊鍾 先生）之實機分析測試成果、導覽動線規劃與空間聚類架構、全區生態系系空缺物種與公民科學偏差深入分析，以及完整的 15 種植物現地解說手冊圖鑑。

---

## 📂 檔案目錄導覽

| 類型 | 檔案名稱 | 說明 |
| :--- | :--- | :--- |
| **圖鑑與導覽** | [dulan-ethnobotany-field-guide.md](dulan-ethnobotany-field-guide.md) | **18 種植物完整現地解說手冊圖鑑 (100% 大滿貫版)**：結合 TBIA 國家級資料庫，補齊刺桐、芙蓉菊與大葉田香草，包含精確 GPS、族語名稱與解說講稿。 |
| **導覽規劃** | [dulan-ethnobotany-tour-guide.md](dulan-ethnobotany-tour-guide.md) | **都蘭阿美族生活植物 4 站式全景導覽手冊**：串連聚落信仰、海岸節氣神話、農園香草與深林保育廊道，內含一鍵開啟之 Google Maps 步行/車行實體導航。 |
| **路徑演演算法** | [spatial-clustering-and-tour-routing-architecture.md](spatial-clustering-and-tour-routing-architecture.md) | 點位多準則評選 (MCDA)、DBSCAN 空間分群、旅行推銷員 (TSP) 最佳化與門戶啟發架構規格書。 |
| **空缺剖析** | [dulan-flora-gap-analysis.md](dulan-flora-gap-analysis.md) | 全區探勘分析：找回食茱萸與林投實體點位，深度解讀刺桐/檳榔/芙蓉菊「0 筆紀錄」之公民科學偏差與教學轉化。 |
| **分類演演算法** | [inaturalist-spatial-and-taxon-matching-algorithm.md](inaturalist-spatial-and-taxon-matching-algorithm.md) | 都蘭空間邊界定義（BBox / 球面半徑）與拉丁學名三階對齊 (Taxon ID / 同物異名 / 研究級共識) 演演算法。 |
| **實測報告** | [inaturalist-jimchen1-dulan-verification.md](inaturalist-jimchen1-dulan-verification.md) | 實機測試報告：`jimchen1` 都蘭 3,065 筆觀察紀錄、原民植物 61.1% 命中率、海拔梯度與物候季節性分析。 |
| **CLI 規格書** | [inaturalist-dulan-flora-cli-spec.md](inaturalist-dulan-flora-cli-spec.md) | CGS v2.0 CLI 治理規格書，涵蓋設定檔驅動架構、子命令定義與資料管線。 |

---

## 🛠️ 配套工具與設定檔 (公開共享資產)

* **iNat CLI 程式碼**：`events/classes/dulan-ai-hub-private/dulan-ai-hub/scripts/inat_cli.py`
* **使用說明書**：`events/classes/dulan-ai-hub-private/dulan-ai-hub/manuals/inat_cli.md`
* **都蘭空間設定檔**：`events/classes/dulan-ai-hub-private/dulan-ai-hub/data/ecology/places.json` (與 eBird 共用)
* **原民植物名錄**：`events/classes/dulan-ai-hub-private/dulan-ai-hub/data/ecology/indigenous_flora.json` (18 種指標植物)
