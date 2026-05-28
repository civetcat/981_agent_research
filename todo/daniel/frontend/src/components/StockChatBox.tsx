import { useEffect, useRef, useState } from "react";
import { stocksApi } from "../api/client";

/**
 * 個股 AI 問答：使用者打字、按 Enter 送出，後端用 Grok 回覆。
 * 每次發問都會消耗 token，所以：
 *   - 第一次發問會跳 confirm
 *   - 後續同一個 session 內不再 confirm（已經點過同意）
 *   - 對話歷史按 symbol 存在 module-level memo：切走 tab 再回來仍保留，
 *     避免使用者重複問同一個問題浪費 token；只有重新整理瀏覽器才會清。
 */
interface Msg {
  role: "user" | "assistant";
  content: string;
  source?: string;
  ts: number;
}

// 跨整個 SPA session 保留每支股票的對話歷史
const _chatCache: Record<string, Msg[]> = {};
let _confirmedGlobally = false;

const PRESETS = [
  "這家公司是做什麼的？",
  "主要產品 / 服務有哪些？",
  "主要競爭對手是誰？",
  "最近有什麼重大新聞 / 事件？",
  "這家公司的營收 / 獲利結構？",
];

export default function StockChatBox({ symbol }: { symbol: string }) {
  const [msgs, setMsgs] = useState<Msg[]>(_chatCache[symbol] || []);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [confirmed, setConfirmed] = useState(_confirmedGlobally);
  const [error, setError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // 換股票時：從 module-level memo 拿這支股票的舊對話（沒有就空）
  useEffect(() => {
    setMsgs(_chatCache[symbol] || []);
    setInput("");
    setError(null);
  }, [symbol]);

  // msgs 變動就同步寫回 memo，下次切回來能秒顯示
  useEffect(() => {
    if (msgs.length === 0) {
      delete _chatCache[symbol];
    } else {
      _chatCache[symbol] = msgs;
    }
  }, [symbol, msgs]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
  }, [msgs, loading]);

  const send = async (q: string) => {
    const question = q.trim();
    if (!question || loading) return;

    if (!confirmed) {
      const ok = window.confirm(
        `對話會呼叫 Grok-4，每則回覆會消耗 token。\n` +
          "確定要繼續嗎？（整個瀏覽 session 僅提示一次）",
      );
      if (!ok) return;
      setConfirmed(true);
      _confirmedGlobally = true;
    }

    setError(null);
    const userMsg: Msg = { role: "user", content: question, ts: Date.now() };
    setMsgs((m) => [...m, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const history = msgs.map((m) => ({ role: m.role, content: m.content }));
      const r = await stocksApi.ask(symbol, question, history);
      setMsgs((m) => [
        ...m,
        {
          role: "assistant",
          content: r.answer,
          source: r.source,
          ts: Date.now(),
        },
      ]);
    } catch (e: any) {
      setError(e?.message || "AI 回覆失敗");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
      <header className="flex flex-wrap items-baseline justify-between gap-2 mb-3">
        <div className="flex items-baseline gap-2">
          <h3 className="font-semibold">問 AI 關於 {symbol}</h3>
          <span className="text-[10px] px-2 py-0.5 bg-indigo-900/40 text-indigo-300 border border-indigo-700 rounded">
            Grok
          </span>
        </div>
        <div className="text-[11px] text-amber-400/90">
          ⚠ 每次發問都會消耗 token（reasoning 模型較貴），請先想好問題再送出。
        </div>
      </header>

      {/* 對話區 */}
      <div
        ref={scrollRef}
        className="bg-black/30 border border-gray-800 rounded-lg p-3 h-[280px] overflow-y-auto space-y-3 text-sm scroll-smooth"
      >
        {msgs.length === 0 && !loading && (
          <div className="text-gray-500 text-sm h-full flex flex-col items-center justify-center gap-3">
            <div>沒有對話。試試以下問題：</div>
            <div className="flex flex-wrap gap-1.5 justify-center max-w-md">
              {PRESETS.map((p) => (
                <button
                  key={p}
                  onClick={() => send(p)}
                  className="px-2.5 py-1 text-[11px] bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-full text-gray-300"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        )}

        {msgs.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[85%] px-3 py-2 rounded-lg leading-relaxed whitespace-pre-wrap ${
                m.role === "user"
                  ? "bg-indigo-600/40 border border-indigo-700/60 text-gray-100"
                  : "bg-gray-800/70 border border-gray-700 text-gray-200"
              }`}
            >
              {m.content}
              {m.role === "assistant" && m.source === "rule" && (
                <div className="text-[10px] text-amber-400 mt-1.5">
                  （未設定 GROK_API_KEY，回覆為規則式）
                </div>
              )}
              {m.role === "assistant" && m.source === "error" && (
                <div className="text-[10px] text-red-400 mt-1.5">
                  （API 錯誤）
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="px-3 py-2 rounded-lg bg-gray-800/70 border border-gray-700 text-gray-400 text-xs flex items-center gap-2">
              <Spinner /> Grok 思考中⋯⋯
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="mt-2 text-xs text-red-400">⚠ {error}</div>
      )}

      {/* 輸入區 */}
      <div className="mt-3 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              send(input);
            }
          }}
          disabled={loading}
          placeholder="例如：這家公司主要做什麼？"
          className="flex-1 bg-gray-950/80 border border-gray-700 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-indigo-500 disabled:opacity-60"
        />
        <button
          onClick={() => send(input)}
          disabled={loading || !input.trim()}
          className="px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed rounded-md font-medium"
        >
          送出
        </button>
        {msgs.length > 0 && (
          <button
            onClick={() => {
              setMsgs([]);
              setError(null);
            }}
            disabled={loading}
            className="px-3 py-2 text-sm bg-gray-800 hover:bg-gray-700 disabled:opacity-50 border border-gray-700 rounded-md text-gray-300"
            title="清除對話歷史（不會影響 token，只清前端 state）"
          >
            清除
          </button>
        )}
      </div>
    </section>
  );
}

function Spinner() {
  return (
    <span className="inline-block w-3 h-3 border-2 border-gray-500 border-t-transparent rounded-full animate-spin" />
  );
}
