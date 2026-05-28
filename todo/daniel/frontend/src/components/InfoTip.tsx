import { useState } from "react";
import { GLOSSARY, GlossaryEntry } from "../lib/glossary";

interface Props {
  /** glossary 對應 key；提供後會自動帶入 name / explain / impact */
  termKey?: keyof typeof GLOSSARY | string;
  /** 直接覆寫文字 (不查 glossary 時用) */
  name?: string;
  explain?: string;
  impact?: string;
  /** tooltip 對齊方向；預設 right (向右展開)，靠近邊界可設 left */
  align?: "left" | "right" | "center";
  className?: string;
}

export default function InfoTip({
  termKey,
  name,
  explain,
  impact,
  align = "right",
  className = "",
}: Props) {
  const [open, setOpen] = useState(false);
  const entry: Partial<GlossaryEntry> =
    (termKey && (GLOSSARY as Record<string, GlossaryEntry>)[termKey as string]) || {};
  const title = name ?? entry.name ?? String(termKey ?? "");
  const exp = explain ?? entry.explain;
  const imp = impact ?? entry.impact;

  if (!exp && !imp) {
    // 沒有資料就不渲染，避免顯示空 tooltip
    return null;
  }

  const alignCls =
    align === "left"
      ? "right-0"
      : align === "center"
      ? "left-1/2 -translate-x-1/2"
      : "left-0";

  return (
    <span className={`relative inline-flex align-middle ml-1 ${className}`}>
      <button
        type="button"
        tabIndex={0}
        aria-label={`${title} 說明`}
        onMouseEnter={() => setOpen(true)}
        onMouseLeave={() => setOpen(false)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        className="inline-flex items-center justify-center w-4 h-4 rounded-full
                   bg-gray-700 hover:bg-indigo-600 text-gray-300 hover:text-white
                   text-[10px] font-bold leading-none cursor-help
                   focus:outline-none focus:ring-2 focus:ring-indigo-500"
      >
        i
      </button>
      {open && (
        <span
          role="tooltip"
          className={`absolute z-50 top-5 ${alignCls} w-64 max-w-[80vw] p-3
                      bg-gray-950 border border-gray-700 rounded-lg shadow-xl
                      text-xs text-gray-200 leading-relaxed text-left normal-case
                      pointer-events-none`}
        >
          <div className="font-semibold text-indigo-300 mb-1">{title}</div>
          {exp && <div className="text-gray-300">{exp}</div>}
          {imp && (
            <div className="mt-1.5 pt-1.5 border-t border-gray-800 text-gray-400">
              <span className="text-gray-500">影響：</span>
              {imp}
            </div>
          )}
        </span>
      )}
    </span>
  );
}
