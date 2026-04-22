# 981 Agent Research（Cursor Skills / Subagent）

和朋友一起整理 Cursor **Skills**（`SKILL.md`）與 **Subagent / Task** 的用法、範本與實驗筆記。

**GitHub：** [civetcat/981_agent_research](https://github.com/civetcat/981_agent_research)

## 本機 Skills 常見位置

- 使用者層級：`~/.cursor/skills/`（底下每個 skill 一個資料夾，內含 `SKILL.md`）
- 專案層級：`.cursor/skills/`（可版本化、與此 repo 一起協作）

## 協作方式建議

1. 把此 repo clone 到本機後，在專案內建立 `.cursor/skills/<你的主題>/SKILL.md`，用 PR 或分支合併。
2. 或只把「可分享的範本」放在 `examples/`，個人機密設定不要 commit。

## Subagent（Task）

在 Cursor 裡透過 **Task / Agent** 委派子任務時，描述要寫清楚：目標、限制、要回傳的格式。此 repo 可放你們約定的「委派範本」文字檔（例如 `examples/task-prompts/`）。

### 目前已放的 Task 範本（`examples/task-prompts/`）

| 檔案 | 用途 |
|---|---|
| `explore-codebase.txt` | 快速掃描 repo 結構與相關檔案 |
| `review-diff.txt` | 唯讀審查變更／風險與驗證建議 |
| `shell-oneoff.txt` | 單次唯讀 shell 調查（grep、git log 等） |

使用方式：複製內容到 Task 對話，把占位符 `＿＿＿主題＿＿＿` 換成實際主題或檔案路徑。

## 可共用 Skills（`examples/skills/`）

以下為從個人 skills 整理、**已去掉或泛化公司／專案綁定**後的版本，可直接複製到 `~/.cursor/skills/<name>/` 或專案 `.cursor/skills/<name>/`。

| 目錄 | 說明 |
|---|---|
| `build-code-on-docker` | 在 Docker 內 build／test（Go、cmake、make）；映像檔請用 `BUILD_IMAGE` 改成你們的 image |
| `code-review-go-cpp-p0p3` | Go／C++ 變更審查，P0–P3 分級與輸出模板 |
| `refactor-optimize-pragmatic` | 務實重構：不過度設計、保留行為、小步驗證 |
| `karpathy-coding-principles` | 實作前的假設／最小改動／可驗證完成 |
| `plan-md-template-zh` | Cursor `plan.md` 繁中 frontmatter + 段落結構 |
| `validation-notes-generic-zh` | 給 QA 的驗證筆記五欄格式（需自行指定「版型參照檔」） |

另有最小範例：`examples/skill-minimal/SKILL.md`。

### 刻意未收錄（偏單一產品線）

下列 skill 與特定 C++ UI command／內部模組強綁定，**不適合當通用教材**，請留在私有 repo 或專案內：

- `option-checker-centralize`
- `cpp-header-thin-wrapper-hygiene`（內文大量引用上述重構脈絡）

若你們團隊剛好是同產品線，可自行從內部來源複製，不建議推進本共用 repo。

## 重新命名倉庫後（本機 `origin`）

若 GitHub 上曾用舊名稱 `cursor_skill_subagent`，現已改為 `981_agent_research`，GitHub 通常會把舊 URL 轉址到新名稱，但本機仍建議把 `origin` 改成新 URL（見下 `git remote set-url`）。

## Clone（協作者）

```bash
git clone https://github.com/civetcat/981_agent_research.git
cd 981_agent_research
```

## 第一次 push（本機已有 `origin` 時）

在專案目錄執行（需已登入 GitHub：PAT、`gh auth login`、或已設好的 SSH）：

```bash
git push -u origin main
```

若本機還沒加過遠端：

```bash
git remote add origin https://github.com/civetcat/981_agent_research.git
git branch -M main
git push -u origin main
```

若遠端已存在但仍是舊 URL，請改成：

```bash
git remote set-url origin https://github.com/civetcat/981_agent_research.git
# 或使用 SSH：
# git remote set-url origin git@github.com:civetcat/981_agent_research.git
```
