import { useEffect, useMemo, useState } from "react";
import {
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { Link } from "react-router-dom";
import { portfolioApi, PortfolioState } from "../api/client";
import BackButton from "../components/BackButton";

let _stateCache: PortfolioState | null = null;

const PIE_COLORS = [
  "#818cf8", "#fbbf24", "#34d399", "#f472b6", "#60a5fa",
  "#a78bfa", "#fb7185", "#22d3ee", "#fde047", "#94a3b8",
];

export default function Portfolio() {
  const [state, setState] = useState<PortfolioState | null>(_stateCache);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // form state
  const [symbol, setSymbol] = useState("2330.TW");
  const [side, setSide] = useState<"BUY" | "SELL">("BUY");
  const [qty, setQty] = useState(1000);
  const [usePrice, setUsePrice] = useState(false);
  const [price, setPrice] = useState<number | "">("");
  const [submitting, setSubmitting] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try {
      const s = await portfolioApi.get();
      _stateCache = s;
      setState(s);
      setError(null);
    } catch (e: any) {
      setError(e?.message || "讀取失敗");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await portfolioApi.transact({
        symbol: symbol.toUpperCase(),
        side,
        qty,
        price: usePrice && price !== "" ? Number(price) : undefined,
      });
      await refresh();
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || "下單失敗");
    } finally {
      setSubmitting(false);
    }
  };

  const reset = async () => {
    const cashStr = prompt("重設投資組合 — 輸入新的起始本金：", "1000000");
    if (!cashStr) return;
    const cash = Number(cashStr);
    if (!cash || cash <= 0) {
      alert("金額必須 > 0");
      return;
    }
    if (!confirm(`會清空所有交易紀錄、現金重設為 ${cash.toLocaleString()}，確定？`)) return;
    await portfolioApi.reset(cash);
    await refresh();
  };

  const cashFlow = async (kind: "deposit" | "withdraw") => {
    const label = kind === "deposit" ? "入金" : "出金";
    const amtStr = prompt(`${label} — 輸入金額：`, "100000");
    if (!amtStr) return;
    const amt = Number(amtStr);
    if (!amt || amt <= 0) {
      alert("金額必須 > 0");
      return;
    }
    try {
      if (kind === "deposit") await portfolioApi.deposit(amt);
      else await portfolioApi.withdraw(amt);
      await refresh();
    } catch (e: any) {
      alert(e?.response?.data?.detail || `${label}失敗`);
    }
  };

  const allocation = useMemo(() => {
    if (!state) return [];
    const data = state.positions.map((p) => ({
      name: p.symbol,
      value: p.market_value,
    }));
    if (state.cash > 0) data.push({ name: "現金", value: state.cash });
    return data;
  }, [state]);

  if (!state) {
    return (
      <div className="text-gray-400 py-12 text-center">
        {loading ? "載入中⋯⋯" : error || "—"}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <BackButton />
      <header className="flex items-baseline justify-between flex-wrap gap-2">
        <h1 className="text-2xl font-bold">{state.name}</h1>
        <div className="flex gap-2">
          <button
            onClick={() => cashFlow("deposit")}
            className="px-3 py-1.5 text-sm bg-bull/80 hover:bg-bull text-white rounded"
          >
            入金
          </button>
          <button
            onClick={() => cashFlow("withdraw")}
            className="px-3 py-1.5 text-sm bg-bear/80 hover:bg-bear text-white rounded"
          >
            出金
          </button>
          <button
            onClick={reset}
            className="px-3 py-1.5 text-sm bg-gray-800 hover:bg-red-900/60 border border-gray-700 rounded"
          >
            重設組合
          </button>
        </div>
      </header>

      {/* 總覽 */}
      <section className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Card
          label="總資金"
          value={fmt$(state.total_invested)}
          sub={`累計入金（含初始）`}
        />
        <Card
          label="總權益"
          value={fmt$(state.total_equity)}
          sub={`現金 ${fmt$(state.cash)} + 持倉 ${fmt$(state.market_value)}`}
        />
        <Card
          label="總報酬"
          value={`${state.total_return_pct >= 0 ? "+" : ""}${state.total_return_pct.toFixed(2)}%`}
          accent={state.total_return_pct >= 0 ? "bull" : "bear"}
          sub={`vs 總資金`}
        />
        <Card label="可用現金" value={fmt$(state.cash)} />
        <Card
          label="未實現損益"
          value={fmt$(state.unrealized_pnl)}
          accent={state.unrealized_pnl >= 0 ? "bull" : "bear"}
          sub={`已實現 ${fmt$(state.realized_pnl)}`}
        />
      </section>

      <div className="grid lg:grid-cols-[1fr_360px] gap-6">
        {/* 持倉 + 紀錄 */}
        <div className="space-y-6">
          <section className="bg-gray-900/60 border border-gray-800 rounded-xl">
            <h3 className="px-4 py-3 border-b border-gray-800 font-semibold">目前持倉</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-gray-400 bg-gray-800/40">
                  <tr>
                    <th className="text-left p-3">代號</th>
                    <th className="text-right p-3">數量</th>
                    <th className="text-right p-3">均成本</th>
                    <th className="text-right p-3">現價</th>
                    <th className="text-right p-3">市值</th>
                    <th className="text-right p-3">未實現</th>
                    <th className="text-right p-3">權重</th>
                  </tr>
                </thead>
                <tbody>
                  {state.positions.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="p-6 text-center text-gray-500">
                        尚無持倉，從右側下單開始。
                      </td>
                    </tr>
                  ) : (
                    state.positions.map((p) => (
                      <tr key={p.symbol} className="border-t border-gray-800 hover:bg-gray-800/30">
                        <td className="p-3 font-mono">
                          <Link to={`/stock/${p.symbol}`} className="text-indigo-400 hover:underline">
                            {p.symbol}
                          </Link>
                        </td>
                        <td className="p-3 text-right">{p.qty}</td>
                        <td className="p-3 text-right">{p.avg_cost.toFixed(2)}</td>
                        <td className="p-3 text-right">{p.last_price?.toFixed(2) ?? "—"}</td>
                        <td className="p-3 text-right">{fmt$(p.market_value)}</td>
                        <td
                          className={`p-3 text-right ${
                            p.unrealized_pnl >= 0 ? "text-bull" : "text-bear"
                          }`}
                        >
                          {fmt$(p.unrealized_pnl)}
                          {p.unrealized_pct != null && (
                            <span className="text-xs ml-1">
                              ({p.unrealized_pct >= 0 ? "+" : ""}
                              {p.unrealized_pct.toFixed(2)}%)
                            </span>
                          )}
                        </td>
                        <td className="p-3 text-right text-gray-400">{p.weight.toFixed(1)}%</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>

          <section className="bg-gray-900/60 border border-gray-800 rounded-xl">
            <h3 className="px-4 py-3 border-b border-gray-800 font-semibold">交易紀錄</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-gray-400 bg-gray-800/40">
                  <tr>
                    <th className="text-left p-3">時間</th>
                    <th className="text-left p-3">代號</th>
                    <th className="text-left p-3">方向</th>
                    <th className="text-right p-3">數量</th>
                    <th className="text-right p-3">價格</th>
                    <th className="text-right p-3">手續費</th>
                  </tr>
                </thead>
                <tbody>
                  {state.transactions.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="p-6 text-center text-gray-500">
                        無紀錄
                      </td>
                    </tr>
                  ) : (
                    state.transactions.slice(0, 30).map((t) => (
                      <tr key={t.id} className="border-t border-gray-800">
                        <td className="p-3 text-gray-400">{t.executed_at?.slice(0, 19).replace("T", " ")}</td>
                        <td className="p-3 font-mono">{t.symbol}</td>
                        <td
                          className={`p-3 font-semibold ${
                            t.side === "BUY" ? "text-bull" : "text-bear"
                          }`}
                        >
                          {t.side}
                        </td>
                        <td className="p-3 text-right">{t.qty}</td>
                        <td className="p-3 text-right">{t.price.toFixed(2)}</td>
                        <td className="p-3 text-right text-gray-500">{t.fee.toFixed(2)}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        {/* 下單 + 配置 */}
        <aside className="space-y-6">
          <section className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
            <h3 className="font-semibold mb-3">下單</h3>
            <form onSubmit={submit} className="space-y-3">
              <div>
                <Label>代號</Label>
                <input
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                  className={inputCls}
                />
              </div>
              <div>
                <Label>方向</Label>
                <div className="grid grid-cols-2 gap-2">
                  {(["BUY", "SELL"] as const).map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => setSide(s)}
                      className={`py-2 rounded font-semibold text-sm ${
                        side === s
                          ? s === "BUY"
                            ? "bg-bull/80 text-white"
                            : "bg-bear/80 text-white"
                          : "bg-gray-800 text-gray-400"
                      }`}
                    >
                      {s === "BUY" ? "買進" : "賣出"}
                    </button>
                  ))}
                </div>
              </div>
              <div>
                <Label>數量</Label>
                <input
                  type="number"
                  step="any"
                  value={qty}
                  onChange={(e) => setQty(+e.target.value)}
                  className={inputCls}
                />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={usePrice}
                  onChange={(e) => setUsePrice(e.target.checked)}
                />
                指定價格（不勾以最近收盤價成交）
              </label>
              {usePrice && (
                <input
                  type="number"
                  step="any"
                  value={price}
                  onChange={(e) => setPrice(e.target.value === "" ? "" : +e.target.value)}
                  placeholder="例如 580.5"
                  className={inputCls}
                />
              )}
              {error && (
                <div className="text-sm text-red-400 bg-red-900/30 border border-red-800 rounded p-2">
                  {error}
                </div>
              )}
              <button
                disabled={submitting}
                type="submit"
                className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded font-medium"
              >
                {submitting ? "送單中⋯⋯" : `確認${side === "BUY" ? "買進" : "賣出"}`}
              </button>
            </form>
          </section>

          <section className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
            <h3 className="font-semibold mb-3">資產配置</h3>
            {allocation.length === 0 ? (
              <div className="h-40 flex items-center justify-center text-gray-500 text-sm">
                尚無資料
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie
                    data={allocation}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    label={(e) => e.name}
                    labelLine={false}
                  >
                    {allocation.map((_, i) => (
                      <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={(v: any) => fmt$(Number(v))}
                    contentStyle={{ background: "#111827", border: "1px solid #374151" }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12 }} />
                </PieChart>
              </ResponsiveContainer>
            )}
          </section>
        </aside>
      </div>
    </div>
  );
}

const inputCls =
  "w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded focus:outline-none focus:border-indigo-500 text-sm";

function Label({ children }: { children: React.ReactNode }) {
  return <div className="text-xs text-gray-400 mb-1">{children}</div>;
}

function Card({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: "bull" | "bear";
}) {
  const color = accent === "bull" ? "text-bull" : accent === "bear" ? "text-bear" : "";
  return (
    <div className="p-4 bg-gray-900/60 border border-gray-800 rounded-lg">
      <div className="text-xs text-gray-400">{label}</div>
      <div className={`text-xl font-semibold mt-1 ${color}`}>{value}</div>
      {sub && <div className="text-xs text-gray-500 mt-1">{sub}</div>}
    </div>
  );
}

function fmt$(v: number): string {
  if (v == null || isNaN(v)) return "—";
  const sign = v < 0 ? "-" : "";
  const abs = Math.abs(v);
  return `${sign}$${abs.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}
