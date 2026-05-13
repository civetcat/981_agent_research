# Project Tip-Toi-Reveng: 點讀筆應用研究

## 📝 專案描述
深入研究開源專案 [tip-toi-reveng](https://github.com/entropia/tip-toi-reveng)，探索點讀筆與數位紙張（OID 編碼）的互動原理。

## 🔍 技術背景
- **OID 編碼**: 研究 Sonix 技術，點讀筆 CMOS 透過紅外光讀取微點陣。
- **列印需求**: 需 600dpi+ 雷射列印、K100 純黑碳粉（吸紅外光）。
- **驗證方式**: 使用 Sony A73 微距鏡頭觀察點陣碼完整度。

## ⚙️ 當前任務
- [ ] 5/16-5/18 接收硬體並開箱。
- [ ] 使用 `tttool` 編譯 YAML 產出 `.gme` 檔。
- [ ] 測試新購點讀專用紙的感應靈敏度。

## 📊 狀態紀錄
- **2026-05-12**: 設備運送中，軟體環境（Haskell/tttool）配置完成。
- **2026-05-13**: 規劃將 OID 生成邏輯整合至 Project Toolbox。

## 🛠 關鍵工具
- **Software**: `tttool`, Python, `pathlib`
- **Hardware**: TipToi Pen, Sony A73, Laser Printer
