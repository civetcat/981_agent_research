import { Agent, CursorAgentError } from "@cursor/sdk";
import { readFileSync, writeFileSync } from "node:fs";
import { argv, cwd as procCwd, exit } from "node:process";

type Scope = "code" | "design" | "general" | "all";

interface Args {
  prompt: string;
  models: string[];
  judge: string;
  scope: Scope;
  out?: string;
  cwd: string;
  verbose: boolean;
}

interface Answer {
  model: string;
  ok: boolean;
  text: string;
  elapsedMs: number;
  error?: string;
}

function parseArgs(): Args {
  const a = argv.slice(2);
  const get = (flag: string): string | undefined => {
    const i = a.indexOf(flag);
    return i >= 0 ? a[i + 1] : undefined;
  };
  const has = (flag: string) => a.includes(flag);

  let prompt = get("--prompt") ?? "";
  const promptFile = get("--prompt-file");
  if (promptFile) prompt = readFileSync(promptFile, "utf8");
  if (!prompt.trim()) {
    console.error("需要 --prompt 或 --prompt-file");
    exit(1);
  }

  const modelsRaw = get("--models");
  if (!modelsRaw) {
    console.error("需要 --models（逗號分隔）");
    exit(1);
  }
  const models = modelsRaw!.split(",").map((s) => s.trim()).filter(Boolean);
  if (models.length < 2) {
    console.error("--models 至少 2 個");
    exit(1);
  }

  const judge = get("--judge") ?? models[0];
  const scopeArg = (get("--scope") ?? "all") as Scope;
  if (!["code", "design", "general", "all"].includes(scopeArg)) {
    console.error("--scope 必須是 code|design|general|all");
    exit(1);
  }

  return {
    prompt,
    models,
    judge,
    scope: scopeArg,
    out: get("--out"),
    cwd: get("--cwd") ?? procCwd(),
    verbose: has("--verbose"),
  };
}

function extractText(result: unknown): string {
  // Agent.prompt 回傳結構有時 result 是字串、有時是 content blocks 陣列
  const r = result as {
    status?: string;
    result?: unknown;
    output?: unknown;
  };
  const candidate = r?.result ?? r?.output ?? r;
  if (typeof candidate === "string") return candidate;
  if (Array.isArray(candidate)) {
    return candidate
      .map((b: unknown) => {
        const blk = b as { type?: string; text?: string };
        if (blk?.type === "text" && typeof blk.text === "string") return blk.text;
        return "";
      })
      .join("\n")
      .trim();
  }
  if (candidate && typeof candidate === "object") {
    const obj = candidate as { text?: string; message?: { content?: unknown } };
    if (typeof obj.text === "string") return obj.text;
    if (obj.message?.content) return extractText(obj.message.content);
  }
  return JSON.stringify(candidate);
}

async function askModel(
  model: string,
  prompt: string,
  cwd: string,
  apiKey: string,
  verbose: boolean,
): Promise<Answer> {
  const t0 = Date.now();
  if (verbose) console.error(`[fan-out] start ${model}`);
  try {
    const result = await Agent.prompt(prompt, {
      apiKey,
      model: { id: model },
      local: { cwd },
    });
    const elapsedMs = Date.now() - t0;
    const status = (result as { status?: string }).status ?? "unknown";
    if (status === "error") {
      return {
        model,
        ok: false,
        text: "",
        elapsedMs,
        error: `run finished with status=error`,
      };
    }
    const text = extractText(result);
    if (verbose) console.error(`[fan-out] done  ${model} (${elapsedMs}ms, ${text.length} chars)`);
    return { model, ok: true, text, elapsedMs };
  } catch (err) {
    const elapsedMs = Date.now() - t0;
    const msg =
      err instanceof CursorAgentError
        ? `${err.message} (retryable=${(err as { isRetryable?: boolean }).isRetryable ?? "?"})`
        : err instanceof Error
          ? err.message
          : String(err);
    if (verbose) console.error(`[fan-out] FAIL  ${model}: ${msg}`);
    return { model, ok: false, text: "", elapsedMs, error: msg };
  }
}

const RUBRIC: Record<Exclude<Scope, "all">, string> = {
  code: [
    "正確性：邏輯與輸出是否正確、是否處理錯誤路徑",
    "邊界條件：null/空集合/上限/併發/race condition",
    "資源安全：thread / 記憶體 / handle / lock 釋放",
    "可測試性與可維護性",
    "相容性風險：API 破壞、版本相依、遷移成本",
  ].join("\n  - "),
  design: [
    "Trade-off 是否清楚、是否權衡多個方案",
    "可擴展性與未來變更成本",
    "複雜度是否與問題匹配（過度設計？欠設計？）",
    "維運成本：observability、failure mode、rollback",
    "替代方案是否被考慮",
  ].join("\n  - "),
  general: [
    "事實正確性與引用可信度",
    "推論是否完整、有無跳步",
    "前提假設是否成立",
    "是否回答了真正的問題",
  ].join("\n  - "),
};

function buildJudgePrompt(
  originalPrompt: string,
  answers: Answer[],
  scope: Scope,
): string {
  const rubricSections =
    scope === "all"
      ? (Object.keys(RUBRIC) as Array<Exclude<Scope, "all">>)
          .map((k) => `### ${k}\n  - ${RUBRIC[k]}`)
          .join("\n\n")
      : `### ${scope}\n  - ${RUBRIC[scope as Exclude<Scope, "all">]}`;

  const answerBlocks = answers
    .map((a, i) => {
      const head = `## 答案 ${i + 1}：${a.model}（${a.elapsedMs}ms${a.ok ? "" : "，FAILED"}）`;
      const body = a.ok ? a.text : `(此模型呼叫失敗：${a.error ?? "unknown"})`;
      return `${head}\n\n${body}`;
    })
    .join("\n\n---\n\n");

  return [
    "你是一個 judge。下面有原始問題與多個模型的答案，請依 rubric 交叉評比，找出共識、分歧、盲點，再給出收斂後的最終建議。",
    "",
    "# 原始問題",
    "",
    originalPrompt,
    "",
    "# 各模型答案",
    "",
    answerBlocks,
    "",
    "# Rubric",
    "",
    rubricSections,
    "",
    "# 輸出格式（請嚴格遵守）",
    "",
    "## 評分表",
    "",
    "| 模型 | 正確性 | 風險 | 一句話評語 |",
    "| --- | --- | --- | --- |",
    "（每個模型一列）",
    "",
    "## 共識",
    "（多數模型同意的點，列點）",
    "",
    "## 分歧",
    "（模型之間明顯不同的判斷，列點，標註誰主張什麼）",
    "",
    "## 盲點",
    "（所有或多數模型都漏掉但你認為重要的點）",
    "",
    "## 最終建議",
    "（整合後可直接執行的答案，務實、不過度設計）",
    "",
    "請用繁體中文，避免空話與場面話。",
  ].join("\n");
}

function formatReport(args: Args, answers: Answer[], judgeText: string): string {
  const head = [
    `# Multi-Model Judge Report`,
    ``,
    `- scope: \`${args.scope}\``,
    `- models: ${args.models.map((m) => `\`${m}\``).join(", ")}`,
    `- judge: \`${args.judge}\``,
    ``,
    `## 原始問題`,
    ``,
    args.prompt.trim(),
    ``,
  ].join("\n");

  const fanout = answers
    .map((a, i) => {
      const status = a.ok ? "OK" : `FAILED：${a.error}`;
      return [
        `<details>`,
        `<summary>答案 ${i + 1}：<code>${a.model}</code> — ${a.elapsedMs}ms — ${status}</summary>`,
        ``,
        a.ok ? a.text : "(略)",
        ``,
        `</details>`,
      ].join("\n");
    })
    .join("\n\n");

  return `${head}\n## 各模型原始答案\n\n${fanout}\n\n## Judge 評比\n\n${judgeText}\n`;
}

async function main() {
  const args = parseArgs();
  const apiKey = process.env.CURSOR_API_KEY;
  if (!apiKey) {
    console.error("CURSOR_API_KEY 未設定");
    exit(1);
  }

  if (args.verbose) {
    console.error(`[main] models=${args.models.join(",")} judge=${args.judge} scope=${args.scope}`);
  }

  const answers = await Promise.all(
    args.models.map((m) => askModel(m, args.prompt, args.cwd, apiKey, args.verbose)),
  );

  const okCount = answers.filter((a) => a.ok).length;
  if (okCount === 0) {
    console.error("所有 fan-out 模型都失敗，終止");
    for (const a of answers) console.error(`  - ${a.model}: ${a.error}`);
    exit(2);
  }

  const judgePrompt = buildJudgePrompt(args.prompt, answers, args.scope);
  if (args.verbose) console.error(`[judge] start ${args.judge}`);
  const judgeAnswer = await askModel(args.judge, judgePrompt, args.cwd, apiKey, args.verbose);
  if (!judgeAnswer.ok) {
    console.error(`judge 模型呼叫失敗：${judgeAnswer.error}`);
    exit(2);
  }

  const report = formatReport(args, answers, judgeAnswer.text);
  if (args.out) {
    writeFileSync(args.out, report, "utf8");
    console.error(`[main] 已寫入 ${args.out}`);
  } else {
    process.stdout.write(report);
  }
}

main().catch((err) => {
  console.error(err);
  exit(1);
});
