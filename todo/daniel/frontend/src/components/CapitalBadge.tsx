import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { portfolioApi, PortfolioSummary } from "../api/client";

export default function CapitalBadge() {
  const [s, setS] = useState<PortfolioSummary | null>(null);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const r = await portfolioApi.summary();
        if (alive) setS(r);
      } catch {}
    };
    tick();
    const id = setInterval(tick, 30_000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, []);

  if (!s) {
    return (
      <Link
        to="/portfolio"
        className="px-3 py-1.5 rounded-md text-xs text-gray-400 bg-gray-800/60 hover:bg-gray-700"
      >
        總資金 ⋯
      </Link>
    );
  }

  const positive = s.total_return_pct >= 0;

  return (
    <Link
      to="/portfolio"
      className="px-3 py-1.5 rounded-md bg-gray-800/80 hover:bg-gray-700 border border-gray-700 flex items-center gap-2"
      title={`現金 ${fmt$(s.cash)} ・ 持倉 ${fmt$(s.market_value)} ・ 持股 ${s.positions_count} 檔`}
    >
      <div className="text-[10px] text-gray-500 leading-none">總權益</div>
      <div className="text-sm font-semibold leading-none">{fmt$(s.total_equity)}</div>
      <div
        className={`text-xs font-medium leading-none ${
          positive ? "text-bull" : "text-bear"
        }`}
      >
        {positive ? "▲" : "▼"} {Math.abs(s.total_return_pct).toFixed(2)}%
      </div>
    </Link>
  );
}

function fmt$(v: number): string {
  if (v == null || isNaN(v)) return "—";
  if (Math.abs(v) >= 1e6) return `$${(v / 1e6).toFixed(2)}M`;
  if (Math.abs(v) >= 1e3) return `$${(v / 1e3).toFixed(1)}K`;
  return `$${v.toFixed(0)}`;
}
