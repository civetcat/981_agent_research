import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { stocksApi } from "../api/client";

interface SearchHit {
  symbol: string;
  name?: string;
  market?: string;
}

function normalizeSymbol(raw: string): string {
  const s = raw.trim().toUpperCase();
  if (!s) return s;
  // 純 4 位數字 → 自動補 .TW（台股）
  if (/^\d{4}$/.test(s)) return `${s}.TW`;
  // 4 位數字 + 一個英文（例如 00679B）→ 視為台股 ETF
  if (/^\d{4,6}[A-Z]?$/.test(s) && !s.includes(".")) return `${s}.TW`;
  return s;
}

export default function SymbolSearchBar({
  initial = "",
  className = "",
}: {
  initial?: string;
  className?: string;
}) {
  const navigate = useNavigate();
  const [q, setQ] = useState(initial);
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [open, setOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const wrapRef = useRef<HTMLDivElement>(null);

  // autocomplete：debounce 250ms
  useEffect(() => {
    const term = q.trim();
    if (!term || term.length < 1) {
      setHits([]);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const r = await stocksApi.search(term);
        const list: SearchHit[] = Array.isArray(r) ? r : r?.results || r?.data || [];
        setHits(list.slice(0, 8));
      } catch {
        setHits([]);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  // 點擊外部關閉
  useEffect(() => {
    const onDoc = (e: MouseEvent) => {
      if (!wrapRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const go = (sym: string) => {
    const target = normalizeSymbol(sym);
    if (!target) return;
    setOpen(false);
    setActiveIdx(-1);
    navigate(`/stock/${encodeURIComponent(target)}`);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      if (activeIdx >= 0 && hits[activeIdx]) {
        go(hits[activeIdx].symbol);
      } else {
        go(q);
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setOpen(true);
      setActiveIdx((i) => Math.min(hits.length - 1, i + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIdx((i) => Math.max(-1, i - 1));
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div
      ref={wrapRef}
      className={`relative flex gap-2 items-center ${className}`}
    >
      <div className="relative flex-1 min-w-[220px]">
        <input
          value={q}
          onChange={(e) => {
            setQ(e.target.value);
            setOpen(true);
            setActiveIdx(-1);
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={onKeyDown}
          placeholder="輸入股票代號或名稱：2330 / NVDA / 台積電..."
          className="w-full bg-gray-950/80 border border-gray-700 rounded-md px-3 py-2 text-sm focus:outline-none focus:border-indigo-500"
        />
        {open && hits.length > 0 && (
          <ul className="absolute z-20 mt-1 w-full bg-gray-900 border border-gray-700 rounded-md shadow-lg max-h-72 overflow-auto">
            {hits.map((h, i) => (
              <li
                key={`${h.symbol}-${i}`}
                onMouseDown={(e) => {
                  e.preventDefault();
                  go(h.symbol);
                }}
                onMouseEnter={() => setActiveIdx(i)}
                className={`px-3 py-2 text-sm cursor-pointer flex justify-between gap-3 ${
                  activeIdx === i ? "bg-indigo-700/40" : "hover:bg-gray-800"
                }`}
              >
                <span className="font-mono text-indigo-300">{h.symbol}</span>
                <span className="text-gray-300 truncate">{h.name || ""}</span>
                {h.market && (
                  <span className="text-xs text-gray-500">{h.market}</span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
      <button
        onClick={() => go(q)}
        className="px-4 py-2 text-sm bg-indigo-600 hover:bg-indigo-500 rounded-md font-medium"
      >
        前往
      </button>
    </div>
  );
}
