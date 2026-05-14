# Create a Markdown file explaining the ROADMAP_TRACKER.md usage and providing a template.

content = """# AI Agent 協作指南：ROADMAP_TRACKER.md 使用規範

## 1. 核心理念：Agent as a PM
將 AI Agent 從單純的「程式碼產生器」提升為「專案管理夥伴」。透過在專案路徑 `toolbox_workspace/docs/ROADMAP_TRACKER.md` 建立此文件，我們為 Agent 提供了一個**外部記憶體**與**任務清單**，確保在長對話或複雜開發中，資訊不遺失、進度可追蹤。

## 2. 使用情境與工作流
當面臨多個功能模組（例如 5 個 Toolboxes）需要實現時，請遵循以下步驟：

1.  **策略規劃 (Planning)**：請 Agent 規劃要實現哪些功能，並說明其「為什麼」要這樣設計。
2.  **任務拆解 (Breakdown)**：針對每個工具，請 Agent 進行顆粒度細小的任務拆解。
3.  **執行與記錄 (Execution & Logging)**：
    - 每完成一個子任務，要求 Agent 更新 `ROADMAP_TRACKER.md`。
    - 讓 Agent 在每次開啟新對話時先讀取此文件，確保進度同步。

---

## 3. ROADMAP_TRACKER.md 模板 (可以直接複製使用)

```markdown
# Project Roadmap & Task Tracker

## 📌 專案概覽
- **目標**：[請簡述專案或 Toolbox 開發目標]
- **當前階段**：規劃中 / 開發中 / 測試中 / 已完成
- **最後更新**：YYYY-MM-DD

---

## 🛠 功能規劃與設計思維 (Strategy)
> 由 Agent 填寫：預計開發哪些模組？為什麼選擇這些技術路徑？

1. **[模組名稱]**：
   - **目的**：解決 [問題]
   - **設計理由**：[原因]

---

## 📝 任務進度追蹤 (Task Lists)

### 🧰 Toolbox 1: [名稱]
- [ ] 任務拆解 1 (規劃中)
- [ ] 任務拆解 2 (待執行)
- [x] 已完成任務範例 (完成日期)

### 🧰 Toolbox 2: [名稱]
- [ ] 任務拆解 1
- [ ] 任務拆解 2

---

## 📅 排程規劃 (Scheduling)
- [ ] 第一階段：基礎設施與環境建置
- [ ] 第二階段：核心邏輯開發
- [ ] 第三階段：整合測試與優化

---

## 📒 開發筆記 (Notes)
> 紀錄開發過程中遇到的重大問題、解決方案或待決策事項。
- [YYYY-MM-DD] 修正了 ...
