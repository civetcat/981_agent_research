# 專案文檔：Matrix-ATS (MATS) 矩陣化執行器設計方案

## 1. 核心願景 (Vision)
在 2026 年高算力時代，將傳統基於「線性邏輯」與「文字日誌」的測試架構（如 pyATS），升級為基於**「線性代數」與「空間投影」**的矩陣化分析架構。

**目標：** 達成零 LLM 依賴、低延遲、高精確度的封閉式故障零件定位。

---

## 2. 現狀分析與新舊對比
| 維度 | 傳統執行器 (pyATS) | Matrix-ATS (MATS) |
| :--- | :--- | :--- |
| **數據模型** | 非結構化文字 (Strings) | 高維張量/矩陣 (Tensors/Matrices) |
| **執行邏輯** | 序列式執行 (Step-by-step) | 空間軌跡監控 (State-space Tracking) |
| **診斷方式** | 人工閱讀 Log / Regex 匹配 | 殘差分析與特徵空間投影 (SVD) |
| **效率** | 低 (隨測試規模線性增長) | 極高 (利用矩陣運算並行處理) |

---

## 3. 技術架構 (Technical Architecture)

### A. 數據向量化 (Vectorization)
將測試過程中的指標（CPU, Latency, Error Codes, Port Status）映射到矩陣 $X_{N \times M}$：
- **$N$**：測試時間點或 Test Case 序號。
- **$M$**：監控的零件或指標維度。

### B. 診斷引擎 (Algebraic Engine)
利用 **奇異值分解 (Singular Value Decomposition, SVD)**：
1. **建立基準**：從正常執行的 Log 中提取「主成分空間」。
2. **計算異常**：將新測試數據投影至該空間，計算其與基準的「歐幾里得距離」。
3. **定位零件**：透過**殘差貢獻度分析 (Contribution Plot)**，找出數值偏移最大的維度，直接鎖定故障零件。

---

## 4. Cursor 實作路線圖 (Implementation Roadmap)

### 第一階段：特徵提取 (Feature Extraction)
- **任務**：開發 `LogFeatureExtractor`。
- **要求**：分析 Log 格式，將關鍵狀態轉化為數值（如：Interface Up=1, Down=0）。

### 第二階段：代數核心 (Core Math)
- **任務**：開發 `AlgebraicEngine`。
- **要求**：使用 `numpy.linalg` 實現 SVD 降維與殘差監控。

### 第三階段：故障定位 (Root Cause Analysis)
- **任務**：開發 `get_root_cause()`。
- **要求**：根據矩陣座標與 `feature_map` 自動指出故障零件名稱與確信度。

### 第四階段：插件整合 (Wrapper Integration)
- **任務**：開發 `MatrixATSExecutor`。
- **要求**：無縫銜接 pyATS `job.json` 並產出可視化診斷報告。

---

## 5. 預期效益 (Expected Benefits)
1. **秒級診斷**：處理百萬行 Log 僅需幾毫秒。
2. **封閉安全**：完全本地運算，不需將敏感 Log 上傳至雲端 AI。
3. **精確度**：排除人為閱讀 Log 的主觀誤判，利用數學機率給出確信度。
4. **易用性**：自動產出零件健康熱點圖，讓維護者直觀定位硬體問題。

---

## 6. 附錄：關鍵 Prompt 備忘錄
- **數據轉化**：分析 Log 格式，寫出數值化 Parser，將狀態映射至固定 Index。
- **數學建模**：利用純線性代數實現異常檢測，嚴禁調用外部 LLM API。
- **故障定位**：實作殘差貢獻度分析，將矩陣 Index 映射回物理零件名稱。

---
**紀錄日期：** 2026-05-13
**版本：** v1.0.0
