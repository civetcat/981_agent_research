import { useEffect, useState } from "react";
import { VerdictEntryMode, VerdictResponse, verdictApi } from "../api/client";

/**
 * 推薦評分儀表板：把策略期望、動能、籌碼、MFI、量能五個分項加權成一個總分，
 * 並呈現「強烈推薦買入 / 推薦買入 / 持平 / 不建議 / 強烈避開」。
 *
 * 設計目標：金融儀表板的乾淨感 — 平滑單一弧線、漂亮指針、大字級分數。
 */
// Session 級快取：verdict 計算後端要跑 5 個回測，重訪同股票直接秒顯示
const _verdictCache: Record<string, VerdictResponse> = {};

const ENTRY_MODE_OPTIONS: { value: VerdictEntryMode; label: string; description: string }[] = [
  { value: "conservative", label: "保守", description: "等較深回檔，避免追高" },
  { value: "balanced", label: "平衡", description: "ATR 回檔區，預設值" },
  { value: "aggressive", label: "積極", description: "分數偏多時允許小幅追價" },
  { value: "sma_pullback", label: "均線回測", description: "靠近 SMA20 / SMA60" },
];

export default function VerdictGauge({ symbol }: { symbol: string }) {
  const [entryMode, setEntryMode] = useState<VerdictEntryMode>("balanced");
  const [data, setData] = useState<VerdictResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    const cacheKey = `${symbol}|${entryMode}`;
    if (_verdictCache[cacheKey]) {
      setData(_verdictCache[cacheKey]);
      setLoading(false);
      return;
    }
    setLoading(true);
    setData(null);
    verdictApi
      .forStock(symbol, entryMode)
      .then((r) => {
        _verdictCache[cacheKey] = r;
        setData(r);
      })
      .catch((e) => setError(e?.message || "評分計算失敗"))
      .finally(() => setLoading(false));
  }, [symbol, entryMode]);

  if (loading) {
    return (
      <section className="bg-gradient-to-br from-gray-900/80 to-gray-900/40 border border-gray-800 rounded-2xl p-6">
        <div className="text-gray-500 text-sm flex items-center gap-2">
          <Spinner /> 評分中⋯⋯
        </div>
      </section>
    );
  }
  if (error) {
    return (
      <section className="bg-gradient-to-br from-gray-900/80 to-gray-900/40 border border-red-900/50 rounded-2xl p-6">
        <div className="text-red-400 text-sm">{error}</div>
      </section>
    );
  }
  if (!data) return null;

  return (
    <section className="bg-gradient-to-br from-gray-900/80 via-gray-900/60 to-gray-900/40 border border-gray-800 rounded-2xl p-6 shadow-lg">
      <div className="flex flex-wrap items-end justify-between gap-3 mb-5">
        <div className="flex items-baseline gap-3">
          <h3 className="font-semibold text-lg text-gray-100">推薦評分</h3>
          <span className="text-xs text-gray-400">
            5 個訊號加權 · 純規則 · 無 AI
          </span>
        </div>
        <label className="flex items-center gap-2 text-xs text-gray-400">
          進場策略
          <select
            value={entryMode}
            onChange={(e) => setEntryMode(e.target.value as VerdictEntryMode)}
            className="bg-gray-950/80 border border-gray-700 rounded-md px-2 py-1.5 text-sm text-gray-100 focus:outline-none focus:border-indigo-500"
          >
            {ENTRY_MODE_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="grid lg:grid-cols-[320px_1fr] gap-8 items-center">
        <Gauge
          score={data.score}
          levelLabel={data.level_label}
          color={data.color}
        />

        <div className="space-y-2.5">
          {data.components.map((c) => (
            <ComponentBar key={c.key} c={c} />
          ))}
        </div>
      </div>

      {data.suggestion && (
        <SuggestionPanel
          suggestion={data.suggestion}
          levelColor={data.color}
          modeDescription={
            ENTRY_MODE_OPTIONS.find((opt) => opt.value === entryMode)?.description || ""
          }
        />
      )}

      <Disclaimer score={data.score} weightUsed={data.weight_used} />
    </section>
  );
}

function SuggestionPanel({
  suggestion: s,
  levelColor,
  modeDescription,
}: {
  suggestion: NonNullable<VerdictResponse["suggestion"]>;
  levelColor: string;
  modeDescription: string;
}) {
  return (
    <div className="mt-6 grid md:grid-cols-[auto_1fr] gap-4 items-stretch">
      <div
        className="px-4 py-3 rounded-xl flex flex-col justify-center min-w-[200px]"
        style={{
          background: `linear-gradient(135deg, ${levelColor}22, ${levelColor}08)`,
          border: `1px solid ${levelColor}55`,
        }}
      >
        <div className="text-xs text-gray-300 tracking-wider uppercase">
          建議動作
        </div>
        <div
          className="text-lg font-bold mt-1"
          style={{ color: levelColor }}
        >
          {s.action}
        </div>
        <div className="text-xs text-gray-300 mt-1.5 leading-relaxed">
          {s.entry_mode_label || "平衡：ATR 回檔區"}
          {modeDescription && <span className="block text-gray-400">{modeDescription}</span>}
        </div>
        {s.hint && (
          <div className="text-xs text-gray-300 mt-1.5 leading-relaxed">
            {s.hint}
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <PriceCell
          label="目前價"
          value={s.entry_price}
          color="text-gray-200"
        />
        <PriceCell
          label="建議買進區"
          value={`${s.buy_low} ~ ${s.buy_high}`}
          color="text-sky-300"
          mono={false}
        />
        <PriceCell
          label="目標價"
          value={s.target_price}
          sub={`+${s.upside_pct.toFixed(1)}%`}
          color="text-emerald-300"
          subColor="text-emerald-400"
        />
        <PriceCell
          label="停損價"
          value={s.stop_loss}
          sub={`${s.downside_pct.toFixed(1)}%`}
          color="text-red-300"
          subColor="text-red-400"
        />
      </div>
    </div>
  );
}

function PriceCell({
  label,
  value,
  sub,
  color = "text-gray-200",
  subColor = "text-gray-500",
  mono = true,
}: {
  label: string;
  value: number | string;
  sub?: string;
  color?: string;
  subColor?: string;
  mono?: boolean;
}) {
  return (
    <div className="bg-gray-900/60 border border-gray-800 rounded-lg px-3 py-2.5">
      <div className="text-xs text-gray-400 tracking-wider uppercase font-medium">
        {label}
      </div>
      <div
        className={`${color} ${
          mono ? "font-mono text-lg" : "text-base"
        } font-bold mt-1 truncate`}
      >
        {value}
      </div>
      {sub && (
        <div className={`text-xs mt-1 font-mono font-semibold ${subColor}`}>{sub}</div>
      )}
    </div>
  );
}

function Spinner() {
  return (
    <span className="inline-block w-3 h-3 border-2 border-gray-500 border-t-transparent rounded-full animate-spin" />
  );
}

function Gauge({
  score,
  levelLabel,
  color,
}: {
  score: number;
  levelLabel: string;
  color: string;
}) {
  // 270° 仿汽車儀表板：底部留 90° 缺口，弧線從左下繞到右下。
  // 角度系統（SVG 慣例：0° 在三點鐘，順時針增加）：
  //   開始 = 135°（左下）→ 結束 = 405° 即 45°（右下）
  //   score = -100 → 開始；score = +100 → 結束
  const cx = 160;
  const cy = 160;
  const r = 120;
  const stroke = 22;

  const ANGLE_START = 135;
  const ANGLE_END = 405; // = 45° + 360°
  const SWEEP = ANGLE_END - ANGLE_START; // 270°

  const scoreToAngle = (s: number) =>
    ANGLE_START + ((s + 100) / 200) * SWEEP;

  // 五個彩色弧段（紅 / 橘 / 灰 / 綠 / 翠綠），與 verdict 顏色一致
  const sectors = [
    { from: -100, to: -60, color: "#dc2626" },
    { from: -60, to: -20, color: "#ea580c" },
    { from: -20, to: 20, color: "#94a3b8" },
    { from: 20, to: 60, color: "#22c55e" },
    { from: 60, to: 100, color: "#10b981" },
  ];

  const needleAngle = scoreToAngle(score);
  const needleLen = r - 8;
  const needleEnd = polarXY(cx, cy, needleLen, needleAngle);

  // 主要刻度（每 25 一個）
  const majorTicks = [-100, -75, -50, -25, 0, 25, 50, 75, 100];
  // 次要刻度（每 12.5 一個，但只畫不在主要刻度的位置）
  const minorTicks: number[] = [];
  for (let v = -100; v <= 100; v += 12.5) {
    if (!majorTicks.includes(v)) minorTicks.push(v);
  }

  return (
    <div className="flex flex-col items-center select-none">
      <svg width="340" height="290" viewBox="-10 -5 340 290">
        <defs>
          <linearGradient id="needleGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#f3f4f6" />
            <stop offset="60%" stopColor="#9ca3af" />
            <stop offset="100%" stopColor="#4b5563" />
          </linearGradient>
          <radialGradient id="hubGrad" cx="50%" cy="40%" r="50%">
            <stop offset="0%" stopColor="#374151" />
            <stop offset="60%" stopColor="#1f2937" />
            <stop offset="100%" stopColor="#0b0f17" />
          </radialGradient>
          <filter id="needleShadow" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="2" stdDeviation="2.5" floodOpacity="0.5" />
          </filter>
          <filter id="glowSoft" x="-30%" y="-30%" width="160%" height="160%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* 外層深色軌道 */}
        <path
          d={describeArc(cx, cy, r, ANGLE_START, ANGLE_END)}
          fill="none"
          stroke="#111827"
          strokeWidth={stroke + 6}
          strokeLinecap="round"
        />
        {/* 內層灰軌 */}
        <path
          d={describeArc(cx, cy, r, ANGLE_START, ANGLE_END)}
          fill="none"
          stroke="#1f2937"
          strokeWidth={stroke}
          strokeLinecap="round"
        />

        {/* 五個彩色弧段，間距留 0.6° 形成分段感 */}
        {sectors.map((s, i) => {
          const a1 = scoreToAngle(s.from) + (s.from === -100 ? 0 : 0.6);
          const a2 = scoreToAngle(s.to) - (s.to === 100 ? 0 : 0.6);
          return (
            <path
              key={i}
              d={describeArc(cx, cy, r, a1, a2)}
              fill="none"
              stroke={s.color}
              strokeWidth={stroke}
              strokeLinecap="butt"
              opacity="0.9"
            />
          );
        })}

        {/* 次要刻度（短白線） */}
        {minorTicks.map((v) => {
          const a = scoreToAngle(v);
          const p1 = polarXY(cx, cy, r - stroke / 2 - 3, a);
          const p2 = polarXY(cx, cy, r - stroke / 2 - 8, a);
          return (
            <line
              key={`mn-${v}`}
              x1={p1.x}
              y1={p1.y}
              x2={p2.x}
              y2={p2.y}
              stroke="#4b5563"
              strokeWidth="1"
            />
          );
        })}

        {/* 主要刻度（長白線 + 數字） */}
        {majorTicks.map((v) => {
          const a = scoreToAngle(v);
          const p1 = polarXY(cx, cy, r - stroke / 2 - 2, a);
          const p2 = polarXY(cx, cy, r - stroke / 2 - 12, a);
          const lbl = polarXY(cx, cy, r + 22, a);
          const isZero = v === 0;
          return (
            <g key={`mj-${v}`}>
              <line
                x1={p1.x}
                y1={p1.y}
                x2={p2.x}
                y2={p2.y}
                stroke={isZero ? "#e5e7eb" : "#9ca3af"}
                strokeWidth={isZero ? "2" : "1.5"}
              />
              <text
                x={lbl.x}
                y={lbl.y}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize="13"
                fontFamily="monospace"
                fill={isZero ? "#e5e7eb" : "#9ca3af"}
                fontWeight={isZero ? "bold" : "500"}
              >
                {v > 0 ? `+${v}` : v}
              </text>
            </g>
          );
        })}

        {/* 指針（金屬漸層 + 投影） */}
        <g filter="url(#needleShadow)">
          <line
            x1={cx}
            y1={cy}
            x2={needleEnd.x}
            y2={needleEnd.y}
            stroke="url(#needleGrad)"
            strokeWidth="5"
            strokeLinecap="round"
          />
          {/* 指針尖端 + 微光 */}
          <circle
            cx={needleEnd.x}
            cy={needleEnd.y}
            r="6"
            fill={color}
            filter="url(#glowSoft)"
            opacity="0.9"
          />
          <circle cx={needleEnd.x} cy={needleEnd.y} r="3.5" fill={color} />
        </g>

        {/* 中心轉軸（凸起金屬感） */}
        <circle cx={cx} cy={cy} r="18" fill="url(#hubGrad)" stroke="#4b5563" strokeWidth="1.5" />
        <circle cx={cx} cy={cy} r="6" fill={color} opacity="0.4" />
        <circle cx={cx} cy={cy} r="3" fill={color} />

        {/* 中心下方放分數，像汽車轉速錶中央的 RPM 數字 */}
        <text
          x={cx}
          y={cy + 60}
          textAnchor="middle"
          fontSize="36"
          fontFamily="monospace"
          fontWeight="bold"
          fill={color}
          filter="url(#glowSoft)"
        >
          {score >= 0 ? "+" : ""}
          {score.toFixed(1)}
        </text>
        <text
          x={cx}
          y={cy + 82}
          textAnchor="middle"
          fontSize="11"
          fontFamily="monospace"
          fill="#9ca3af"
          letterSpacing="3"
          fontWeight="600"
        >
          SCORE
        </text>
      </svg>

      <div
        className="mt-1 text-xl font-bold tracking-wide"
        style={{ color }}
      >
        {levelLabel}
      </div>
    </div>
  );
}

function describeArc(
  cx: number,
  cy: number,
  r: number,
  startDeg: number,
  endDeg: number
): string {
  // 標準 SVG arc：0° = 三點鐘，順時針增加。
  const start = polarXY(cx, cy, r, startDeg);
  const end = polarXY(cx, cy, r, endDeg);
  const sweep = endDeg - startDeg;
  const largeArc = Math.abs(sweep) > 180 ? 1 : 0;
  const sweepFlag = sweep > 0 ? 1 : 0;
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} ${sweepFlag} ${end.x} ${end.y}`;
}

function polarXY(cx: number, cy: number, r: number, deg: number) {
  const rad = (deg * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

interface CompProps {
  c: {
    label: string;
    raw_score: number;
    weight: number;
    weighted: number;
    detail: any;
  };
}

function ComponentBar({ c }: CompProps) {
  const available = c.detail?.available !== false;
  const pct = Math.max(-100, Math.min(100, c.raw_score));
  const positive = pct >= 0;
  const barWidth = (Math.abs(pct) / 100) * 50;

  return (
    <div className="group">
      <div className="flex items-center justify-between text-sm mb-1.5">
        <div className="flex items-baseline gap-2">
          <span className="text-gray-100 font-semibold">{c.label}</span>
          <span className="text-xs text-gray-400">
            權重 {(c.weight * 100).toFixed(0)}%
          </span>
        </div>
        {available ? (
          <div className="flex items-baseline gap-2 font-mono">
            <span
              className={`text-sm ${
                positive ? "text-emerald-400" : pct === 0 ? "text-gray-500" : "text-red-400"
              }`}
            >
              {pct >= 0 ? "+" : ""}
              {pct.toFixed(0)}
            </span>
            <span className="text-gray-600">→</span>
            <span
              className={`font-bold text-sm ${
                c.weighted >= 0 ? "text-emerald-400" : c.weighted === 0 ? "text-gray-500" : "text-red-400"
              }`}
            >
              {c.weighted >= 0 ? "+" : ""}
              {c.weighted.toFixed(1)}
            </span>
          </div>
        ) : (
          <span className="text-xs text-gray-600">資料不足</span>
        )}
      </div>

      {/* 雙向 bar：中線在 50%，往左/右展開 */}
      <div className="relative h-2 bg-gray-800/80 rounded-full overflow-hidden">
        <div className="absolute inset-y-0 left-1/2 w-px bg-gray-700/80" />
        {available && pct !== 0 && (
          <div
            className="absolute inset-y-0 rounded-full transition-all"
            style={{
              left: positive ? "50%" : `${50 - barWidth}%`,
              width: `${barWidth}%`,
              background: positive
                ? "linear-gradient(90deg, #34d399, #10b981)"
                : "linear-gradient(90deg, #ef4444, #f87171)",
            }}
          />
        )}
      </div>

      {available && <DetailLine detail={c.detail} />}
    </div>
  );
}

function DetailLine({ detail }: { detail: any }) {
  const parts: string[] = [];
  if (detail.median_expected_pct != null) {
    parts.push(
      `期望中位數 ${detail.median_expected_pct >= 0 ? "+" : ""}${detail.median_expected_pct}%`
    );
    if (detail.has_signal_now) parts.push("目前有訊號");
  }
  if (detail.return_1m_pct != null)
    parts.push(`1M ${detail.return_1m_pct >= 0 ? "+" : ""}${detail.return_1m_pct}%`);
  if (detail.return_3m_pct != null)
    parts.push(`3M ${detail.return_3m_pct >= 0 ? "+" : ""}${detail.return_3m_pct}%`);
  if (detail.ratio_5d != null)
    parts.push(`5 日法人 / 平均量 = ${detail.ratio_5d}`);
  if (detail.insider_buys != null)
    parts.push(`Insider 買 ${detail.insider_buys} / 賣 ${detail.insider_sells}`);
  if (detail.mfi != null) parts.push(`MFI ${detail.mfi}`);
  if (detail.vol_z != null)
    parts.push(`量能 z=${detail.vol_z} ${detail.direction_up ? "↑" : "↓"}`);

  if (!parts.length) return null;
  return (
    <div className="text-xs text-gray-400 mt-1.5 ml-0.5">
      {parts.join(" ・ ")}
    </div>
  );
}

function Disclaimer({
  score,
  weightUsed,
}: {
  score: number;
  weightUsed: number;
}) {
  if (weightUsed >= 0.95) return null;
  const missing = ((1 - weightUsed) * 100).toFixed(0);
  return (
    <div className="mt-4 px-3 py-1.5 bg-amber-900/20 border border-amber-800/40 rounded-md text-[11px] text-amber-300/90">
      ⚠ 有 {missing}% 權重的資料缺漏（已用實際資料正規化），分數可信度略降。
      {score === 0 && " 全部資料缺漏，分數不可信。"}
    </div>
  );
}
