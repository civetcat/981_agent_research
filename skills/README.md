# Skills Directory

此目錄包含 **Cursor** 與 **Hermes Agent** 可共用的技能（Skills），以 `SKILL.md` 格式組織。

## 目錄說明

- `skills/`：本專案收集的技能範本，可直接複製使用
- 每個子目錄代表一個獨立技能，內含 `SKILL.md` 主檔案（可能包含 `scripts/`、`references/` 等子目錄）

## 使用方式

### 1. Cursor Skills

Cursor 會自動讀取以下位置的技能：

```bash
# 使用者全域技能（推薦）
~/.cursor/skills/

# 專案專用技能（推薦與專案一起版本控制）
.cursor/skills/
```

**安裝單一技能：**

```bash
# 複製特定技能到 Cursor 技能目錄
cp -r skills/build-code-on-docker ~/.cursor/skills/
# 或複製到專案內
cp -r skills/build-code-on-docker .cursor/skills/
```

### 2. Hermes Agent Skills

Hermes Agent 的技能存放於：

```bash
~/.hermes/skills/
```

**安裝方式：**

```bash
cp -r skills/hermes-memory-management ~/.hermes/skills/
```

或使用 Hermes 內建指令：
```bash
hermes skill import <skill-name>
```

## 目前可用技能一覽

| 技能名稱                        | 類型           | 主要功能 |
|-------------------------------|----------------|----------|
| `build-code-on-docker`        | Build          | 在 Docker 容器中安全編譯、測試與除錯（Go、C/C++） |
| `code-review-go-cpp-p0p3`     | Review         | Go/C++ 程式碼審查（P0-P3 嚴重度分級，繁體中文輸出） |
| `karpathy-coding-principles`  | Coding         | 實作 Karpathy 務實編碼原則（最小改動、可驗證完成） |
| `multi-model-judge`           | Judge          | 多模型並行生成 + Judge 模型交叉評比，減少幻覺 |
| `produce-code`                | Orchestrator   | 多 Agent 子代理工作流（Coder/Reviewer/Judge 隔離執行） |
| `refactor-optimize-pragmatic` | Refactor       | 務實重構：不過度設計、保留正確行為、小步驗證 |
| `hermes-memory-management`    | Productivity   | Hermes Agent 記憶體壓縮、知識提煉至 memory、清理舊 session |
| `plan-md-template-zh`         | Template       | Cursor `plan.md` 繁體中文標準模板（含 YAML frontmatter） |
| `validation-notes-generic-zh` | Documentation  | 產生標準化 QA 驗證筆記（五欄格式） |
| `skill-minimal`               | Template       | 建立新技能的最小範例模板 |

## 技能格式規範（SKILL.md）

每個技能應包含：

```yaml
---
name: skill-name
description: 簡短描述（50 字以內）
category: coding/review/build/productivity
last_updated: 2026-05-01
owner: Your Name
---

# Skill Title

## 目標
...

## 執行流程
1. ...
```

## 最佳實踐

- **單一職責**：一個 skill 只解決一類問題
- **清晰觸發條件**：在 `description` 中寫清楚什麼情況會觸發此 skill
- **包含 Verification**：提供驗證步驟
- **記錄 Pitfalls**：寫下常見錯誤與注意事項
- **保持更新**：使用 `last_updated` 標記版本

## 相關資源

- [Cursor Skills 文檔](https://cursor.com/docs/skills)
- [Hermes Agent Skills 機制](../README.md#hermes-agent-客製化設定)
- `rules/character.mdc`：全域角色與行為規範
- `rules/cursor-rules-consolidated.mdc`：合併版 Cursor Rules

---

**維護者**：本專案致力於收集高品質、可複製的開發技能，歡迎 PR 貢獻新技能或改進現有內容。
