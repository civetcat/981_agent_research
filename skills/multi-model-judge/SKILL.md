---
name: multi-model-judge
description: 用 Cursor SDK 把同一個 prompt 並行丟給多個模型（快速/精準/平衡），再用 judge 模型交叉評比，找出盲點與分歧並給出收斂答案。當使用者提到「多模型互審」「代理互評」「跨模型 judge」「model 互相評比」「避免單一模型盲點」「fast model 跟 precise model 比一比」「跑三個模型再裁決」「multi-model judge」「cross-model review」「composer-2 跟 claude-opus 比較看看」「opus thinking 一份 fast 一份再 judge」時使用。產出每個模型的原始答案 + judge 的盲點/共識/分歧分析 + 最終建議。
disable-model-invocation: true
---

# Multi-Model Judge

## 目標

對同一個問題並行詢問多個 Cursor 模型（如 fast / precise / thinking），再用一個 judge 模型評比，避免單一模型的盲點與誤判。

跟 `multi-agent-dispatcher` 的差別：本 skill 真的跨「不同模型」，前者只是同一模型扮多角色。

## 觸發語意

- 「多模型互審」/「multi-model judge」
- 「代理互評」/「跨模型評比」/「cross-model review」
- 「跑三個 model 再 judge」/「fan out 多個模型」
- 「fast 跟 precise 比一比」
- 「避免單一模型盲點」/「怕某個 model 漏看」
- 「composer-2 跟 opus 都跑一份」
- 「thinking 一份 fast 一份再裁決」

## 前置條件

1. 已安裝 Node.js 18+。
2. 設好 `CURSOR_API_KEY` 環境變數（個人 key：<https://cursor.com/dashboard/integrations>；團隊 service account：<https://cursor.com/dashboard/team-settings>，見 [Service accounts](https://cursor.com/docs/account/enterprise/service-accounts.md)）。
3. 第一次使用時，在 **本 skill 目錄下的 `scripts/`** 執行 `npm install`。  
   - 從 [981_agent_research](https://github.com/civetcat/981_agent_research) clone 時，路徑為 `skills/multi-model-judge/scripts/`。  
   - 若已複製到 `~/.cursor/skills/multi-model-judge/`，則為該目錄下的 `scripts/`。

以下指令中的 `<skill-dir>` 請替換成你實際的 skill 根目錄（內含 `SKILL.md` 與 `scripts/`）。

## 使用流程

### Step 1：確認可用模型

不同帳號可用的模型不同，model ID 也會變。先列一次：

```bash
cd <skill-dir>/scripts
node --import tsx list-models.ts
```

把想用的 ID 記下來（例如一個 fast、一個重推理、一個平衡）。

### Step 2：跑互審

```bash
cd <skill-dir>/scripts
node --import tsx judge.ts \
  --prompt "你的問題" \
  --models gpt-5.5,claude-opus-4-7,claude-sonnet-4-6 \
  --judge claude-opus-4-7 \
  --scope code
```

或從檔案讀 prompt：

```bash
cd <skill-dir>/scripts
node --import tsx judge.ts --prompt-file ./question.md \
  --models gpt-5.5,claude-opus-4-7 \
  --judge claude-opus-4-7 \
  --scope all
```

### 參數

| 參數 | 必填 | 說明 |
|------|------|------|
| `--prompt` 或 `--prompt-file` | 必填擇一 | 問題內容或讀檔 |
| `--models` | 必填 | 逗號分隔 model id（建議 2-4 個） |
| `--judge` | 選填 | 裁決用 model id；預設取 `--models` 第一個 |
| `--scope` | 選填 | `code` / `design` / `general` / `all`，影響 rubric，預設 `all` |
| `--out` | 選填 | 輸出 markdown 檔路徑，預設 stdout |
| `--cwd` | 選填 | 給 local agent 的工作目錄，預設目前目錄 |

### Step 3：讀 judge 輸出

輸出 markdown 含：

- 每個模型的原始答案（折疊）
- Judge 評分表（正確性 / 風險 / 共識 / 分歧 / 盲點）
- 最終建議（整合後的可執行答案）

## Rubric（依 scope）

腳本內建三段 rubric，judge prompt 會依 `--scope` 帶入：

- **code**：正確性、邊界條件、執行緒/資源安全、可測試性、相容性風險
- **design**：trade-off、可擴展性、複雜度、維運成本、替代方案
- **general**：事實正確、推論完整、有無跳步、引用可信度

`all` 會三段都評。

## 約束

- 預設 `local` runtime，跑在 `--cwd` 指定的目錄（未指定則為執行指令時的 cwd）。
- 並行 fan-out 用 `Promise.all`；任一失敗不阻塞其他模型，judge 會看到「某 model 失敗」並照樣評估剩餘答案。
- 每個 fan-out 與 judge 都用 `Agent.prompt()`（一次性、會自動 dispose）。
- 為控成本，預設不串流；要看進度加 `--verbose`。

## 失敗排查

- `CursorAgentError`：通常是 API key 或網路；檢查 `CURSOR_API_KEY` 是否帶白空白。
- 某 model id 跑出 401/404：該帳號沒有該模型權限，先用 `list-models.ts` 確認。
- judge 輸出格式跑掉：用 `--scope` 收斂，或在 judge prompt template 加更明確的 markdown 結構要求（見 `scripts/judge.ts` 的 `buildJudgePrompt`）。
