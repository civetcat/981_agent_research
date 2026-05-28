import { useState } from "react";
import { Link } from "react-router-dom";
import { screenerApi } from "../api/client";
import BackButton from "../components/BackButton";
import InfoTip from "../components/InfoTip";

interface ScreenForm {
  market: "ALL" | "TW" | "US";
  pe_max: string;
  pb_max: string;
  dividend_yield_min: string;
  market_cap_min: string;
  price_above_sma: string;
  rsi_min: string;
  rsi_max: string;
  macd_bullish: boolean;
  limit: number;
}

const DEFAULT_FORM: ScreenForm = {
  market: "ALL",
  pe_max: "",
  pb_max: "",
  dividend_yield_min: "",
  market_cap_min: "",
  price_above_sma: "",
  rsi_min: "",
  rsi_max: "",
  macd_bullish: false,
  limit: 50,
};

const TEMPLATES: { name: string; patch: Partial<ScreenForm> }[] = [
  { name: "高殖利率", patch: { dividend_yield_min: "0.04", pe_max: "20" } },
  { name: "低本益比成長", patch: { pe_max: "15", pb_max: "3", price_above_sma: "60" } },
  { name: "趨勢突破", patch: { price_above_sma: "60", macd_bullish: true, rsi_max: "70" } },
];

export default function Screener() {
  const [form, setForm] = useState<ScreenForm>(DEFAULT_FORM);
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [meta, setMeta] = useState<{ total: number; scanned: number } | null>(null);

  const upd = <K extends keyof ScreenForm>(k: K, v: ScreenForm[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  const run = async () => {
    setLoading(true);
    setMeta(null);
    try {
      const fundamental: any = {};
      if (form.pe_max) fundamental.pe_max = +form.pe_max;
      if (form.pb_max) fundamental.pb_max = +form.pb_max;
      if (form.dividend_yield_min) fundamental.dividend_yield_min = +form.dividend_yield_min;
      if (form.market_cap_min) fundamental.market_cap_min = +form.market_cap_min;

      const technical: any = {};
      if (form.price_above_sma) technical.price_above_sma = +form.price_above_sma;
      if (form.rsi_min) technical.rsi_min = +form.rsi_min;
      if (form.rsi_max) technical.rsi_max = +form.rsi_max;
      if (form.macd_bullish) technical.macd_bullish = true;

      const r = await screenerApi.run({
        market: form.market,
        conditions: { fundamental, technical },
        limit: form.limit,
      });
      setResults(r.results || []);
      setMeta({ total: r.total, scanned: r.scanned });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <BackButton />
      <div className="grid lg:grid-cols-[320px_1fr] gap-6">
      <aside className="bg-gray-900/60 border border-gray-800 rounded-xl p-5 space-y-4 h-fit">
        <h2 className="text-lg font-semibold">篩選條件</h2>

        <div>
          <Label>市場</Label>
          <select
            value={form.market}
            onChange={(e) => upd("market", e.target.value as any)}
            className={inputCls}
          >
            <option value="ALL">全部</option>
            <option value="TW">台股</option>
            <option value="US">美股</option>
          </select>
        </div>

        <div>
          <Label>快速套用</Label>
          <div className="flex flex-wrap gap-1.5">
            {TEMPLATES.map((t) => (
              <button
                key={t.name}
                onClick={() => setForm({ ...DEFAULT_FORM, ...t.patch })}
                className="px-2 py-1 text-xs bg-gray-800 hover:bg-gray-700 rounded"
              >
                {t.name}
              </button>
            ))}
            <button
              onClick={() => setForm(DEFAULT_FORM)}
              className="px-2 py-1 text-xs bg-gray-800 hover:bg-gray-700 rounded"
            >
              重置
            </button>
          </div>
        </div>

        <Section title="基本面">
          <NumField label="PE 最大" tip="PE" value={form.pe_max} onChange={(v) => upd("pe_max", v)} placeholder="例如 20" />
          <NumField label="PB 最大" tip="PB" value={form.pb_max} onChange={(v) => upd("pb_max", v)} placeholder="例如 3" />
          <NumField
            label="殖利率下限（小數）"
            tip="DIVIDEND_YIELD"
            value={form.dividend_yield_min}
            onChange={(v) => upd("dividend_yield_min", v)}
            placeholder="0.04 = 4%"
          />
          <NumField
            label="市值下限"
            tip="MARKET_CAP"
            value={form.market_cap_min}
            onChange={(v) => upd("market_cap_min", v)}
            placeholder="例如 1000000000"
          />
        </Section>

        <Section title="技術面">
          <div>
            <Label>股價在哪條均線之上<InfoTip termKey="SMA" /></Label>
            <select
              value={form.price_above_sma}
              onChange={(e) => upd("price_above_sma", e.target.value)}
              className={inputCls}
            >
              <option value="">不限</option>
              <option value="20">SMA 20</option>
              <option value="60">SMA 60</option>
              <option value="240">SMA 240（年線）</option>
            </select>
          </div>
          <NumField label="RSI 下限" tip="RSI" value={form.rsi_min} onChange={(v) => upd("rsi_min", v)} placeholder="例如 50" />
          <NumField label="RSI 上限" tip="RSI" value={form.rsi_max} onChange={(v) => upd("rsi_max", v)} placeholder="例如 70" />
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.macd_bullish}
              onChange={(e) => upd("macd_bullish", e.target.checked)}
            />
            MACD 多頭排列
            <InfoTip termKey="MACD" />
          </label>
        </Section>

        <button
          disabled={loading}
          onClick={run}
          className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded-lg font-medium"
        >
          {loading ? "篩選中⋯⋯（首次會慢一點）" : "開始篩選"}
        </button>
      </aside>

      <section>
        {meta && (
          <div className="text-sm text-gray-400 mb-3">
            掃描 {meta.scanned} 檔，符合 {meta.total} 檔
          </div>
        )}

        <div className="bg-gray-900/60 border border-gray-800 rounded-xl overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-800/50 text-gray-400">
              <tr>
                <th className="text-left p-3">代號</th>
                <th className="text-left p-3">名稱</th>
                <th className="text-left p-3">市場</th>
                <th className="text-right p-3">PE<InfoTip termKey="PE" align="left" /></th>
                <th className="text-right p-3">PB<InfoTip termKey="PB" align="left" /></th>
                <th className="text-right p-3">殖利率<InfoTip termKey="DIVIDEND_YIELD" align="left" /></th>
                <th className="text-right p-3">RSI14<InfoTip termKey="RSI" align="left" /></th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {results.length === 0 ? (
                <tr>
                  <td colSpan={8} className="p-6 text-center text-gray-500">
                    {loading ? "計算中⋯⋯" : "尚無結果，請設定條件並按下『開始篩選』。"}
                  </td>
                </tr>
              ) : (
                results.map((r) => (
                  <tr key={r.symbol} className="border-t border-gray-800 hover:bg-gray-800/40">
                    <td className="p-3 font-mono">{r.symbol}</td>
                    <td className="p-3">{r.name}</td>
                    <td className="p-3 text-gray-400">{r.market}</td>
                    <td className="p-3 text-right">{fmt(r.pe)}</td>
                    <td className="p-3 text-right">{fmt(r.pb)}</td>
                    <td className="p-3 text-right">
                      {r.dividend_yield != null ? `${(r.dividend_yield * 100).toFixed(2)}%` : "—"}
                    </td>
                    <td className="p-3 text-right">{fmt(r.snapshot?.rsi_14)}</td>
                    <td className="p-3 text-right">
                      <Link
                        to={`/stock/${r.symbol}`}
                        className="text-indigo-400 hover:underline"
                      >
                        分析 →
                      </Link>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
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
function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="space-y-2 pt-2 border-t border-gray-800">
      <div className="text-sm font-semibold text-gray-300">{title}</div>
      {children}
    </div>
  );
}
function NumField({
  label,
  value,
  onChange,
  placeholder,
  tip,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  tip?: string;
}) {
  return (
    <div>
      <Label>
        {label}
        {tip && <InfoTip termKey={tip} />}
      </Label>
      <input
        type="number"
        step="any"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={inputCls}
      />
    </div>
  );
}
function fmt(v: any): string {
  if (v == null || isNaN(v)) return "—";
  return Number(v).toFixed(2);
}
