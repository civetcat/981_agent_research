import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { EtfRow, etfApi } from "../api/client";
import BackButton from "../components/BackButton";
import InfoTip from "../components/InfoTip";

// session 級快取：(market|category) → ETF 排行；類別清單只抓一次。
const _rankCache: Record<string, EtfRow[]> = {};
let _catCache: { key: string; label: string }[] | null = null;
const _ck = (market: string, category: string) => `${market}|${category}`;

type SortKey =
  | "symbol"
  | "name"
  | "category"
  | "last_close"
  | "aum"
  | "expense_ratio"
  | "dividend_yield"
  | "return_1m"
  | "return_3m"
  | "return_6m"
  | "return_1y"
  | "inst_net_5d"
  | "inst_net_20d";
type SortDir = "asc" | "desc";

const MARKETS: { key: "ALL" | "TW" | "US"; label: string }[] = [
  { key: "ALL", label: "全部" },
  { key: "TW", label: "台股 ETF" },
  { key: "US", label: "美股 ETF" },
];

export default function Etfs() {
  const navigate = useNavigate();
  const initialKey = _ck("ALL", "");
  const [items, setItems] = useState<EtfRow[]>(_rankCache[initialKey] || []);
  const [categories, setCategories] = useState<{ key: string; label: string }[]>(
    _catCache || [],
  );
  const [market, setMarket] = useState<"ALL" | "TW" | "US">("ALL");
  const [category, setCategory] = useState<string>("");
  const [sortKey, setSortKey] = useState<SortKey>("aum");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (_catCache) return;
    etfApi
      .categories()
      .then((c) => {
        _catCache = c;
        setCategories(c);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    const key = _ck(market, category);
    const cached = _rankCache[key];
    if (cached) {
      setItems(cached);
      setLoading(false);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    etfApi
      .ranking({
        market: market === "ALL" ? undefined : market,
        category: category || undefined,
      })
      .then((r) => {
        _rankCache[key] = r.items;
        setItems(r.items);
      })
      .catch((e) => setError(e?.message || "載入失敗"))
      .finally(() => setLoading(false));
  }, [market, category]);

  const sorted = useMemo(() => {
    const arr = items.slice();
    arr.sort((a, b) => {
      const va = (a as any)[sortKey];
      const vb = (b as any)[sortKey];
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      if (typeof va === "number" && typeof vb === "number") {
        return sortDir === "asc" ? va - vb : vb - va;
      }
      return sortDir === "asc"
        ? String(va).localeCompare(String(vb))
        : String(vb).localeCompare(String(va));
    });
    return arr;
  }, [items, sortKey, sortDir]);

  const onSort = (k: SortKey) => {
    if (sortKey === k) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(k);
      const descKeys: SortKey[] = [
        "aum",
        "dividend_yield",
        "return_1m",
        "return_3m",
        "return_6m",
        "return_1y",
        "inst_net_5d",
        "inst_net_20d",
        "last_close",
      ];
      setSortDir(descKeys.includes(k) ? "desc" : "asc");
    }
  };

  return (
    <div className="space-y-6">
      <BackButton />
      <header>
        <h1 className="text-2xl font-bold">ETF 排行</h1>
        <p className="text-sm text-gray-400 mt-1">
          策劃過的台股 / 美股主流 ETF 清單，用 ETF 適合的指標排序：規模 (AUM)、費用率、殖利率、多期報酬，台股另附三大法人近 5 / 20 日累計淨流向。
          <br />
          <span className="text-gray-500">
            資料來源：yfinance（規模/費用率/殖利率）+ TWSE T86（台股法人）+ 自算多期報酬。1 小時快取。
          </span>
        </p>
      </header>

      {/* 篩選 */}
      <section className="flex flex-wrap items-center gap-3 bg-gray-900/60 border border-gray-800 rounded-xl p-4">
        <div className="flex items-center gap-1">
          <span className="text-sm text-gray-400 mr-2">市場：</span>
          {MARKETS.map((m) => (
            <button
              key={m.key}
              onClick={() => setMarket(m.key)}
              className={`px-3 py-1.5 rounded text-sm transition ${
                market === m.key
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-800 text-gray-300 hover:bg-gray-700"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-1 flex-wrap">
          <span className="text-sm text-gray-400 mx-2">類別：</span>
          <button
            onClick={() => setCategory("")}
            className={`px-3 py-1.5 rounded text-sm ${
              category === ""
                ? "bg-indigo-600 text-white"
                : "bg-gray-800 text-gray-300 hover:bg-gray-700"
            }`}
          >
            全部
          </button>
          {categories.map((c) => (
            <button
              key={c.key}
              onClick={() => setCategory(c.key)}
              className={`px-3 py-1.5 rounded text-sm ${
                category === c.key
                  ? "bg-indigo-600 text-white"
                  : "bg-gray-800 text-gray-300 hover:bg-gray-700"
              }`}
            >
              {c.label}
            </button>
          ))}
        </div>

        <span className="ml-auto text-xs text-gray-500">
          {loading ? "載入中⋯" : `${items.length} 檔`}
        </span>
      </section>

      {error && (
        <div className="p-3 bg-red-900/40 border border-red-800 rounded text-sm">
          {error}
        </div>
      )}

      <section className="bg-gray-900/60 border border-gray-800 rounded-xl overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-800/50 text-gray-300">
            <tr>
              <SortHeader sk="symbol" cur={sortKey} dir={sortDir} onSort={onSort} align="left">
                代號 / 名稱
              </SortHeader>
              <SortHeader sk="category" cur={sortKey} dir={sortDir} onSort={onSort} align="left">
                類別
              </SortHeader>
              <SortHeader sk="last_close" cur={sortKey} dir={sortDir} onSort={onSort}>
                收盤
              </SortHeader>
              <SortHeader sk="aum" cur={sortKey} dir={sortDir} onSort={onSort}>
                規模 AUM
              </SortHeader>
              <SortHeader sk="expense_ratio" cur={sortKey} dir={sortDir} onSort={onSort}>
                費用率<InfoTip termKey="EXPENSE_RATIO" align="center" />
              </SortHeader>
              <SortHeader sk="dividend_yield" cur={sortKey} dir={sortDir} onSort={onSort}>
                殖利率<InfoTip termKey="DIVIDEND_YIELD" align="center" />
              </SortHeader>
              <SortHeader sk="return_1m" cur={sortKey} dir={sortDir} onSort={onSort}>
                1 個月
              </SortHeader>
              <SortHeader sk="return_3m" cur={sortKey} dir={sortDir} onSort={onSort}>
                3 個月
              </SortHeader>
              <SortHeader sk="return_6m" cur={sortKey} dir={sortDir} onSort={onSort}>
                6 個月
              </SortHeader>
              <SortHeader sk="return_1y" cur={sortKey} dir={sortDir} onSort={onSort}>
                1 年
              </SortHeader>
              <SortHeader sk="inst_net_5d" cur={sortKey} dir={sortDir} onSort={onSort}>
                法人 5 日
              </SortHeader>
            </tr>
          </thead>
          <tbody>
            {sorted.length === 0 ? (
              <tr>
                <td colSpan={11} className="p-6 text-center text-gray-500">
                  {loading ? "載入中⋯" : "目前條件下無資料"}
                </td>
              </tr>
            ) : (
              sorted.map((r) => (
                <tr
                  key={r.symbol}
                  className="border-t border-gray-800 hover:bg-indigo-900/20 cursor-pointer transition-colors"
                  onClick={() => navigate(`/stock/${r.symbol}`)}
                  title={`點擊分析 ${r.symbol}`}
                >
                  <td className="p-3">
                    <Link
                      to={`/stock/${r.symbol}`}
                      onClick={(e) => e.stopPropagation()}
                      className="text-indigo-400 hover:underline font-mono mr-2"
                    >
                      {r.symbol}
                    </Link>
                    <span className="text-gray-300">{r.name}</span>
                  </td>
                  <td className="p-3 text-xs text-gray-400">
                    <CategoryBadge cat={r.category} categories={categories} />
                  </td>
                  <td className="p-3 text-right font-mono">
                    {r.last_close?.toFixed(2)}
                  </td>
                  <td className="p-3 text-right font-mono text-gray-300" title="總淨資產 (USD/TWD)">
                    {fmtAum(r.aum, r.currency)}
                  </td>
                  <td className="p-3 text-right text-gray-400">
                    {r.expense_ratio != null ? `${r.expense_ratio}%` : "—"}
                  </td>
                  <td className="p-3 text-right text-emerald-400">
                    {r.dividend_yield != null ? `${r.dividend_yield}%` : "—"}
                  </td>
                  <ReturnCell value={r.return_1m} />
                  <ReturnCell value={r.return_3m} />
                  <ReturnCell value={r.return_6m} />
                  <ReturnCell value={r.return_1y} />
                  <td
                    className={`p-3 text-right font-mono text-xs ${
                      (r.inst_net_5d || 0) > 0
                        ? "text-bull"
                        : (r.inst_net_5d || 0) < 0
                        ? "text-bear"
                        : "text-gray-500"
                    }`}
                    title="台股三大法人近 5 個交易日累計淨買賣（股）"
                  >
                    {r.inst_net_5d != null ? fmtShares(r.inst_net_5d) : "—"}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>
    </div>
  );
}

function CategoryBadge({
  cat,
  categories,
}: {
  cat: string;
  categories: { key: string; label: string }[];
}) {
  const label = categories.find((c) => c.key === cat)?.label || cat;
  const color: Record<string, string> = {
    market_index: "bg-indigo-900/40 text-indigo-300 border-indigo-800",
    high_yield: "bg-emerald-900/40 text-emerald-300 border-emerald-800",
    thematic: "bg-pink-900/40 text-pink-300 border-pink-800",
    international: "bg-amber-900/40 text-amber-300 border-amber-800",
    bond: "bg-sky-900/40 text-sky-300 border-sky-800",
    reits_gold: "bg-yellow-900/40 text-yellow-300 border-yellow-800",
  };
  return (
    <span className={`px-1.5 py-0.5 text-xs rounded border ${color[cat] || ""}`}>
      {label}
    </span>
  );
}

function ReturnCell({ value }: { value: number | null }) {
  if (value == null) return <td className="p-3 text-right text-gray-500">—</td>;
  const positive = value >= 0;
  return (
    <td
      className={`p-3 text-right font-mono ${
        positive ? "text-bull" : "text-bear"
      }`}
    >
      {positive ? "+" : ""}
      {value.toFixed(2)}%
    </td>
  );
}

function SortHeader({
  sk,
  cur,
  dir,
  onSort,
  children,
  align = "right",
}: {
  sk: SortKey;
  cur: SortKey;
  dir: SortDir;
  onSort: (k: SortKey) => void;
  children: React.ReactNode;
  align?: "left" | "right";
}) {
  const active = cur === sk;
  return (
    <th
      onClick={() => onSort(sk)}
      className={`p-3 cursor-pointer select-none hover:bg-gray-700/50 ${
        align === "left" ? "text-left" : "text-right"
      }`}
    >
      <span className={active ? "text-indigo-400" : ""}>{children}</span>
      <span className="ml-1 text-xs text-gray-500">
        {active ? (dir === "asc" ? "▲" : "▼") : "↕"}
      </span>
    </th>
  );
}

function fmtAum(v: number | null, currency: string | null): string {
  if (v == null) return "—";
  const sym = currency === "TWD" ? "NT$" : "$";
  if (v >= 1e12) return `${sym}${(v / 1e12).toFixed(2)}T`;
  if (v >= 1e9) return `${sym}${(v / 1e9).toFixed(2)}B`;
  if (v >= 1e6) return `${sym}${(v / 1e6).toFixed(0)}M`;
  return `${sym}${v.toFixed(0)}`;
}

function fmtShares(v: number): string {
  // 台股「張」= 1000 股
  const lots = v / 1000;
  if (Math.abs(lots) >= 10000) return `${(lots / 10000).toFixed(1)}萬張`;
  return `${lots >= 0 ? "+" : ""}${lots.toFixed(0)}張`;
}
