import { useState } from "react";
import { useNavigate } from "react-router-dom";

const QUICK_PICKS = [
  { sym: "2330.TW", name: "台積電" },
  { sym: "0050.TW", name: "元大台灣50" },
  { sym: "AAPL", name: "Apple" },
  { sym: "NVDA", name: "NVIDIA" },
  { sym: "TSLA", name: "Tesla" },
  { sym: "QQQ", name: "Invesco QQQ" },
];

export default function Home() {
  const [q, setQ] = useState("");
  const navigate = useNavigate();

  const go = (s: string) => {
    if (!s.trim()) return;
    navigate(`/stock/${s.trim().toUpperCase()}`);
  };

  return (
    <div className="space-y-10">
      <section className="text-center py-16">
        <h1 className="text-4xl font-bold mb-3">
          股票模擬與回測平台
        </h1>
        <p className="text-gray-400 mb-8">台股 + 美股 ・ 選股 ・ 技術分析 ・ 策略回測</p>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            go(q);
          }}
          className="max-w-xl mx-auto flex gap-2"
        >
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="輸入股票代號（例如 2330.TW、AAPL）"
            className="flex-1 px-4 py-3 bg-gray-800 border border-gray-700 rounded-lg
                       focus:outline-none focus:border-indigo-500"
          />
          <button
            type="submit"
            className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 rounded-lg font-medium"
          >
            分析
          </button>
        </form>

        <div className="mt-6 flex flex-wrap justify-center gap-2">
          {QUICK_PICKS.map((p) => (
            <button
              key={p.sym}
              onClick={() => go(p.sym)}
              className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded-md text-sm"
            >
              {p.sym} <span className="text-gray-500">{p.name}</span>
            </button>
          ))}
        </div>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-3 text-gray-200">所有功能</h2>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.map((f) => (
            <FeatureCard key={f.to} {...f} />
          ))}
        </div>
      </section>
    </div>
  );
}

interface Feature {
  icon: string;
  title: string;
  desc: string;
  to: string;
}

const FEATURES: Feature[] = [
  {
    icon: "📈",
    title: "個股深入分析",
    desc: "K 線、技術指標、基本面、籌碼、AI 評等一次看",
    to: "/stock/2330.TW",
  },
  {
    icon: "🔎",
    title: "條件選股",
    desc: "基本面 + 技術面條件組合篩出標的",
    to: "/screener",
  },
  {
    icon: "🧪",
    title: "策略回測",
    desc: "內建策略一鍵跑歷史績效與權益曲線",
    to: "/backtest",
  },
  {
    icon: "📚",
    title: "策略目錄",
    desc: "所有策略的訊號邏輯、適用情境與調參建議",
    to: "/strategies",
  },
  {
    icon: "⭐",
    title: "推薦選股",
    desc: "依持有期匹配策略，掃出最近的進場訊號",
    to: "/recommend",
  },
  {
    icon: "🤖",
    title: "AI 選股",
    desc: "Grok-4 推演當前題材與直接受惠候選股",
    to: "/ai-picks",
  },
  {
    icon: "🧠",
    title: "AI 推薦 ETF",
    desc: "AI 推演當前最值得佈局的 ETF 主題",
    to: "/ai-etfs",
  },
  {
    icon: "🏆",
    title: "ETF 排行",
    desc: "台美股主流 ETF：規模、費用率、殖利率、多期報酬",
    to: "/etfs",
  },
  {
    icon: "💼",
    title: "模擬投資組合",
    desc: "現金、持倉、損益、資產配置一目了然",
    to: "/portfolio",
  },
];

function FeatureCard({ icon, title, desc, to }: Feature) {
  const navigate = useNavigate();
  return (
    <button
      onClick={() => navigate(to)}
      className="text-left p-5 bg-gray-800/60 hover:bg-gray-800 border border-gray-700
                 hover:border-indigo-700 rounded-xl transition group"
    >
      <div className="flex items-start gap-3">
        <div className="text-2xl shrink-0">{icon}</div>
        <div className="min-w-0">
          <h3 className="text-lg font-semibold mb-1 group-hover:text-indigo-300 transition">
            {title}
          </h3>
          <p className="text-sm text-gray-400 leading-relaxed">{desc}</p>
        </div>
      </div>
    </button>
  );
}
