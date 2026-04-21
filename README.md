# Cursor Skills & Subagent 研究室

和朋友一起整理 Cursor **Skills**（`SKILL.md`）與 **Subagent / Task** 的用法、範本與實驗筆記。

## 本機 Skills 常見位置

- 使用者層級：`~/.cursor/skills/`（底下每個 skill 一個資料夾，內含 `SKILL.md`）
- 專案層級：`.cursor/skills/`（可版本化、與此 repo 一起協作）

## 協作方式建議

1. 把此 repo clone 到本機後，在專案內建立 `.cursor/skills/<你的主題>/SKILL.md`，用 PR 或分支合併。
2. 或只把「可分享的範本」放在 `examples/`，個人機密設定不要 commit。

## Subagent（Task）

在 Cursor 裡透過 **Task / Agent** 委派子任務時，描述要寫清楚：目標、限制、要回傳的格式。此 repo 可放你們約定的「委派範本」文字檔（例如 `examples/task-prompts/`）。

## 推上 GitHub（本機已 `git init` 後）

若尚未安裝 GitHub CLI，可到 [github.com/new](https://github.com/new) 建立空 repo，然後：

```bash
cd /home/dan/cursor-skills-lab
git remote add origin https://github.com/<你的帳號>/<repo名稱>.git
git branch -M main
git push -u origin main
```

若已安裝 `gh` 並登入：

```bash
cd /home/dan/cursor-skills-lab
gh repo create cursor-skills-lab --private --source=. --remote=origin --push
```

（`--public` 可改成公開；repo 名稱請自訂。）
