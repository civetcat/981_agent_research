---
name: hermes-memory-management
category: productivity
description: 定期壓縮 Hermes Agent 記憶體、提煉知識、清理舊 session，防止長期使用後 context 與 state.db 膨脹。僅使用 memory，不建立新 skill。
last_updated: 2026-04-27
owner: Derek Ko
---

# Hermes Memory Management & Cleanup

此 skill 負責將分散在 session 中的知識**僅提煉成 memory**，並安全清理舊紀錄，防止長期使用後 context window 與 state.db 持續成長。**避免建立新 skill** 以防止產生大量內容重複、大同小異的技能。

## 執行流程

1. **現況評估**
   - 計算 session 數量 (`ls ~/.hermes/sessions/ | wc -l`)
   - 檢查 state.db 大小 (`du -h ~/.hermes/state.db`)

2. **知識遷移 (最高優先)**
   - 使用 `session_search` 找出近期重要主題 (git, karpathy, bmc, yocto, kernel, debug 等)
   - 將關鍵事實以 **declarative facts** 格式存入 `memory` 工具 (target=user 或 memory)
   - **Why**：Memory 是精簡、持久、可索引的結構，不會像 session 一樣無限累積 token 成本。僅使用 memory，避免建立重複或內容大同小異的 skill。

3. **安全清理**
   - 只刪除超過 10 天的舊 session：
     ```bash
     find ~/.hermes/sessions -name "session_*.json" -mtime +10 -delete
     ```
   - 優化 SQLite 資料庫：
     ```bash
     sqlite3 ~/.hermes/state.db "VACUUM; PRAGMA optimize;"
     ```

4. **驗證與記錄**
   - 比較清理前後的 session 數量與 db 大小
   - 使用 `memory` 工具記錄本次清理重點與新發現

## Verification
```bash
ls ~/.hermes/sessions/ | wc -l
du -h ~/.hermes/state.db
```

## Pitfalls
- 絕對不要刪除最近 2 天的 session（避免破壞當前對話 context）
- Memory 內容必須是 declarative facts ("User prefers concise responses" 而非 "Always respond concisely")
- **嚴格僅使用 memory 工具**，不要使用 skill_manage 建立新 skill，以避免技能內容大量重複
- 每次執行後若發現更好方法，立即使用 `skill_manage(action='patch')` 更新本 skill

## Related Tools
- `session_search`
- `memory`
- `cronjob` (建議每週執行一次此 skill)

**此 skill 是維持 Hermes Agent 長期記憶體效率的核心機制，特別適合長期開發環境使用。所有提煉結果只存入 memory。**
