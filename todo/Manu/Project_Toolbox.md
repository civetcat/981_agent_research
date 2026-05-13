# Project Toolbox: 萬用 Agent 工具箱

## 📝 專案描述
建立一個跨平台（Win10/Linux）的標準化工具庫，讓 AI Agent (Hermes/Cursor) 能透過統一介面呼叫常用腳本。

## 🏗 架構規範
- **環境隔離**: 每個工具獨立資料夾，含 `meta.yaml` 描述檔。
- **跨平台**: 使用 `pathlib` 處理路徑，支援 Win10 與公司 Linux VM。
- **管理機制**: 具備自動註冊 (Registry) 與環境偵測功能。

## 📊 當前狀態
- [架構中] 規劃 `manager.py` 核心調度邏輯。
- [進行中] 導入路徑抽象化與環境檢查腳本。
