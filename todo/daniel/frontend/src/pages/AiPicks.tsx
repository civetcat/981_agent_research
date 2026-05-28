import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  AiPicksResponse,
  AiPickTheme,
  aiPicksApi,
} from "../api/client";
import BackButton from "../components/BackButton";

// 整個 SPA session 共用一份快取，按 (top_n, theme_hint) 分桶。
// 切走再切回完全不打 backend，更不打 Grok。
// 重新整理頁面會清掉這份 in-memory cache，讓使用者主動拿到最新。
const _sessionCache: Record<string, AiPicksResponse> = {};
const _cacheKey = (n: number, h: string) => `${n}|${h.trim()}`;

const HEAT_COLORS: Record<string, string> = {
  high: "bg-red-900/40 text-red-300 border-red-700",
  medium: "bg-amber-900/40 text-amber-300 border-amber-700",
  low: "bg-gray-700/40 text-gray-300 border-gray-600",
};

const CAT_COLORS: Record<string, string> = {
  AI: "bg-indigo-900/40 text-indigo-300 border-indigo-800",
  半導體: "bg-pink-900/40 text-pink-300 border-pink-800",
  電動車: "bg-emerald-900/40 text-emerald-300 border-emerald-800",
  軍工: "bg-stone-700/40 text-stone-300 border-stone-600",
  高股息: "bg-amber-900/40 text-amber-300 border-amber-800",
  重電: "bg-yellow-900/40 text-yellow-300 border-yellow-800",
  生技: "bg-green-900/40 text-green-300 border-green-800",
  加密: "bg-orange-900/40 text-orange-300 border-orange-800",
};

export default function AiPicks() {
  const [topN, setTopN] = useState(10);
  const [themeHint, setThemeHint] = useState("");
  // 已套用到 fetch 的版本（避免使用者改了輸入但還沒按「分析」就影響顯示）
  const [appliedN, setAppliedN] = useState(10);
  const [appliedHint, setAppliedHint] = useState("");

  const initialKey = _cacheKey(10, "");
  const [data, setData] = useState<AiPicksResponse | null>(
    _sessionCache[initialKey] || null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async (
    refresh: boolean,
    n: number = topN,
    hint: string = themeHint,
  ) => {
    setLoading(true);
    setError(null);
    try {
      const r = await aiPicksApi.get(refresh, n, hint);
      setData(r);
      setAppliedN(n);
      setAppliedHint(hint);
      _sessionCache[_cacheKey(n, hint)] = r;
      if (r.error) setError(r.error);
    } catch (e: any) {
      setError(e?.message || "載入失敗");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!_sessionCache[initialKey]) {
      load(false, 10, "");
    }
  }, []);

  // 「分析」按鈕：用目前輸入觸發新一輪推演
  const runAnalyze = () => {
    const n = Math.max(1, Math.min(20, topN));
    const hint = themeHint.trim();
    const key = _cacheKey(n, hint);
    // 已有 session memo 直接顯示；沒有才打 backend（backend 還會看 24h 檔案快取）
    if (_sessionCache[key]) {
      setData(_sessionCache[key]);
      setAppliedN(n);
      setAppliedHint(hint);
      return;
    }
    load(false, n, hint);
  };

  return (
    <div className="space-y-6">
      <BackButton />
      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">
            AI 選股
            <span className="ml-2 text-xs px-2 py-0.5 bg-indigo-900/40 text-indigo-300 border border-indigo-700 rounded">
              Grok-4 reasoning
            </span>
          </h1>
          <p className="text-sm text-gray-400 mt-1">
            用 Grok-4 推演<b className="text-indigo-300">目前正在發酵的題材</b>
            ，並列出每個題材底下最直接受惠的<b className="text-indigo-300">候選股 + 為什麼</b>
            。Grok 會即時從網路抓最新新聞、財報、政策、法人動向。
          </p>
          {data?.as_of_date && (
            <div className="mt-2 text-xs text-gray-500">
              分析基準日：
              <span className="font-mono text-gray-300">{data.as_of_date}</span>
              {data.web_search_used != null && (
                <span className="ml-3">
                  網路即時搜尋：
                  <span
                    className={
                      data.web_search_used ? "text-bull" : "text-amber-400"
                    }
                  >
                    {data.web_search_used ? "已啟用" : "未啟用（題材可能偏舊）"}
                  </span>
                </span>
              )}
              {data.from_cache ? (
                <span className="ml-3 text-emerald-400">
                  ✓ 從快取載入，未消耗 Grok token（24h 內生效）
                </span>
              ) : (
                <span className="ml-3 text-indigo-400">新鮮分析（剛打 Grok）</span>
              )}
              {data.generated_at && (
                <span className="ml-3 text-gray-500">
                  生成時間 {data.generated_at}
                </span>
              )}
            </div>
          )}
        </div>

        <button
          onClick={() => {
            if (
              data &&
              !confirm(
                "重新分析會強制呼叫 Grok-4 reasoning + 網路搜尋，需 30~90 秒並消耗 token。確定要繼續嗎？",
              )
            ) {
              return;
            }
            load(true, topN, themeHint.trim());
          }}
          disabled={loading}
          className="px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-md font-medium"
        >
          {loading ? "推演中⋯⋯" : "重新分析"}
        </button>
      </header>

      {/* 題材輸入 + Top N */}
      <section className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
        <div className="grid md:grid-cols-[1fr_auto_auto] gap-3 items-end">
          <div>
            <label className="text-xs text-gray-400 block mb-1">
              題材方向（可留空，留空則由 AI 自由選 top N）
            </label>
            <input
              value={themeHint}
              onChange={(e) => setThemeHint(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") runAnalyze();
              }}
              placeholder="例如：AI 伺服器、低軌道衛星、重電、Stablecoin"
              disabled={loading}
              className="w-full bg-gray-950/80 border border-gray-700 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-indigo-500 disabled:opacity-60"
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 block mb-1">Top N 題材</label>
            <input
              type="number"
              min={1}
              max={20}
              value={topN}
              onChange={(e) => setTopN(Number(e.target.value) || 10)}
              disabled={loading}
              className="w-24 bg-gray-950/80 border border-gray-700 rounded-md px-3 py-2 text-sm font-mono text-center focus:outline-none focus:border-indigo-500 disabled:opacity-60"
            />
          </div>
          <button
            onClick={runAnalyze}
            disabled={loading}
            className="px-5 py-2 text-sm bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 rounded-md font-medium"
            title="若同樣的 (Top N, 題材) 已分析過則直接取 session 快取，不會打 Grok"
          >
            分析
          </button>
        </div>
        {(appliedHint || appliedN !== 10) && data && (
          <div className="mt-2 text-xs text-gray-400">
            目前顯示：
            {appliedHint ? (
              <span className="ml-1 text-indigo-300">「{appliedHint}」</span>
            ) : (
              <span className="ml-1 text-gray-300">自由選題</span>
            )}
            <span className="ml-1">· Top {appliedN}</span>
          </div>
        )}
      </section>

      {error && (
        <div className="p-4 bg-red-900/40 border border-red-800 rounded text-sm">
          <div className="font-semibold mb-1">⚠ {error}</div>
          {data?.raw_excerpt && (
            <pre className="text-xs text-gray-400 mt-2 whitespace-pre-wrap">
              {data.raw_excerpt}
            </pre>
          )}
        </div>
      )}

      {loading && !data && (
        <div className="p-12 text-center text-gray-500">
          <div className="text-3xl mb-3">⌛</div>
          推演中（reasoning + 網路搜尋約需 30~90 秒）⋯⋯
        </div>
      )}

      {data?.themes && data.themes.length > 0 && (
        <div className="space-y-5">
          {data.themes.map((t, i) => (
            <ThemeCard key={`${t.name}-${i}`} theme={t} index={i} />
          ))}
        </div>
      )}

      {data?.citations && data.citations.length > 0 && (
        <details className="bg-gray-900/40 border border-gray-800 rounded-xl p-4">
          <summary className="cursor-pointer text-sm text-gray-300">
            參考來源（{data.citations.length} 條）
          </summary>
          <ul className="mt-3 space-y-1 text-xs">
            {data.citations.map((url, i) => (
              <li key={i}>
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-indigo-400 hover:underline break-all"
                >
                  [{i + 1}] {url}
                </a>
              </li>
            ))}
          </ul>
        </details>
      )}

      <div className="text-[11px] text-gray-500 leading-relaxed">
        <div>⚠ AI 推演結果不構成投資建議。模型可能對代號或事實有錯誤，請自行驗證。</div>
        <div className="mt-1">
          快取機制：切換 tab 走 session 記憶體（0 request、0 token）；
          重新整理會走 backend 24h 檔案快取（1 request、0 token）；
          只有按「重新分析」才會打 Grok（消耗 token）。
        </div>
      </div>
    </div>
  );
}

function ThemeCard({ theme: t, index }: { theme: AiPickTheme; index: number }) {
  const heatCls = HEAT_COLORS[t.heat_level] || HEAT_COLORS.medium;
  const catCls = CAT_COLORS[t.category] || "bg-gray-800 text-gray-300 border-gray-700";

  return (
    <article className="bg-gray-900/60 border border-gray-800 rounded-xl p-5 space-y-3">
      <header className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-baseline gap-3 flex-wrap">
          <span className="text-gray-500 font-mono text-sm">#{index + 1}</span>
          <h2 className="text-xl font-bold">{t.name}</h2>
          <span className={`px-2 py-0.5 text-xs rounded border ${catCls}`}>
            {t.category}
          </span>
          <span className={`px-2 py-0.5 text-xs rounded border ${heatCls}`}>
            熱度 {t.heat_level}
          </span>
        </div>
      </header>

      <p className="text-sm text-gray-300 leading-relaxed">{t.summary}</p>

      {t.drivers && t.drivers.length > 0 && (
        <div>
          <div className="text-xs text-gray-400 mb-1">關鍵驅動因素</div>
          <ul className="text-xs text-gray-300 grid sm:grid-cols-2 gap-x-4 gap-y-1">
            {t.drivers.map((d, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-indigo-500">▸</span>
                <span>{d}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {t.stocks && t.stocks.length > 0 && (
        <div className="grid md:grid-cols-2 gap-3">
          {t.stocks.map((s) => (
            <div
              key={s.symbol}
              className="bg-gray-800/40 border border-gray-700 rounded-lg p-3"
            >
              <div className="flex items-baseline justify-between gap-2">
                <Link
                  to={`/stock/${s.symbol}`}
                  className="text-indigo-400 hover:underline font-mono font-semibold"
                >
                  {s.symbol}
                </Link>
                <span className="text-sm text-gray-300 truncate">{s.name}</span>
              </div>
              <p className="text-xs text-gray-300 mt-2 leading-relaxed">
                {s.thesis}
              </p>
              {s.risks && (
                <p className="text-[11px] text-amber-400/80 mt-2 leading-relaxed">
                  ⚠ {s.risks}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </article>
  );
}
