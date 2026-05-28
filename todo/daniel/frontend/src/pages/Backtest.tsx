import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { backtestApi, BacktestResult, MultiBacktestResult } from "../api/client";
import { Link, useSearchParams } from "react-router-dom";
import BackButton from "../components/BackButton";
import InfoTip from "../components/InfoTip";

interface Strategy {
  key: string;
  name: string;
  description: string;
  params: Record<string, number>;
}

// session 級快取：策略清單不會變，重打浪費。回測結果按 (mode|symbols|strategy|params|start|end|cash) 快取。
let _strategiesCache: Strategy[] | null = null;
const _resultCache: Record<string, BacktestResult> = {};
const _multiCache: Record<string, MultiBacktestResult> = {};

export default function Backtest() {
  const [searchParams] = useSearchParams();
  const initStrategy = searchParams.get("strategy") || "ma_cross";
  const initSymbol = searchParams.get("symbol")?.toUpperCase() || "2330.TW";

  const [strategies, setStrategies] = useState<Strategy[]>(_strategiesCache || []);
  const [mode, setMode] = useState<"single" | "multi">("single");
  const [symbol, setSymbol] = useState(initSymbol);
  const [symbolsText, setSymbolsText] = useState("2330.TW, AAPL, NVDA, TSLA, 0050.TW");
  const [strategy, setStrategy] = useState(initStrategy);
  const [params, setParams] = useState<Record<string, number>>({});
  const [start, setStart] = useState("2018-01-01");
  const [end, setEnd] = useState("");
  const [initCash, setInitCash] = useState(100000);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [multiResult, setMultiResult] = useState<MultiBacktestResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (_strategiesCache) return;
    backtestApi.strategies().then((s) => {
      _strategiesCache = s;
      setStrategies(s);
      if (s.length > 0) {
        // 已透過 init 從 query 設過 strategy；只在當前 strategy 不存在於清單時覆寫
        if (!s.find((x: Strategy) => x.key === strategy)) {
          setStrategy(s[0].key);
          setParams({ ...s[0].params });
        }
      }
    });
  }, []);

  useEffect(() => {
    const meta = strategies.find((s) => s.key === strategy);
    if (meta) setParams({ ...meta.params });
  }, [strategy, strategies]);

  const run = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    setMultiResult(null);
    try {
      if (mode === "single") {
        const key = JSON.stringify(["s", symbol, strategy, params, start, end, initCash]);
        if (_resultCache[key]) {
          setResult(_resultCache[key]);
        } else {
          const r = await backtestApi.run({
            symbol,
            strategy,
            params,
            start: start || undefined,
            end: end || undefined,
            init_cash: initCash,
          });
          _resultCache[key] = r;
          setResult(r);
        }
      } else {
        const symbols = symbolsText
          .split(/[,，\s]+/)
          .map((s) => s.trim().toUpperCase())
          .filter(Boolean);
        if (symbols.length === 0) {
          setError("請輸入至少一個代號");
          return;
        }
        const key = JSON.stringify(["m", symbols, strategy, params, start, end, initCash]);
        if (_multiCache[key]) {
          setMultiResult(_multiCache[key]);
        } else {
          const r = await backtestApi.runMulti({
            symbols,
            strategy,
            params,
            start: start || undefined,
            end: end || undefined,
            init_cash: initCash,
          });
          _multiCache[key] = r;
          setMultiResult(r);
        }
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || "回測失敗");
    } finally {
      setLoading(false);
    }
  };

  const chartData = useMemo(() => {
    if (!result) return [];
    const bench = new Map(result.benchmark_curve.map((p) => [p.date, p.value]));
    return result.equity_curve.map((p) => ({
      date: p.date,
      strategy: p.value,
      benchmark: bench.get(p.date) ?? null,
    }));
  }, [result]);

  return (
    <div className="space-y-4">
      <BackButton />
      <div className="grid lg:grid-cols-[340px_1fr] gap-6">
      <aside className="bg-gray-900/60 border border-gray-800 rounded-xl p-5 space-y-4 h-fit">
        <h2 className="text-lg font-semibold">回測設定</h2>

        <div>
          <Label>模式</Label>
          <div className="grid grid-cols-2 gap-2">
            {(["single", "multi"] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setMode(m)}
                className={`py-2 rounded text-sm font-medium ${
                  mode === m ? "bg-indigo-600 text-white" : "bg-gray-800 text-gray-400"
                }`}
              >
                {m === "single" ? "單檔詳細" : "多檔比較"}
              </button>
            ))}
          </div>
        </div>

        {mode === "single" ? (
          <div>
            <Label>股票代號</Label>
            <input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              className={inputCls}
            />
          </div>
        ) : (
          <div>
            <Label>股票代號清單（逗號 / 換行分隔，最多 200 檔）</Label>
            <textarea
              value={symbolsText}
              onChange={(e) => setSymbolsText(e.target.value)}
              rows={4}
              className={inputCls}
              placeholder="2330.TW, AAPL, NVDA"
            />
          </div>
        )}

        <div>
          <Label>策略</Label>
          <select value={strategy} onChange={(e) => setStrategy(e.target.value)} className={inputCls}>
            {strategies.map((s) => (
              <option key={s.key} value={s.key}>
                {s.name}
              </option>
            ))}
          </select>
          {strategies.find((s) => s.key === strategy)?.description && (
            <p className="text-xs text-gray-500 mt-1">
              {strategies.find((s) => s.key === strategy)?.description}
            </p>
          )}
        </div>

        {Object.keys(params).length > 0 && (
          <div className="space-y-2 pt-2 border-t border-gray-800">
            <div className="text-sm font-semibold text-gray-300">策略參數</div>
            {Object.entries(params).map(([k, v]) => (
              <div key={k}>
                <Label>
                  {k}
                  {k === "fast" && <InfoTip termKey="FAST_LINE" />}
                  {k === "slow" && <InfoTip termKey="SLOW_LINE" />}
                </Label>
                <input
                  type="number"
                  step="any"
                  value={v}
                  onChange={(e) =>
                    setParams((p) => ({ ...p, [k]: Number(e.target.value) }))
                  }
                  className={inputCls}
                />
              </div>
            ))}
          </div>
        )}

        <div className="grid grid-cols-2 gap-2">
          <div>
            <Label>起始日<InfoTip termKey="START_DATE" /></Label>
            <input
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              className={inputCls}
            />
          </div>
          <div>
            <Label>結束日<InfoTip termKey="END_DATE" align="left" /></Label>
            <input
              type="date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              className={inputCls}
            />
          </div>
        </div>

        <div>
          <Label>初始資金<InfoTip termKey="INIT_CASH" /></Label>
          <input
            type="number"
            value={initCash}
            onChange={(e) => setInitCash(+e.target.value)}
            className={inputCls}
          />
        </div>

        <button
          disabled={loading}
          onClick={run}
          className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg font-medium"
        >
          {loading ? "回測中⋯⋯" : "執行回測"}
        </button>
      </aside>

      <section className="space-y-4">
        {error && (
          <div className="p-3 bg-red-900/40 border border-red-800 rounded">{error}</div>
        )}

        {!result && !multiResult && !error && (
          <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-12 text-center text-gray-500">
            設定左側參數後按下「執行回測」。
          </div>
        )}

        {multiResult && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Metric label="掃描檔數" value={String(multiResult.scanned)} />
              <Metric
                label="獲利檔比"
                value={`${multiResult.summary.profit_ratio.toFixed(1)}%`}
                accent
              />
              <Metric
                label="平均報酬"
                value={pct(multiResult.summary.avg_total_return)}
                accent
              />
              <Metric
                label="平均最大回撤"
                value={pct(multiResult.summary.avg_max_drawdown)}
                negative
              />
            </div>

            <div className="bg-gray-900/60 border border-gray-800 rounded-xl overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-gray-800/50 text-gray-400">
                  <tr>
                    <th className="text-left p-3">代號</th>
                    <th className="text-right p-3">總報酬</th>
                    <th className="text-right p-3">年化</th>
                    <th className="text-right p-3">Sharpe</th>
                    <th className="text-right p-3">最大回撤</th>
                    <th className="text-right p-3">勝率</th>
                    <th className="text-right p-3">交易次數</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {multiResult.results.map((r) => (
                    <tr key={r.symbol} className="border-t border-gray-800 hover:bg-gray-800/30">
                      <td className="p-3 font-mono">
                        <Link to={`/stock/${r.symbol}`} className="text-indigo-400 hover:underline">
                          {r.symbol}
                        </Link>
                      </td>
                      <td
                        className={`p-3 text-right font-semibold ${
                          (r.total_return ?? 0) >= 0 ? "text-bull" : "text-bear"
                        }`}
                      >
                        {pct(r.total_return)}
                      </td>
                      <td className="p-3 text-right">{pct(r.annual_return)}</td>
                      <td className="p-3 text-right">{num(r.sharpe)}</td>
                      <td className="p-3 text-right text-bear">{pct(r.max_drawdown)}</td>
                      <td className="p-3 text-right">{pct(r.win_rate)}</td>
                      <td className="p-3 text-right text-gray-400">{r.trades}</td>
                      <td className="p-3 text-right">
                        <button
                          onClick={() => {
                            setMode("single");
                            setSymbol(r.symbol);
                            setMultiResult(null);
                          }}
                          className="text-xs text-indigo-400 hover:underline"
                        >
                          詳細 →
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {multiResult.failures.length > 0 && (
              <details className="bg-gray-900/60 border border-gray-800 rounded-xl p-4 text-sm">
                <summary className="cursor-pointer text-gray-400">
                  失敗檔數：{multiResult.failures.length}
                </summary>
                <div className="mt-2 space-y-1 text-xs text-gray-500">
                  {multiResult.failures.map((f) => (
                    <div key={f.symbol}>
                      <span className="font-mono">{f.symbol}</span>: {f.error}
                    </div>
                  ))}
                </div>
              </details>
            )}
          </>
        )}

        {result && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Metric label="總報酬率" value={pct(result.metrics.total_return)} accent />
              <Metric label="年化報酬" value={pct(result.metrics.annual_return)} />
              <Metric label="最大回撤" value={pct(result.metrics.max_drawdown)} negative />
              <Metric label="Sharpe" value={num(result.metrics.sharpe)} />
              <Metric label="Sortino" value={num(result.metrics.sortino)} />
              <Metric label="勝率" value={pct(result.metrics.win_rate)} />
              <Metric label="交易次數" value={String(result.metrics.trades)} />
              <Metric label="持倉時間" value={pct(result.metrics.exposure)} />
            </div>

            <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
              <h3 className="font-semibold mb-2">權益曲線（vs 買入並持有）</h3>
              <ResponsiveContainer width="100%" height={360}>
                <LineChart data={chartData}>
                  <CartesianGrid stroke="#1f2937" strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fill: "#9ca3af", fontSize: 12 }} minTickGap={40} />
                  <YAxis tick={{ fill: "#9ca3af", fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{ background: "#111827", border: "1px solid #374151" }}
                    formatter={(v: any) => Number(v).toFixed(0)}
                  />
                  <Legend />
                  <Line type="monotone" dataKey="strategy" stroke="#818cf8" dot={false} name="策略" />
                  <Line type="monotone" dataKey="benchmark" stroke="#94a3b8" dot={false} name="買進持有" />
                </LineChart>
              </ResponsiveContainer>
            </div>

            <div className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
              <h3 className="font-semibold mb-3">交易紀錄（最近 20 筆）</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="text-gray-400">
                    <tr>
                      <th className="text-left p-2">進場日</th>
                      <th className="text-left p-2">出場日</th>
                      <th className="text-right p-2">進場價</th>
                      <th className="text-right p-2">出場價</th>
                      <th className="text-right p-2">損益</th>
                      <th className="text-right p-2">報酬率</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.trades.slice(-20).reverse().map((t, i) => (
                      <tr key={i} className="border-t border-gray-800">
                        <td className="p-2">{t.entry_date?.slice(0, 10)}</td>
                        <td className="p-2">{t.exit_date?.slice(0, 10) ?? "持倉中"}</td>
                        <td className="p-2 text-right">{num(t.entry_price)}</td>
                        <td className="p-2 text-right">{num(t.exit_price)}</td>
                        <td
                          className={`p-2 text-right ${
                            (t.pnl ?? 0) >= 0 ? "text-bull" : "text-bear"
                          }`}
                        >
                          {num(t.pnl)}
                        </td>
                        <td
                          className={`p-2 text-right ${
                            (t.return_pct ?? 0) >= 0 ? "text-bull" : "text-bear"
                          }`}
                        >
                          {pct(t.return_pct)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        )}
      </section>
      </div>
    </div>
  );
}

const inputCls =
  "w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded focus:outline-none focus:border-indigo-500 text-sm";

function Label({ children }: { children: React.ReactNode }) {
  return <div className="text-xs text-gray-400 mb-1">{children}</div>;
}

function Metric({
  label,
  value,
  accent,
  negative,
}: {
  label: string;
  value: string;
  accent?: boolean;
  negative?: boolean;
}) {
  const color = accent ? "text-indigo-400" : negative ? "text-bear" : "";
  return (
    <div className="p-3 bg-gray-900/60 border border-gray-800 rounded-lg">
      <div className="text-xs text-gray-400">{label}</div>
      <div className={`text-lg font-semibold mt-1 ${color}`}>{value}</div>
    </div>
  );
}

function pct(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return "—";
  return `${v.toFixed(2)}%`;
}
function num(v: number | null | undefined): string {
  if (v == null || isNaN(v)) return "—";
  return v.toFixed(2);
}
