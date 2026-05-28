import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  PredictionItem,
  StrategyCatalog,
  StrategyCatalogItem,
  predictionApi,
  strategiesApi,
} from "../api/client";
import BackButton from "../components/BackButton";

let _catalogCache: StrategyCatalog | null = null;

const CAT_COLORS: Record<string, string> = {
  trend: "bg-indigo-900/50 text-indigo-300 border-indigo-700",
  reversion: "bg-amber-900/50 text-amber-300 border-amber-700",
  breakout: "bg-pink-900/50 text-pink-300 border-pink-700",
  passive: "bg-gray-700/60 text-gray-300 border-gray-600",
};

export default function Strategies() {
  const [data, setData] = useState<StrategyCatalog | null>(_catalogCache);
  const [activeCat, setActiveCat] = useState<string>("all");
  const [activeUse, setActiveUse] = useState<"all" | "backtest" | "recommend">("all");

  useEffect(() => {
    if (_catalogCache) return;
    strategiesApi.catalog().then((c) => {
      _catalogCache = c;
      setData(c);
    });
  }, []);

  const filtered = useMemo(() => {
    if (!data) return [];
    return data.items.filter((s) => {
      if (activeCat !== "all" && s.category !== activeCat) return false;
      if (activeUse !== "all" && s.use_in !== activeUse) return false;
      return true;
    });
  }, [data, activeCat, activeUse]);

  if (!data) {
    return <div className="text-gray-400 py-12 text-center">載入中⋯⋯</div>;
  }

  return (
    <div className="space-y-6">
      <BackButton />
      <header>
        <h1 className="text-2xl font-bold">策略指南</h1>
        <p className="text-sm text-gray-400 mt-1">
          所有可用策略的完整使用手冊：訊號邏輯、適用時機、優缺點、調參建議。
          底下「依需求推薦」幫你快速找到適合的起點。
        </p>
      </header>

      {/* 場景推薦 */}
      <section className="bg-gradient-to-br from-indigo-950/40 to-gray-900/60 border border-indigo-900/40 rounded-xl p-5">
        <h2 className="text-lg font-semibold mb-3">依你的需求推薦</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {data.scenarios.map((sc) => {
            const target = data.items.find((s) => s.key === sc.recommend);
            return (
              <ScenarioCard
                key={sc.scenario}
                scenario={sc.scenario}
                recommend={target}
                reason={sc.reason}
              />
            );
          })}
        </div>
      </section>

      {/* 篩選 */}
      <div className="flex flex-wrap gap-2 items-center">
        <span className="text-sm text-gray-400 mr-2">分類：</span>
        <CatButton active={activeCat === "all"} onClick={() => setActiveCat("all")}>
          全部
        </CatButton>
        {data.categories.map((c) => (
          <CatButton
            key={c.key}
            active={activeCat === c.key}
            onClick={() => setActiveCat(c.key)}
          >
            {c.label}
          </CatButton>
        ))}

        <span className="text-sm text-gray-400 mx-2 ml-6">用於：</span>
        <CatButton active={activeUse === "all"} onClick={() => setActiveUse("all")}>
          全部
        </CatButton>
        <CatButton
          active={activeUse === "backtest"}
          onClick={() => setActiveUse("backtest")}
        >
          回測
        </CatButton>
        <CatButton
          active={activeUse === "recommend"}
          onClick={() => setActiveUse("recommend")}
        >
          推薦選股
        </CatButton>
      </div>

      {/* 策略卡片 */}
      <div className="grid lg:grid-cols-2 gap-4">
        {filtered.map((s) => (
          <StrategyCard key={s.key} s={s} catLabel={catLabel(data, s.category)} />
        ))}
      </div>
    </div>
  );
}

function catLabel(data: StrategyCatalog, cat: string): string {
  return data.categories.find((c) => c.key === cat)?.label || cat;
}

function CatButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-1.5 rounded-md text-sm transition ${
        active ? "bg-indigo-600 text-white" : "bg-gray-800 text-gray-300 hover:bg-gray-700"
      }`}
    >
      {children}
    </button>
  );
}

function ScenarioCard({
  scenario,
  recommend,
  reason,
}: {
  scenario: string;
  recommend: StrategyCatalogItem | undefined;
  reason: string;
}) {
  const nav = useNavigate();

  const hasHorizon = (recommend?.horizon_days?.length ?? 0) > 0;
  const isPassive = recommend?.category === "passive";

  const goRecommend = () => {
    if (!recommend) return;
    const h = recommend.horizon_days[0] || 10;
    nav(`/recommend?horizon=${h}`);
  };

  // 被動 / 無訊號的策略：「找推薦」改導 ETF 排行（買入並持有最自然的選擇是大盤 ETF）
  const goEtfs = () => nav(`/etfs`);

  const goBacktest = () => {
    if (!recommend) return;
    const params = new URLSearchParams({ strategy: recommend.key });
    nav(`/backtest?${params.toString()}`);
  };

  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-lg p-4 flex flex-col gap-2">
      <div className="text-sm text-gray-300 font-medium">{scenario}</div>
      <div className="text-xs text-gray-500 leading-relaxed">{reason}</div>
      <div className="mt-1 flex items-center justify-between gap-2 flex-wrap">
        <span className="text-sm font-semibold text-indigo-300">
          → {recommend?.name || recommend?.key || "—"}
        </span>
        <div className="flex gap-1">
          {hasHorizon ? (
            <button
              onClick={goRecommend}
              className="px-2.5 py-1 text-xs bg-indigo-600 hover:bg-indigo-500 rounded"
              title="立刻看現在符合此策略的標的"
            >
              找推薦
            </button>
          ) : isPassive ? (
            <button
              onClick={goEtfs}
              className="px-2.5 py-1 text-xs bg-indigo-600 hover:bg-indigo-500 rounded"
              title="買入並持有最適合大盤 ETF —— 直接看 ETF 排行"
            >
              看 ETF 排行
            </button>
          ) : null}
          <button
            onClick={goBacktest}
            className="px-2.5 py-1 text-xs bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded"
            title="拿這個策略到回測頁驗證歷史績效"
          >
            回測
          </button>
        </div>
      </div>
    </div>
  );
}

function StrategyCard({ s, catLabel }: { s: StrategyCatalogItem; catLabel: string }) {
  const nav = useNavigate();

  const hasHorizon = s.horizon_days.length > 0;
  const isPassive = s.category === "passive";

  const goRecommend = () => {
    const h = s.horizon_days[0] || 10;
    nav(`/recommend?horizon=${h}`);
  };

  const goEtfs = () => nav(`/etfs`);

  const goBacktest = () => {
    const params = new URLSearchParams({ strategy: s.key });
    nav(`/backtest?${params.toString()}`);
  };

  return (
    <article className="bg-gray-900/60 border border-gray-800 rounded-xl p-5 space-y-3">
      <header className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-lg font-bold">{s.name}</h3>
          <div className="flex items-center gap-2 mt-1 flex-wrap">
            <span
              className={`px-2 py-0.5 text-xs rounded border ${
                CAT_COLORS[s.category] || ""
              }`}
            >
              {catLabel}
            </span>
            <span className="px-2 py-0.5 text-xs rounded bg-gray-800 border border-gray-700 text-gray-400">
              {s.use_in === "backtest" ? "回測" : "推薦選股"}
            </span>
            {s.horizon_days.length > 0 && (
              <span className="text-xs text-gray-500">
                持有期 {s.horizon_days.join(" / ")} 天
              </span>
            )}
            {s.indicators.length > 0 && (
              <span className="text-xs text-gray-500">
                指標：{s.indicators.join(", ")}
              </span>
            )}
          </div>
        </div>
        <div className="shrink-0 flex flex-col gap-1.5 items-stretch">
          {hasHorizon ? (
            <button
              onClick={goRecommend}
              className="px-3 py-1.5 text-xs bg-indigo-600 hover:bg-indigo-500 rounded font-medium"
              title="立刻看現在符合此策略的標的"
            >
              找推薦標的 →
            </button>
          ) : isPassive ? (
            <button
              onClick={goEtfs}
              className="px-3 py-1.5 text-xs bg-indigo-600 hover:bg-indigo-500 rounded font-medium"
              title="被動策略最適合大盤 ETF — 看 ETF 排行"
            >
              看 ETF 排行 →
            </button>
          ) : null}
          <button
            onClick={goBacktest}
            className="px-3 py-1.5 text-xs bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded"
            title="拿這個策略到回測頁驗證歷史績效"
          >
            回測驗證
          </button>
        </div>
      </header>

      <Section title="訊號規則" body={s.signal_rule} />
      <Section title="適用時機" body={s.when_to_use} accent />

      <div className="grid sm:grid-cols-2 gap-3">
        <BulletList title="優點" items={s.pros} color="text-bull" />
        <BulletList title="缺點" items={s.cons} color="text-bear" />
      </div>

      {s.best_for.length > 0 && (
        <BulletList title="適合什麼股票" items={s.best_for} />
      )}

      {Object.keys(s.default_params).length > 0 && (
        <div>
          <div className="text-xs text-gray-400 mb-1">預設參數</div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
            {Object.entries(s.default_params).map(([k, v]) => (
              <div
                key={k}
                className="px-2 py-1.5 bg-gray-800/60 rounded text-xs"
                title={s.param_tips[k] || ""}
              >
                <span className="text-gray-500">{k}</span>{" "}
                <span className="font-mono text-gray-200">{v}</span>
                {s.param_tips[k] && (
                  <div className="text-[10px] text-gray-500 mt-0.5">
                    {s.param_tips[k]}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {s.tune_tips && (
        <div className="text-xs text-gray-300 bg-amber-900/15 border-l-2 border-amber-700/60 pl-3 py-2">
          <span className="text-amber-400 font-semibold">調參建議</span>：{s.tune_tips}
        </div>
      )}

      {hasHorizon && <PredictionCalculator strategy={s} />}
    </article>
  );
}

/**
 * 預測計算器：輸入股號 → 抓 /predictions/{symbol} → 顯示對應持有期的預期目標 / 停損 / ATR。
 * 純粹把後端算好的數字攤出來，不做新的計算。
 */
function PredictionCalculator({ strategy }: { strategy: StrategyCatalogItem }) {
  const [symbol, setSymbol] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<PredictionItem | null>(null);
  const [lastClose, setLastClose] = useState<number | undefined>(undefined);
  const [error, setError] = useState<string | null>(null);

  const targetHorizon = strategy.horizon_days[0];

  const compute = async () => {
    const sym = symbol.trim();
    if (!sym) return;
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const r = await predictionApi.forStock(sym);
      setLastClose(r.last_close);
      const match =
        r.predictions.find((p) => p.horizon === targetHorizon) ||
        r.predictions[0] ||
        null;
      if (!match) {
        setError("找不到此股票的回測資料");
      } else {
        setResult(match);
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || e?.message || "計算失敗");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="border-t border-gray-800 pt-3 mt-2">
      <div className="text-xs text-gray-400 mb-2">
        預測計算器
        <span className="text-gray-600 ml-1">
          （輸入股號 → 套用此策略歷史統計 × 當前股價，外推目標/停損）
        </span>
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <input
          value={symbol}
          onChange={(e) => setSymbol(e.target.value.toUpperCase())}
          onKeyDown={(e) => e.key === "Enter" && compute()}
          placeholder="例：2330.TW / AAPL"
          className="px-2 py-1.5 bg-gray-800 border border-gray-700 rounded text-sm w-44
                     focus:outline-none focus:border-indigo-500 font-mono"
        />
        <button
          onClick={compute}
          disabled={busy || !symbol.trim()}
          className="px-3 py-1.5 text-xs bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 rounded"
        >
          {busy ? "計算中⋯" : "計算預期價位"}
        </button>
        {error && <span className="text-xs text-red-400">{error}</span>}
      </div>

      {result && (
        <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-2 text-sm">
          <PredCell label="進場價" value={result.entry?.toFixed(2)} mono />
          <PredCell
            label={`預期目標 (+${result.upside_pct?.toFixed(1)}%)`}
            value={result.target_high?.toFixed(2)}
            color="text-bull"
            mono
          />
          <PredCell
            label={`停損參考 (${result.downside_pct?.toFixed(1)}%)`}
            value={result.target_low?.toFixed(2)}
            color="text-bear"
            mono
          />
          <PredCell
            label={`ATR 區間 (±${result.atr_pct?.toFixed(1)}%)`}
            value={
              result.atr_low != null && result.atr_high != null
                ? `${result.atr_low.toFixed(2)}–${result.atr_high.toFixed(2)}`
                : undefined
            }
            mono
          />
          <PredCell
            label="勝率 / 樣本"
            value={
              result.win_rate != null
                ? `${(result.win_rate * 100).toFixed(0)}% / ${result.n_trades}`
                : undefined
            }
          />
          <PredCell
            label="期望值"
            value={
              result.expected_return_pct != null
                ? `${result.expected_return_pct >= 0 ? "+" : ""}${result.expected_return_pct.toFixed(2)}%`
                : undefined
            }
            color={
              (result.expected_return_pct ?? 0) >= 0 ? "text-bull" : "text-bear"
            }
          />
          <PredCell
            label="目前是否有訊號"
            value={
              result.has_signal_now
                ? `是（${result.signal_date}）`
                : "否（最近 3 日內無）"
            }
            color={result.has_signal_now ? "text-bull" : "text-gray-400"}
          />
          <PredCell
            label="持有期"
            value={`${result.horizon} 天`}
          />
        </div>
      )}

      {result?.warning && (
        <div className="mt-2 text-xs text-amber-400">{result.warning}</div>
      )}
      {result && lastClose != null && (
        <div className="mt-2 text-[11px] text-gray-500">
          數據口徑：以最近收盤 {lastClose.toFixed(2)} 為進場價，套用此策略過去 {result.n_trades} 筆完整交易的勝率/勝幅/敗幅外推。樣本越少越不可信。
        </div>
      )}
    </div>
  );
}

function PredCell({
  label,
  value,
  color = "text-gray-200",
  mono,
}: {
  label: string;
  value: string | number | undefined;
  color?: string;
  mono?: boolean;
}) {
  return (
    <div className="bg-gray-800/40 rounded px-2 py-1.5">
      <div className="text-[10px] text-gray-500">{label}</div>
      <div className={`text-sm ${color} ${mono ? "font-mono" : ""}`}>
        {value ?? "—"}
      </div>
    </div>
  );
}

function Section({
  title,
  body,
  accent,
}: {
  title: string;
  body: string;
  accent?: boolean;
}) {
  return (
    <div>
      <div className="text-xs text-gray-400 mb-1">{title}</div>
      <div
        className={`text-sm leading-relaxed ${
          accent ? "text-indigo-200" : "text-gray-300"
        }`}
      >
        {body}
      </div>
    </div>
  );
}

function BulletList({
  title,
  items,
  color = "text-gray-300",
}: {
  title: string;
  items: string[];
  color?: string;
}) {
  return (
    <div>
      <div className="text-xs text-gray-400 mb-1">{title}</div>
      <ul className={`text-sm space-y-1 ${color}`}>
        {items.map((x, i) => (
          <li key={i} className="flex gap-2">
            <span className="text-gray-600">▸</span>
            <span>{x}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
