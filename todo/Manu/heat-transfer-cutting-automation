# 熱轉印與 3D 印表機改裝自動化裁切專案進度表
# Heat Transfer & 3D Printer Cutting Automation Project Tracker

## 🛠 設備與耗材清單 / Hardware & Materials List
- **圖像處理軟體 / Vector Design**: Inkscape (向量排版、文字轉路徑)
- **輸出印表機 / Inkjet Printer**: Canon G3780 (大供墨系統)
- **加熱設備 / Heat Source**: 家用熨斗 (目前測試用，關閉蒸汽)
- **轉印介質 / Transfer Media**: 
  - [x] 彩之舞 (HY-J10) 深色噴墨轉印紙 (A4 / 0.18mm)
  - [ ] Siser EasyColor DTV (預計進階升級選項)
- **自動化裁切備案 / Cutting Automation (Bambu P1S MOD)**:
  - [ ] 3D 列印夾具：Maker World 帶彈簧緩衝之 P1S 專用刀架 (Spring-Loaded Mount)
  - [ ] 切割刀具：工業標準羅蘭刻字刀座 + 45度/60度鎢鋼刀片 (Roland Blade)

---

## 📈 第一階段：熨斗 MVP 實驗進度 / Phase 1: Iron MVP Experimental Progress

### 1. 前置準備與去濕 / Pre-treatment & Dehumidification
- [ ] **布料預處理**: 實施「先洗後印」流程，排除 110cm 小孩素 T 的工業漿料與縮水率變因。
- [ ] **纖維去濕**: 熱壓前用熨斗預熱壓 10 秒，蒸發布料內層微量水氣（避免氣泡）。
- [ ] **物理平面選擇**: 放棄軟質燙衣板，改在實木桌或大理石等硬質表面施壓，確保力量 100% 傳導。

### 2. 裁切工藝與視覺隱形 / Cutting Craft & Visual Camouflage
- [ ] **黑框保護邊 (2mm Offset)**: 在 Inkscape 中為圖片外圍建立 2mm 黑框，消除黑衣白邊突兀感。
- [ ] **手動裁切實驗**: 直線使用「鋼尺 + 美工刀」，大輪廓使用「剪刀」。
- [ ] **應力優化（圓角化）**: 依官方說明書指引，將圖案尖角修成「小圓弧」，防止洗滌時從邊角起翹。

### 3. 熱壓參數實驗 (4x1.5cm 小圖案) / Heat Press Parameters (Small Logo)
- [ ] **設定溫度**: 熨斗調整至「棉質 (Cotton)」等級，底板實測溫度約 160°C - 180°C。
- [ ] **定點重壓**: 摒棄滑動燙法，利用「身體全身重量」對準小圖案垂直定點重壓 **8 秒**。
- [ ] **冷卻與二次加壓**: 靜置 2-3 分鐘完全冷卻後才撕除蠟紙；隨後蓋上隔熱紙進行 5 秒二次加壓。

---

## 🔬 第二階段：P1S 割字機改裝硬核實驗 / Phase 2: P1S Drag Knife Hardcore MOD

### 1. 軟體工具鏈建立 / Software Toolchain Configuration
- [ ] **向量路徑編譯**: Inkscape 文字物件執行 `Ctrl+Shift+C` 轉為純路徑（路徑不跑位）。
- [ ] **G-code 轉譯測試**: 
  - 測試方案 A：使用 Inkscape 內建外掛 `Gcodetools` (設定下刀深度 Z= -0.1mm，抬刀 Z= 2mm)。
  - 測試方案 B：使用網頁端開源 CAM 軟體 `LaserWeb` / `Jscut` 導出標準 G-code。
- [ ] **拓竹指令相容性優化**: 於 G-code 前置代碼加入 `M104 S0` (關閉噴頭) 與 `M140 S0` (關閉熱床)，移除自動調平與擦拭噴頭指令。

### 2. 硬體改裝與安全防錯 / Hardware Modding & Safety Precautions
- [ ] **緩衝件列印**: 於 P1S 上實裝帶有彈簧機構的刀架，利用物理彈簧吸收 Z 軸微量誤差。
- [ ] **鋼板防護**: 在 P1S 不鏽鋼板上加貼一層厚紙板或軟膠墊，避免因下刀過深刮傷 PEI 磁吸鋼板。
- [ ] **首航測試 (Dry Run)**: 不裝刀片，純粹讓 P1S 工具頭在空中跑一遍 Inkscape 的文字路徑，確認 X/Y 軸運動邏輯與速度限制 (建議小於 2000 mm/min)。

---

## 📔 實作筆記與痛點分析 / Implementation Notes & Pain Point Analysis

- **2026-05-18**: 收集完割字機與雷雕機資料，拍板定案先以「家用熨斗」進行最小可行性測試。
- **2026-05-18**: 釐清 Inkscape 匯出 PDF 設定（300/600 DPI 差異）與 Canon 驅動程式設定（應選擇高解析度紙張/霧面相片紙，避免 T-Shirt 轉印模式之自動鏡像陷阱）。
- **[待填寫] 熨斗實作回饋**: 
- **[待填寫] 首洗測試紀錄 (靜置 72 小時後)**: 

---

## 💡 第三階段：未來商業硬體評估候選 / Phase 3: Future Commercial Hardware Evaluation
- [ ] **大面積手持熱壓機**: 卡影 25x30cm (蝦皮 110V)，解決 A4 範圍一次壓合不留接縫之需求。
- [ ] **專業抽拉式熱壓機**: 翼兆 38x38cm 抽拉平板款，安全性最高，槓桿重壓變因完全受控。
- [ ] **獨立居家電腦割字機**: 評估 `Silhouette Cameo` 系列（因其具備專屬外掛，可與 Inkscape 向量檔一鍵無縫串接，最符合工程師工作流）。
