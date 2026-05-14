# Project Tip-Toi-Reveng: 點讀筆應用研究與工具開發

## 📝 專案描述
深入研究開源專案 [tip-toi-reveng](https://github.com/entropia/tip-toi-reveng) 與 [snowbirdopter](https://github.com/maehw/snowbirdopter)，探索點讀筆與 OID 編碼的互動原理，並透過自建 Toolbox 實現客製化教材的自動化生產鏈。

## 🔍 技術背景
- **OID 編碼**: 研究 OID2/OID3 技術，點讀筆 CMOS 透過紅外光讀取微點陣。
- **跨專案整合**: 結合 `main_repo` 的檔案格式分析與 `snowbird_repo` 的 SoC (ZC3202N) 硬體底層邏輯。
- **硬體版本**: 已取得 **第四代 (Model 00110)**，具備內建鋰電池與 USB 傳輸功能。
- **精密品質檢測**: 使用 Sony A73 搭配微距鏡頭進行 1200dpi 碳粉點陣鑑定，確保 K100 純黑碳粉吸光特性達標。

## ⚙️ 當前進度
- [x] **環境構建與逆向基礎**：
    - [x] 整合兩大核心 Repo (`main_repo`, `snowbird_wiki`)。
    - [x] 完成 Wiki 繁體中文化轉換 (HTML 離線版)，克服德文技術文檔障礙。
- [x] **5/14 全鏈路首通 (里程碑)**：
    - [x] 完成第四代筆備份 (`system/`, `update/`) 與 `tttool` 通訊測試。
    - [x] 成功實現 `.mp3` -> `.ogg` -> `.gme` 注入並由硬體正常發聲。
- [x] **5/14 Toolbox 規劃與工作空間建立**：
    - [x] 建立 `toolbox_workspace` 架構，區分 `Human-Read` 與 `Agent-Read` 計畫書。
    - [x] 定義核心工具：OID 生成器、自動化打包器 (mp3+json)、音軌管理器。
- [ ] **5/15-5/18 規模化與自動化實作**：
    - [ ] **實作 Toolbox #1**: OID 條碼批次生成工具 (Python)。
    - [ ] **實作 Toolbox #2**: 撰寫自動化腳本，將 JSON 描述檔一鍵轉為專案專用 YAML 並編譯。
    - [ ] **物理升級**: 採購 1200dpi 雷射印表機 (HP M404n/Brother L2460DW) 並完成首批 1000-1100 網格測試。

## 📊 狀態紀錄
- **2026-05-12**: 設備運送中，軟體環境配置完成。
- **2026-05-13**: 規劃將 OID 生成邏輯整合至 Project Toolbox。
- **2026-05-14**: **重大突破**。完成全鏈路測試，自訂音檔成功發聲。
- **2026-05-14**: **架構升級**。啟動 Toolbox Workspace 計畫，導入 AI Agent 協作模式開發專屬工具集。

## 🛠 關鍵工具與工作流
- **Knowledge Base**: 中文化 Wiki (Tip-Toi-Reveng & Snowbirdopter)
- **Software**: `tttool`, Cursor (Claude 3.5 Sonnet), Python (pydub, reportlab, jinja2)
- **Hardware**: TipToi Pen (00110), Sony A73 (Macro Check), **Target: 1200dpi Laser Printer**
- **Toolbox Path**: `tiptoi_study/toolbox_workspace/`

## 🚀 未來願景 (Toolbox Plan)
1. **Barcode Generator**: 輸入 ID 範圍自動生成 A4 排版 PDF。
2. **Auto-Packer**: 監控目錄，自動將 MP3 與 JSON 指令打包成 .gme。
3. **Firmware Explorer**: 基於 Snowbird 研究，探索 00110 硬體更多的隱藏功能。
