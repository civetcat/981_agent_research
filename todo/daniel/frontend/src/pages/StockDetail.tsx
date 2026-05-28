import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { stocksApi, OHLCVRow, StockInfo } from "../api/client";
import KLineChart from "../components/KLineChart";
import FundFlowSection from "../components/FundFlowSection";
import VerdictGauge from "../components/VerdictGauge";
import StockChatBox from "../components/StockChatBox";
import SymbolSearchBar from "../components/SymbolSearchBar";
import BackButton from "../components/BackButton";

const PERIODS = ["3mo", "6mo", "1y", "2y", "5y", "max"];

// session 級快取：(symbol|period) → 個股資訊。重新整理頁面會清掉。
interface DetailBundle {
  info: StockInfo | null;
  rows: OHLCVRow[];
  fundamentals: any;
}
const _detailCache: Record<string, DetailBundle> = {};
const _dk = (sym: string, period: string) => `${sym}|${period}`;

export default function StockDetail() {
  const { symbol = "2330.TW" } = useParams();
  const initialKey = _dk(symbol, "1y");
  const initialCache = _detailCache[initialKey];
  const [info, setInfo] = useState<StockInfo | null>(initialCache?.info ?? null);
  const [period, setPeriod] = useState("1y");
  const [rows, setRows] = useState<OHLCVRow[]>(initialCache?.rows ?? []);
  const [fundamentals, setFundamentals] = useState<any>(
    initialCache?.fundamentals ?? null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    const key = _dk(symbol, period);
    const cached = _detailCache[key];
    if (cached) {
      setInfo(cached.info);
      setRows(cached.rows);
      setFundamentals(cached.fundamentals);
      setLoading(false);
      return;
    }
    setLoading(true);
    Promise.all([
      stocksApi.info(symbol).catch(() => null),
      stocksApi
        .indicators(symbol, period, "sma_20,sma_60,bb,macd,rsi_14")
        .catch(() => null),
      stocksApi.fundamentals(symbol).catch(() => null),
    ])
      .then(([i, k, f]) => {
        const r = k?.data || [];
        setInfo(i);
        setRows(r);
        setFundamentals(f);
        if (!i || !k) {
          setError("無法取得資料，請確認股票代號或後端是否正常。");
        } else {
          _detailCache[key] = { info: i, rows: r, fundamentals: f };
        }
      })
      .finally(() => setLoading(false));
  }, [symbol, period]);

  const overlays = [
    {
      name: "SMA20",
      values: rows.map((r) => ({ date: r.date, value: (r as any).sma_20 ?? null })),
      color: "#fbbf24",
    },
    {
      name: "SMA60",
      values: rows.map((r) => ({ date: r.date, value: (r as any).sma_60 ?? null })),
      color: "#60a5fa",
    },
    {
      name: "BB Upper",
      values: rows.map((r) => ({ date: r.date, value: (r as any).bb_upper ?? null })),
      color: "#a78bfa",
    },
    {
      name: "BB Lower",
      values: rows.map((r) => ({ date: r.date, value: (r as any).bb_lower ?? null })),
      color: "#a78bfa",
    },
  ];

  return (
    <div className="space-y-6">
      <BackButton />
      <SymbolSearchBar />
      <header className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold">
            {info?.name || symbol}
            <span className="ml-3 text-base text-gray-400 font-normal">{symbol}</span>
          </h1>
          <div className="text-sm text-gray-400 mt-1 space-x-3">
            {info?.market && <span>{info.market}</span>}
            {info?.sector && <span>{info.sector}</span>}
            {info?.industry && <span>{info.industry}</span>}
          </div>
        </div>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 rounded text-sm ${
                period === p ? "bg-indigo-600 text-white" : "bg-gray-800 text-gray-300"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </header>

      {error && <div className="p-3 bg-red-900/40 border border-red-800 rounded">{error}</div>}

      <VerdictGauge symbol={symbol} />

      <section className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
        {loading && rows.length === 0 ? (
          <div className="h-[460px] flex items-center justify-center text-gray-500">載入中⋯⋯</div>
        ) : (
          <KLineChart
            data={rows}
            overlays={overlays}
            panes={["volume", "macd", "rsi"]}
          />
        )}
      </section>

      <section className="grid md:grid-cols-4 gap-4">
        <Stat label="本益比 PE" value={fmtNum(info?.pe ?? fundamentals?.pe)} />
        <Stat label="股價淨值比 PB" value={fmtNum(info?.pb ?? fundamentals?.pb)} />
        <Stat label="EPS" value={fmtNum(info?.eps)} />
        <Stat
          label="殖利率"
          value={
            (info?.dividend_yield ?? fundamentals?.dividend_yield) != null
              ? `${((info?.dividend_yield ?? fundamentals?.dividend_yield) * 100).toFixed(2)}%`
              : "—"
          }
        />
        <Stat label="市值" value={fmtBig(info?.market_cap)} />
        <Stat label="幣別" value={info?.currency || "—"} />
        <Stat label="交易所" value={info?.exchange || "—"} />
        <Stat label="資料來源" value={fundamentals?.source || "yfinance"} />
      </section>

      {fundamentals?.finmind && <FinMindSection data={fundamentals.finmind} />}

      <FundFlowSection symbol={symbol} />

      <StockChatBox symbol={symbol} />
    </div>
  );
}

function Stat({ label, value }: { label: string; value: any }) {
  return (
    <div className="p-4 bg-gray-900/60 border border-gray-800 rounded-lg">
      <div className="text-xs text-gray-400">{label}</div>
      <div className="text-lg font-semibold mt-1">{value ?? "—"}</div>
    </div>
  );
}

function FinMindSection({
  data,
}: {
  data: { monthly_revenue: any[]; dividend: any[] };
}) {
  const mr = data?.monthly_revenue || [];
  const div = data?.dividend || [];
  if (!mr.length && !div.length) return null;

  const recentMr = mr.slice(-12).reverse(); // 最近 12 個月

  return (
    <section className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
      <div className="flex items-baseline justify-between mb-3">
        <h3 className="font-semibold text-lg">財報重點（FinMind）</h3>
        <span className="text-xs text-gray-500">月營收 + 歷史股利</span>
      </div>

      <div className="grid lg:grid-cols-2 gap-6">
        {recentMr.length > 0 && (
          <div>
            <div className="text-sm text-gray-300 mb-2">月營收（近 12 個月）</div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="bg-gray-800/50 text-gray-400">
                  <tr>
                    <th className="p-2 text-left">月份</th>
                    <th className="p-2 text-right">營收 (千元)</th>
                    <th className="p-2 text-right">YoY</th>
                    <th className="p-2 text-right">MoM</th>
                  </tr>
                </thead>
                <tbody>
                  {recentMr.map((r) => (
                    <tr key={r.date} className="border-t border-gray-800">
                      <td className="p-2 font-mono text-gray-300">
                        {r.year}-{String(r.month).padStart(2, "0")}
                      </td>
                      <td className="p-2 text-right font-mono">
                        {r.revenue != null ? Number(r.revenue).toLocaleString() : "—"}
                      </td>
                      <td
                        className={`p-2 text-right font-mono ${
                          r.yoy_pct == null
                            ? "text-gray-500"
                            : r.yoy_pct >= 0
                            ? "text-bull"
                            : "text-bear"
                        }`}
                      >
                        {r.yoy_pct == null
                          ? "—"
                          : `${r.yoy_pct >= 0 ? "+" : ""}${r.yoy_pct}%`}
                      </td>
                      <td
                        className={`p-2 text-right font-mono ${
                          r.mom_pct == null
                            ? "text-gray-500"
                            : r.mom_pct >= 0
                            ? "text-bull"
                            : "text-bear"
                        }`}
                      >
                        {r.mom_pct == null
                          ? "—"
                          : `${r.mom_pct >= 0 ? "+" : ""}${r.mom_pct}%`}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {div.length > 0 && (
          <div>
            <div className="text-sm text-gray-300 mb-2">
              歷史股利（按年合併）
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead className="bg-gray-800/50 text-gray-400">
                  <tr>
                    <th className="p-2 text-left">年度</th>
                    <th className="p-2 text-right">現金股利</th>
                    <th className="p-2 text-right">股票股利</th>
                  </tr>
                </thead>
                <tbody>
                  {div
                    .slice()
                    .reverse()
                    .slice(0, 10)
                    .map((d) => (
                      <tr key={d.year} className="border-t border-gray-800">
                        <td className="p-2 font-mono text-gray-300">{d.year}</td>
                        <td className="p-2 text-right font-mono text-emerald-400">
                          {d.cash_dividend != null
                            ? d.cash_dividend.toFixed(2)
                            : "—"}
                        </td>
                        <td className="p-2 text-right font-mono text-amber-400">
                          {d.stock_dividend != null
                            ? d.stock_dividend.toFixed(2)
                            : "—"}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

function fmtNum(v: any): string {
  if (v == null || isNaN(v)) return "—";
  return Number(v).toFixed(2);
}
function fmtBig(v: any): string {
  if (v == null) return "—";
  if (v >= 1e12) return (v / 1e12).toFixed(2) + " T";
  if (v >= 1e9) return (v / 1e9).toFixed(2) + " B";
  if (v >= 1e6) return (v / 1e6).toFixed(2) + " M";
  return String(v);
}
