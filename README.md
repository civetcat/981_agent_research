# 981 Agent Research（Cursor Skills / Subagent / Hermes）

和朋友一起整理 **Cursor Skills**（`SKILL.md`）、**Subagent / Task** 範本、**Project Rules** 以及 **Hermes Agent** 客製化設定。

**GitHub：** [civetcat/981_agent_research](https://github.com/civetcat/981_agent_research)

## 倉庫根目錄結構（最新）

| 路徑             | 用途 |
|------------------|------|
| `skills/`        | 可複製的 Cursor `SKILL.md`（含各主題子目錄） |
| `agents/`        | 複製到 `.cursor/agents` 的角色定義（coder, judge, reviewer） |
| `rules/`         | Project Rules 範例（`.mdc`）；`cursor-rules-consolidated.mdc` 為 BMC 全域＋Git／commit 合併版 |
| `task-prompts/`  | Task／委派用的文字範本（`.txt`） |
| `docs/agent/`    | 各 Agent 工具的設定指南與截圖（Cursor + Grok、Hermes + Grok） |
| `USER.md`        | 使用者 Profile 模板（已改為可彈性修改版本） |

## 可共用 Skills 一覽表（`skills/`）

| Skill 名稱                        | 分類           | 主要功能 |
|----------------------------------|----------------|----------|
| `build-code-on-docker`           | Build          | 在 Docker 容器中編譯、測試、排除 build 錯誤 |
| `code-review-go-cpp-p0p3`        | Review         | Go/C++ 程式碼審查（P0–P3 嚴重度，繁體中文輸出） |
| `karpathy-coding-principles`     | Coding         | 實作 Karpathy 務實編碼原則（最小改動、可驗證） |
| `multi-model-judge`              | Judge          | 多模型並行執行 + Judge 模型交叉評比 |
| `produce-code`                   | Orchestrator   | 多 Agent 子代理工作流（Coder/Reviewer/Judge 分離） |
| `refactor-optimize-pragmatic`    | Refactor       | 務實重構：不過度設計、保留正確行為、小步驗證 |
| `hermes-memory-management`       | Productivity   | Hermes Agent 記憶體壓縮、知識提煉至 memory、清理舊 session |
| `plan-md-template-zh`            | Template       | Cursor `plan.md` 繁體中文標準模板 |
| `validation-notes-generic-zh`    | Validation     | 產生 QA 驗證筆記（五欄格式） |
| `skill-minimal`                  | Example        | 最小技能範例模板 |

## Hermes Agent 客製化設定

此專案包含 Hermes Agent 的使用者特定配置：

- **`USER.md`**：定義 persistent user profile 與 communication preferences，會注入到 Hermes Agent 的每一次對話。
  - **Core Tech Stack**：OpenBMC、Yocto Project、Linux Kernel Drivers、C/C++、Python、YOLOv8、Transformer、LangChain、Reinforcement Learning。
  - **Language Preference**：預設使用**繁體中文 (zh-TW)** 回覆，所有專有名詞、變數、函式、程式碼片段維持英文。
  - **Response Tone**：直截了當、專業且極度精簡。禁止不必要的客套語。
  - **Code Generation Rules**：C/Kernel 程式碼必須考量嵌入式系統的記憶體限制與硬體安全性；Yocto 變更需直接提供 bitbake recipe 或 bbappend；除錯時優先從 register-level、driver 層面分析。

**使用方式**：
- 將 `USER.md` 放在專案根目錄或 `~/.hermes/` 下
- Hermes Agent 啟動時會自動載入此檔案作為 persona 與偏好
- 所有互動將遵循「Simplicity First」、「Surgical Changes」以及 BMC 工程師的硬體導向思維

## 本機 Skills 常見位置

- 使用者層級：`~/.cursor/skills/`
- 專案層級：`.cursor/skills/`（可版本控制）

## 協作方式建議

1. Clone 此 repo 後，在專案內建立 `.cursor/skills/<你的主題>/SKILL.md`，透過 PR 或分支貢獻。
2. 個人敏感設定請勿 commit，可使用 `USER.md` 模板來自訂偏好。

---

**最後更新**：2026-05-06
