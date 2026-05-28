import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { FundFlowPayload, fundFlowApi } from "../api/client";

const COLOR_FOREIGN = "#ef4444"; // 紅 — 外資
const COLOR_TRUST = "#10b981"; // 綠 — 投信
const COLOR_DEALER = "#fbbf24"; // 黃 — 自營商

const CHART_BG = "#0b0f17";
const GRID = "#1f2937";
const AXIS = "#6b7280";

// Session 級快取：同一支股票的資金流向，同次造訪不重抓
const _flowCache: Record<string, FundFlowPayload> = {};

export default function FundFlowSection({ symbol }: { symbol: string }) {
  const [payload, setPayload] = useState<FundFlowPayload | null>(
    _flowCache[symbol] || null,
  );
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    // 已有快取直接顯示，不發 request
    if (_flowCache[symbol]) {
      setPayload(_flowCache[symbol]);
      return;
    }
    setLoading(true);
    setPayload(null);
    fundFlowApi
      .get(symbol)
      .then((p) => {
        _flowCache[symbol] = p;
        setPayload(p);
      })
      .catch((e) => setError(e?.message || "資金流向資料載入失敗"))
      .finally(() => setLoading(false));
  }, [symbol]);

  return (
    <div className="space-y-6">
      <section className="bg-gray-900/60 border border-gray-800 rounded-xl p-5">
        <div className="flex items-baseline justify-between mb-4">
          <h3 className="font-semibold text-lg">資金流向觀察</h3>
          {payload && (
            <span className="text-xs text-gray-500">
              市場：{payload.market}　•　近 {payload.indicators.length} 日技術指標
            </span>
          )}
        </div>

        {loading && <div className="text-gray-500 text-sm">載入中⋯⋯</div>}
        {error && (
          <div className="p-3 bg-red-900/40 border border-red-800 rounded text-sm">
            {error}
          </div>
        )}
        {payload?.warnings && payload.warnings.length > 0 && (
          <div className="mb-3 p-2 bg-amber-900/30 border border-amber-800 rounded text-xs text-amber-300">
            部分資料來源暫時無法取得：{payload.warnings.join("；")}
          </div>
        )}

        {payload && payload.market === "TW" && (
          <TwInstitutional rows={payload.tw_institutional || []} />
        )}
        {payload && payload.market === "US" && (
          <UsHoldings
            insider={payload.us_insider || []}
            institutional={payload.us_institutional || []}
          />
        )}
        {payload && <Indicators rows={payload.indicators} />}
      </section>

    </div>
  );
}

function TwInstitutional({ rows }: { rows: import("../api/client").TwInstitutionalRow[] }) {
  if (rows.length === 0) {
    return (
      <div className="text-sm text-gray-500">
        近期沒有抓到三大法人資料（可能 TWSE 暫無回應或非交易日尚未公布）。
      </div>
    );
  }
  const last5 = [...rows].slice(-5).reverse();
  return (
    <div className="space-y-4">
      <div>
        <div className="text-sm text-gray-400 mb-2">三大法人買賣超（張）— 近 30 日</div>
        <div style={{ width: "100%", height: 240 }}>
          <ResponsiveContainer>
            <BarChart data={rows} stackOffset="sign" style={{ background: CHART_BG }}>
              <CartesianGrid stroke={GRID} strokeDasharray="3 3" />
              <XAxis dataKey="date" stroke={AXIS} fontSize={11} />
              <YAxis stroke={AXIS} fontSize={11} />
              <Tooltip
                contentStyle={{ background: "#0f172a", border: `1px solid ${GRID}` }}
                labelStyle={{ color: "#cbd5e1" }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <ReferenceLine y={0} stroke={AXIS} />
              <Bar dataKey="foreign" name="外資" stackId="a" fill={COLOR_FOREIGN} />
              <Bar dataKey="trust" name="投信" stackId="a" fill={COLOR_TRUST} />
              <Bar dataKey="dealer" name="自營商" stackId="a" fill={COLOR_DEALER} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div>
        <div className="text-sm text-gray-400 mb-2">最近 5 日明細（張）</div>
        <table className="w-full text-sm">
          <thead className="text-gray-400">
            <tr className="border-b border-gray-800">
              <th className="text-left py-1.5">日期</th>
              <th className="text-right">外資</th>
              <th className="text-right">投信</th>
              <th className="text-right">自營商</th>
              <th className="text-right">合計</th>
            </tr>
          </thead>
          <tbody>
            {last5.map((r) => (
              <tr key={r.date} className="border-b border-gray-900">
                <td className="py-1.5">{r.date}</td>
                <td className={`text-right ${cls(r.foreign)}`}>{fmt(r.foreign)}</td>
                <td className={`text-right ${cls(r.trust)}`}>{fmt(r.trust)}</td>
                <td className={`text-right ${cls(r.dealer)}`}>{fmt(r.dealer)}</td>
                <td className={`text-right font-semibold ${cls(r.net)}`}>{fmt(r.net)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function UsHoldings({
  insider,
  institutional,
}: {
  insider: import("../api/client").InsiderRow[];
  institutional: import("../api/client").InstitutionalHolder[];
}) {
  return (
    <div className="grid md:grid-cols-2 gap-6">
      <div>
        <div className="text-sm text-gray-400 mb-2">內部人交易（最近 10 筆）</div>
        {insider.length === 0 ? (
          <div className="text-sm text-gray-500">無資料</div>
        ) : (
          <table className="w-full text-xs">
            <thead className="text-gray-400">
              <tr className="border-b border-gray-800">
                <th className="text-left py-1">日期</th>
                <th className="text-left">人員</th>
                <th className="text-left">類型</th>
                <th className="text-right">股數</th>
                <th className="text-right">金額</th>
              </tr>
            </thead>
            <tbody>
              {insider.slice(0, 10).map((r, i) => (
                <tr key={i} className="border-b border-gray-900">
                  <td className="py-1">{r.date || "—"}</td>
                  <td>
                    <div className="truncate max-w-[140px]" title={r.insider || ""}>
                      {r.insider || "—"}
                    </div>
                    <div className="text-gray-500 text-[10px]">{r.position || ""}</div>
                  </td>
                  <td className={txClass(r.transaction)}>{r.transaction || "—"}</td>
                  <td className="text-right">{fmt(r.shares)}</td>
                  <td className="text-right">{fmtBig(r.value)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div>
        <div className="text-sm text-gray-400 mb-2">機構持股 Top 10</div>
        {institutional.length === 0 ? (
          <div className="text-sm text-gray-500">無資料</div>
        ) : (
          <table className="w-full text-xs">
            <thead className="text-gray-400">
              <tr className="border-b border-gray-800">
                <th className="text-left py-1">機構</th>
                <th className="text-right">股數</th>
                <th className="text-right">市值</th>
                <th className="text-right">佔比</th>
              </tr>
            </thead>
            <tbody>
              {institutional.slice(0, 10).map((h, i) => (
                <tr key={i} className="border-b border-gray-900">
                  <td className="py-1">
                    <div className="truncate max-w-[160px]" title={h.holder || ""}>
                      {h.holder || "—"}
                    </div>
                    <div className="text-gray-500 text-[10px]">{h.date_reported || ""}</div>
                  </td>
                  <td className="text-right">{fmt(h.shares)}</td>
                  <td className="text-right">{fmtBig(h.value)}</td>
                  <td className="text-right">{fmtPct(h.pct_held)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function Indicators({
  rows,
}: {
  rows: import("../api/client").MoneyFlowIndicatorRow[];
}) {
  if (rows.length === 0) return null;
  const data = rows;
  return (
    <div className="grid md:grid-cols-3 gap-4 mt-6">
      <MiniChart
        title="MFI (14)"
        data={data.map((r) => ({ date: r.date, value: r.mfi }))}
        domain={[0, 100]}
        refs={[20, 80]}
        color="#a78bfa"
      />
      <MiniChart
        title="OBV"
        data={data.map((r) => ({ date: r.date, value: r.obv }))}
        color="#60a5fa"
      />
      <MiniChart
        title="量能 z-score (vs 20d)"
        data={data.map((r) => ({ date: r.date, value: r.vol_z }))}
        refs={[-2, 2]}
        color="#fbbf24"
      />
    </div>
  );
}

function MiniChart({
  title,
  data,
  domain,
  refs,
  color,
}: {
  title: string;
  data: { date: string; value: number | null }[];
  domain?: [number, number];
  refs?: number[];
  color: string;
}) {
  const yDomain: any = domain ?? ["auto", "auto"];
  return (
    <div>
      <div className="text-xs text-gray-400 mb-1">{title}</div>
      <div style={{ width: "100%", height: 140 }}>
        <ResponsiveContainer>
          <LineChart data={data} style={{ background: CHART_BG }}>
            <CartesianGrid stroke={GRID} strokeDasharray="3 3" />
            <XAxis dataKey="date" stroke={AXIS} fontSize={10} hide />
            <YAxis stroke={AXIS} fontSize={10} domain={yDomain} />
            <Tooltip
              contentStyle={{ background: "#0f172a", border: `1px solid ${GRID}` }}
              labelStyle={{ color: "#cbd5e1" }}
            />
            {refs?.map((r) => (
              <ReferenceLine key={r} y={r} stroke={AXIS} strokeDasharray="2 2" />
            ))}
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function fmt(v: number | null | undefined): string {
  if (v == null || isNaN(v as number)) return "—";
  return Number(v).toLocaleString("en-US", { maximumFractionDigits: 1 });
}

function fmtBig(v: number | null | undefined): string {
  if (v == null) return "—";
  const n = Number(v);
  if (!isFinite(n)) return "—";
  if (Math.abs(n) >= 1e12) return (n / 1e12).toFixed(2) + " T";
  if (Math.abs(n) >= 1e9) return (n / 1e9).toFixed(2) + " B";
  if (Math.abs(n) >= 1e6) return (n / 1e6).toFixed(2) + " M";
  return n.toLocaleString();
}

function fmtPct(v: number | null | undefined): string {
  if (v == null) return "—";
  const n = Number(v);
  if (!isFinite(n)) return "—";
  // yfinance pctHeld 通常是 0~1 區間
  const pct = n < 1 && n > -1 ? n * 100 : n;
  return pct.toFixed(2) + "%";
}

function cls(v: number | null | undefined): string {
  if (v == null) return "";
  if (v > 0) return "text-red-400";
  if (v < 0) return "text-emerald-400";
  return "text-gray-400";
}

function txClass(t: string | null | undefined): string {
  if (!t) return "";
  const s = t.toLowerCase();
  if (s.includes("buy") || s.includes("purchase")) return "text-red-400";
  if (s.includes("sale") || s.includes("sell")) return "text-emerald-400";
  return "";
}
