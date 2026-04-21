# Cursor Skills & Subagent 研究室

和朋友一起整理 Cursor **Skills**（`SKILL.md`）與 **Subagent / Task** 的用法、範本與實驗筆記。

**GitHub：** [civetcat/cursor_skill_subagent](https://github.com/civetcat/cursor_skill_subagent)

## 本機 Skills 常見位置

- 使用者層級：`~/.cursor/skills/`（底下每個 skill 一個資料夾，內含 `SKILL.md`）
- 專案層級：`.cursor/skills/`（可版本化、與此 repo 一起協作）

## 協作方式建議

1. 把此 repo clone 到本機後，在專案內建立 `.cursor/skills/<你的主題>/SKILL.md`，用 PR 或分支合併。
2. 或只把「可分享的範本」放在 `examples/`，個人機密設定不要 commit。

## Subagent（Task）

在 Cursor 裡透過 **Task / Agent** 委派子任務時，描述要寫清楚：目標、限制、要回傳的格式。此 repo 可放你們約定的「委派範本」文字檔（例如 `examples/task-prompts/`）。

## Clone（協作者）

```bash
git clone https://github.com/civetcat/cursor_skill_subagent.git
cd cursor_skill_subagent
```

## 第一次 push（本機已有 `origin` 時）

在專案目錄執行（需已登入 GitHub：PAT、`gh auth login`、或已設好的 SSH）：

```bash
git push -u origin main
```

若本機還沒加過遠端：

```bash
git remote add origin https://github.com/civetcat/cursor_skill_subagent.git
git branch -M main
git push -u origin main
```
