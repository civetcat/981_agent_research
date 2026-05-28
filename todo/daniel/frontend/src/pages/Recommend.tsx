import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import {
  RecommendItem,
  RecommendRun,
  recommendApi,
  portfolioApi,
} from "../api/client";
import BackButton from "../components/BackButton";
import InfoTip from "../components/InfoTip";

const HORIZONS = [5, 10, 15, 20, 30];

// session 級快取：切換 tab 後切回不重打 API。重新整理頁面會清掉。
const _cache: Record<number, { run: RecommendRun | null; items: RecommendItem[] }> = {};
let _strategyMapCache: Record<number, string> | null = null;

type SortKey =
  | "symbol"
  | "last_close"
  | "signal_date"
  | "win_rate"
  | "avg_win_pct"
  | "avg_loss_pct"
  | "expected_return_pct"
  | "n_trades"
  | "max_drawdown_pct"
  | "target_high"
  | "target_low"
  | "risk_reward_ratio";
type SortDir = "asc" | "desc";

interface Filters {
  win_rate_min: string;       // %，例 50
  expected_return_min: string; // %，例 3
  avg_win_min: string;         // %，例 10（勝幅至少要這麼高）
  avg_loss_max: string;        // %，正值，例 5（敗時損失「不超過」這個 %）
}

const DEFAULT_FILTERS: Filters = {
  win_rate_min: "",
  expected_return_min: "",
  avg_win_min: "",
  avg_loss_max: "",
};

export default function Recommend() {
  const [searchParams] = useSearchParams();
  const initHorizon = (() => {
    const h = parseInt(searchParams.get("horizon") || "");
    return HORIZONS.includes(h) ? h : 10;
  })();
  const [horizon, setHorizon] = useState(initHorizon);
  const [strategyMap, setStrategyMap] = useState<Record<number, string>>(
    _strategyMapCache || {},
  );
  const [run, setRun] = useState<RecommendRun | null>(_cache[initHorizon]?.run ?? null);
  const [items, setItems] = useState<RecommendItem[]>(
    _cache[initHorizon]?.items ?? [],
  );
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [sortKey, setSortKey] = useState<SortKey>("expected_return_pct");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [topN, setTopN] = useState<number>(10);

  const refresh = async (h: number) => {
    try {
      const r = await recommendApi.latest(h, 200); // 抓多一點，前端做篩選/排序/截斷
      setRun(r.run);
      setItems(r.results);
      _cache[h] = { run: r.run, items: r.results };
      setError(null);
    } catch (e: any) {
      setError(e?.message || "載入失敗");
    }
  };

  useEffect(() => {
    if (_strategyMapCache) return;
    recommendApi.horizons().then((hs) => {
      const m: Record<number, string> = {};
      hs.forEach((h) => (m[h.horizon] = h.strategy));
      _strategyMapCache = m;
      setStrategyMap(m);
    });
  }, []);

  useEffect(() => {
    const cached = _cache[horizon];
    if (cached) {
      setRun(cached.run);
      setItems(cached.items);
    }
    // 仍背景刷新，但已先秒顯示舊資料
    refresh(horizon);
  }, [horizon]);

  const startScan = async (universe: "top500" | "tw" | "us" | "all") => {
    if (scanning) return;
    setScanning(true);
    setError(null);
    try {
      const { run_id } = await recommendApi.scan(horizon, universe);
      const poll = async () => {
        try {
          const s = await recommendApi.scanStatus(run_id);
          setRun(s);
          if (s.status === "done" || s.status === "failed") {
            setScanning(false);
            await refresh(horizon);
          } else {
            pollRef.current = window.setTimeout(poll, 2000);
          }
        } catch {
          setScanning(false);
        }
      };
      poll();
    } catch (e: any) {
      setScanning(false);
      setError(e?.response?.data?.detail || e?.message || "掃描失敗");
    }
  };

  useEffect(
    () => () => {
      if (pollRef.current) clearTimeout(pollRef.current);
    },
    []
  );

  // ---- 篩選 + 排序 ----
  const visible = useMemo(() => {
    let arr = items.slice();

    const wr = parseFloat(filters.win_rate_min);
    const er = parseFloat(filters.expected_return_min);
    const aw = parseFloat(filters.avg_win_min);
    const al = parseFloat(filters.avg_loss_max);

    if (!isNaN(wr)) arr = arr.filter((r) => r.win_rate * 100 >= wr);
    if (!isNaN(er)) arr = arr.filter((r) => r.expected_return_pct >= er);
    if (!isNaN(aw)) arr = arr.filter((r) => r.avg_win_pct >= aw);
    // 平均敗幅：使用者輸入正值 5 表示「敗時損失不超過 5%」→ avg_loss_pct >= -5
    if (!isNaN(al)) arr = arr.filter((r) => r.avg_loss_pct >= -Math.abs(al));

    arr.sort((a, b) => {
      const va = (a as any)[sortKey];
      const vb = (b as any)[sortKey];
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;
      if (typeof va === "number" && typeof vb === "number") {
        return sortDir === "asc" ? va - vb : vb - va;
      }
      const sa = String(va);
      const sb = String(vb);
      return sortDir === "asc" ? sa.localeCompare(sb) : sb.localeCompare(sa);
    });

    return arr.slice(0, topN);
  }, [items, filters, sortKey, sortDir, topN]);

  const totalAfterFilter = useMemo(() => {
    const wr = parseFloat(filters.win_rate_min);
    const er = parseFloat(filters.expected_return_min);
    const aw = parseFloat(filters.avg_win_min);
    const al = parseFloat(filters.avg_loss_max);
    return items.filter((r) => {
      if (!isNaN(wr) && r.win_rate * 100 < wr) return false;
      if (!isNaN(er) && r.expected_return_pct < er) return false;
      if (!isNaN(aw) && r.avg_win_pct < aw) return false;
      if (!isNaN(al) && r.avg_loss_pct < -Math.abs(al)) return false;
      return true;
    }).length;
  }, [items, filters]);

  const onSort = (k: SortKey) => {
    if (sortKey === k) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(k);
      // 預設方向：價格/勝率/期望/勝幅/交易次數 → desc；敗幅/最大回撤/代號/日期 → asc
      const descKeys: SortKey[] = [
        "expected_return_pct",
        "win_rate",
        "avg_win_pct",
        "n_trades",
        "last_close",
        "target_high",
        "risk_reward_ratio",
      ];
      setSortDir(descKeys.includes(k) ? "desc" : "asc");
    }
  };

  return (
    <div className="space-y-6">
      <BackButton />
      <header>
        <h1 className="text-2xl font-bold">推薦選股</h1>
        <p className="text-sm text-gray-400 mt-1">
          依持有期匹配對應策略，掃描股票池中最近 3 個交易日內出現進場訊號的標的，依「歷史回測期望值」排序。
          <br />
          <span className="text-gray-500">
            預期報酬 = 勝率 × 平均勝幅 + (1 − 勝率) × 平均敗幅。樣本必須 ≥ 3 筆完整交易才會列入。
          </span>
        </p>
      </header>

      {/* 持有期 */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-sm text-gray-400 mr-2">持有期：</span>
        {HORIZONS.map((h) => (
          <button
            key={h}
            onClick={() => setHorizon(h)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition ${
              h === horizon
                ? "bg-indigo-600 text-white"
                : "bg-gray-800 text-gray-300 hover:bg-gray-700"
            }`}
            title={strategyMap[h]}
          >
            {h} 天
          </button>
        ))}
        <span className="text-xs text-gray-500 ml-2">
          {strategyMap[horizon] && `策略：${strategyMap[horizon]}`}
        </span>
      </div>

      {/* 掃描狀態 */}
      <section className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
        <div className="flex items-center justify-between flex-wrap gap-3">
          <div className="text-sm text-gray-300">
            {run ? (
              <>
                上次掃描：
                <span className="text-gray-100 font-mono">
                  {run.finished_at?.replace("T", " ").slice(0, 19) || "—"}
                </span>
                <span className="ml-3 text-gray-500">
                  範圍 <b>{run.universe}</b> ・ 掃 {run.scanned}/{run.total} ・
                  命中 <b className="text-indigo-400">{run.matched}</b>
                </span>
                {scanning && (
                  <span className="ml-2 text-yellow-400">
                    （掃描中：{run.scanned}/{run.total}）
                  </span>
                )}
              </>
            ) : (
              <span className="text-gray-500">尚未掃描，按下方按鈕開始</span>
            )}
          </div>

          <div className="flex gap-2">
            <button
              disabled={scanning}
              onClick={() => startScan("top500")}
              className="px-3 py-1.5 text-sm bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded"
            >
              掃 Top 500
            </button>
            <button
              disabled={scanning}
              onClick={() => startScan("tw")}
              className="px-3 py-1.5 text-sm bg-gray-800 hover:bg-gray-700 disabled:opacity-50 rounded"
            >
              全台股
            </button>
            <button
              disabled={scanning}
              onClick={() => startScan("us")}
              className="px-3 py-1.5 text-sm bg-gray-800 hover:bg-gray-700 disabled:opacity-50 rounded"
            >
              全美股
            </button>
            <button
              disabled={scanning}
              onClick={() => startScan("all")}
              className="px-3 py-1.5 text-sm bg-red-900/60 hover:bg-red-900 border border-red-800 disabled:opacity-50 rounded"
              title="掃所有股票（耗時很久）"
            >
              全市場
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-3 text-sm text-red-400 bg-red-900/30 border border-red-800 rounded p-2">
            {error}
          </div>
        )}
      </section>

      {/* 篩選器 */}
      <section className="bg-gray-900/60 border border-gray-800 rounded-xl p-4">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-sm font-semibold text-gray-200">篩選條件：</span>

          <FilterField
            label="勝率 ≥"
            tip="WIN_RATE"
            unit="%"
            value={filters.win_rate_min}
            onChange={(v) => setFilters((f) => ({ ...f, win_rate_min: v }))}
            placeholder="50"
          />
          <FilterField
            label="預期報酬 ≥"
            tip="EXPECTED_RETURN"
            unit="%"
            value={filters.expected_return_min}
            onChange={(v) => setFilters((f) => ({ ...f, expected_return_min: v }))}
            placeholder="3"
          />
          <FilterField
            label="平均勝幅 ≥"
            tip="AVG_WIN"
            unit="%"
            value={filters.avg_win_min}
            onChange={(v) => setFilters((f) => ({ ...f, avg_win_min: v }))}
            placeholder="10"
          />
          <FilterField
            label="平均敗幅 ≤"
            tip="AVG_LOSS"
            unit="%"
            value={filters.avg_loss_max}
            onChange={(v) => setFilters((f) => ({ ...f, avg_loss_max: v }))}
            placeholder="5"
            hint="輸入正值。例如填 5 表示「賠時平均虧損不超過 5%」"
          />

          <button
            onClick={() => setFilters(DEFAULT_FILTERS)}
            className="px-2.5 py-1.5 text-xs bg-gray-800 hover:bg-gray-700 rounded"
          >
            清除
          </button>

          <div className="ml-auto flex items-center gap-2 text-sm">
            <span className="text-gray-400">顯示前</span>
            <select
              value={topN}
              onChange={(e) => setTopN(+e.target.value)}
              className="px-2 py-1 bg-gray-800 border border-gray-700 rounded text-sm"
            >
              {[5, 10, 15, 20, 30, 50, 100, 200].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
            <span className="text-gray-400">名</span>
          </div>
        </div>

        <div className="mt-2 text-xs text-gray-500">
          原始命中 {items.length} 檔 → 篩選後 {totalAfterFilter} 檔 → 顯示 {visible.length} 檔
        </div>
      </section>

      {/* 結果表 */}
      <section className="bg-gray-900/60 border border-gray-800 rounded-xl overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-800/50 text-gray-300">
            <tr>
              <SortHeader sk="symbol" cur={sortKey} dir={sortDir} onSort={onSort} align="left">
                代號 / 名稱
              </SortHeader>
              <SortHeader sk="last_close" cur={sortKey} dir={sortDir} onSort={onSort}>
                收盤
              </SortHeader>
              <SortHeader sk="signal_date" cur={sortKey} dir={sortDir} onSort={onSort} align="left">
                訊號日
              </SortHeader>
              <SortHeader sk="win_rate" cur={sortKey} dir={sortDir} onSort={onSort}>
                勝率<InfoTip termKey="WIN_RATE" align="center" />
              </SortHeader>
              <SortHeader sk="avg_win_pct" cur={sortKey} dir={sortDir} onSort={onSort}>
                平均勝幅<InfoTip termKey="AVG_WIN" align="center" />
              </SortHeader>
              <SortHeader sk="avg_loss_pct" cur={sortKey} dir={sortDir} onSort={onSort}>
                平均敗幅<InfoTip termKey="AVG_LOSS" align="center" />
              </SortHeader>
              <SortHeader sk="expected_return_pct" cur={sortKey} dir={sortDir} onSort={onSort}>
                預期報酬<InfoTip termKey="EXPECTED_RETURN" align="center" />
              </SortHeader>
              <SortHeader sk="target_high" cur={sortKey} dir={sortDir} onSort={onSort}>
                預期目標
              </SortHeader>
              <SortHeader sk="target_low" cur={sortKey} dir={sortDir} onSort={onSort}>
                停損參考
              </SortHeader>
              <SortHeader sk="risk_reward_ratio" cur={sortKey} dir={sortDir} onSort={onSort}>
                賠率比<InfoTip termKey="RR" align="center" />
              </SortHeader>
              <SortHeader sk="n_trades" cur={sortKey} dir={sortDir} onSort={onSort}>
                樣本
              </SortHeader>
              <SortHeader sk="max_drawdown_pct" cur={sortKey} dir={sortDir} onSort={onSort}>
                最大回撤
              </SortHeader>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {visible.length === 0 ? (
              <tr>
                <td colSpan={13} className="p-6 text-center text-gray-500">
                  {items.length === 0
                    ? `目前持有期 ${horizon} 天沒有命中標的，可換期或重新掃描。`
                    : "目前篩選條件下無結果，請放寬條件。"}
                </td>
              </tr>
            ) : (
              visible.map((r, i) => (
                <tr key={r.symbol} className="border-t border-gray-800 hover:bg-gray-800/30">
                  <td className="p-3">
                    <div className="flex items-center gap-2">
                      <span className="text-gray-500 text-xs w-5">#{i + 1}</span>
                      <Link
                        to={`/stock/${r.symbol}`}
                        className="text-indigo-400 hover:underline font-mono"
                      >
                        {r.symbol}
                      </Link>
                      <span className="text-gray-300">{r.name || "—"}</span>
                    </div>
                  </td>
                  <td className="p-3 text-right font-mono">{r.last_close.toFixed(2)}</td>
                  <td className="p-3 text-gray-300">{r.signal_date}</td>
                  <td className="p-3 text-right">{(r.win_rate * 100).toFixed(0)}%</td>
                  <td className="p-3 text-right text-bull">+{r.avg_win_pct.toFixed(2)}%</td>
                  <td className="p-3 text-right text-bear">{r.avg_loss_pct.toFixed(2)}%</td>
                  <td
                    className={`p-3 text-right font-semibold ${
                      r.expected_return_pct >= 0 ? "text-bull" : "text-bear"
                    }`}
                  >
                    {r.expected_return_pct >= 0 ? "+" : ""}
                    {r.expected_return_pct.toFixed(2)}%
                  </td>
                  <td className="p-3 text-right font-mono text-bull" title="歷史平均贏單漲幅外推">
                    {r.target_high != null ? r.target_high.toFixed(2) : "—"}
                  </td>
                  <td className="p-3 text-right font-mono text-bear" title="歷史平均輸單跌幅外推">
                    {r.target_low != null ? r.target_low.toFixed(2) : "—"}
                  </td>
                  <td className="p-3 text-right text-gray-300" title="平均勝幅 / 平均敗幅 (絕對值)">
                    {r.risk_reward_ratio != null ? r.risk_reward_ratio.toFixed(2) : "—"}
                  </td>
                  <td className="p-3 text-right text-gray-400">{r.n_trades}</td>
                  <td className="p-3 text-right text-gray-400">
                    {r.max_drawdown_pct.toFixed(1)}%
                  </td>
                  <td className="p-3 text-right">
                    <QuickBuyButton symbol={r.symbol} />
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

function FilterField({
  label,
  unit,
  value,
  onChange,
  placeholder,
  hint,
  tip,
}: {
  label: string;
  unit?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  hint?: string;
  tip?: string;
}) {
  return (
    <div className="flex items-center gap-1.5" title={hint}>
      <span className="text-xs text-gray-400 inline-flex items-center">
        {label}
        {tip && <InfoTip termKey={tip} />}
      </span>
      <input
        type="number"
        step="any"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-20 px-2 py-1 bg-gray-800 border border-gray-700 rounded text-sm text-right
                   focus:outline-none focus:border-indigo-500"
      />
      {unit && <span className="text-xs text-gray-500">{unit}</span>}
    </div>
  );
}

function QuickBuyButton({ symbol }: { symbol: string }) {
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);

  const buy = async () => {
    const qtyStr = prompt(`快速買進 ${symbol}，輸入股數：`, "100");
    if (!qtyStr) return;
    const qty = Number(qtyStr);
    if (!qty || qty <= 0) return;
    setBusy(true);
    try {
      await portfolioApi.transact({ symbol, side: "BUY", qty });
      setDone(true);
      setTimeout(() => setDone(false), 2000);
    } catch (e: any) {
      alert(e?.response?.data?.detail || "下單失敗");
    } finally {
      setBusy(false);
    }
  };

  return (
    <button
      onClick={buy}
      disabled={busy}
      className={`px-2 py-1 text-xs rounded ${
        done
          ? "bg-green-700 text-white"
          : "bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50"
      }`}
    >
      {done ? "已買進" : busy ? "⋯" : "快速買"}
    </button>
  );
}
