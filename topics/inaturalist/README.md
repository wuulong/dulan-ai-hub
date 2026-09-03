# 🌿 iNaturalist 都蘭生態系系與阿美族傳統生活植物分析

本單元收錄針對台東都蘭公民科學（iNaturalist）觀測資料的完整系統架構、規格書、精準比對演演算法、以及在地代表性觀察家（`jimchen1` 陳豊鍾 先生）之實機分析測試成果。

---

## 📂 檔案目錄導覽

| 類型 | 檔案名稱 | 說明 |
| :--- | :--- | :--- |
| **規格書** | [inaturalist-dulan-flora-cli-spec.md](inaturalist-dulan-flora-cli-spec.md) | CGS v2.0 CLI 治理規格書，涵蓋設定檔驅動架構、子命令定義與空間資料流。 |
| **實測報告** | [inaturalist-jimchen1-dulan-verification.md](inaturalist-jimchen1-dulan-verification.md) | 實機測試報告：`jimchen1` 都蘭 3,065 筆觀察紀錄、原民植物 61.1% 命中率、海拔梯度與物候季節性分析。 |
| **演演算法檔案** | [inaturalist-spatial-and-taxon-matching-algorithm.md](inaturalist-spatial-and-taxon-matching-algorithm.md) | 都蘭 Bounding Box / 球面半徑空間演算、拉丁學名三階對齊 (Taxon ID / 同物異名 / 研究級共識) 演演算法。 |

---

## 🛠️ 配套工具與設定檔 (公開共享資產)

* **CLI 程式碼**：`events/classes/dulan-ai-hub-private/dulan-ai-hub/scripts/inat_cli.py`
* **使用說明書**：`events/classes/dulan-ai-hub-private/dulan-ai-hub/manuals/inat_cli.md`
* **都蘭空間設定**：`events/classes/dulan-ai-hub-private/dulan-ai-hub/data/ecology/places.json`
* **原民植物名錄**：`events/classes/dulan-ai-hub-private/dulan-ai-hub/data/ecology/indigenous_flora.json` (18 種都蘭指標生活植物)
