import { NavLink, Route, Routes } from "react-router-dom";
import StockDetail from "./pages/StockDetail";
import Screener from "./pages/Screener";
import Backtest from "./pages/Backtest";
import Home from "./pages/Home";
import Portfolio from "./pages/Portfolio";
import Recommend from "./pages/Recommend";
import Strategies from "./pages/Strategies";
import Etfs from "./pages/Etfs";
import AiPicks from "./pages/AiPicks";
import AiEtfPicks from "./pages/AiEtfPicks";
import CapitalBadge from "./components/CapitalBadge";

const navClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-2 rounded-md text-sm font-medium transition ${
    isActive
      ? "bg-indigo-600 text-white"
      : "text-gray-300 hover:bg-gray-700 hover:text-white"
  }`;

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-4">
          <div className="text-xl font-bold tracking-tight">
            <span className="text-indigo-400">Stock</span>Sim
          </div>
          <nav className="flex gap-1 flex-1 flex-wrap">
            <NavLink to="/" end className={navClass}>首頁</NavLink>
            <NavLink to="/recommend" className={navClass}>推薦選股</NavLink>
            <NavLink to="/ai-picks" className={navClass}>AI 選股</NavLink>
            <NavLink to="/ai-etfs" className={navClass}>AI 推薦 ETF</NavLink>
            <NavLink to="/etfs" className={navClass}>ETF 排行</NavLink>
            <NavLink to="/strategies" className={navClass}>策略</NavLink>
            <NavLink to="/stock/2330.TW" className={navClass}>個股分析</NavLink>
            <NavLink to="/screener" className={navClass}>選股</NavLink>
            <NavLink to="/backtest" className={navClass}>回測</NavLink>
            <NavLink to="/portfolio" className={navClass}>投資組合</NavLink>
          </nav>
          <CapitalBadge />
        </div>
      </header>

      <main className="flex-1 max-w-7xl mx-auto w-full px-6 py-6">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/recommend" element={<Recommend />} />
          <Route path="/ai-picks" element={<AiPicks />} />
          <Route path="/ai-etfs" element={<AiEtfPicks />} />
          <Route path="/etfs" element={<Etfs />} />
          <Route path="/strategies" element={<Strategies />} />
          <Route path="/stock/:symbol" element={<StockDetail />} />
          <Route path="/screener" element={<Screener />} />
          <Route path="/backtest" element={<Backtest />} />
          <Route path="/portfolio" element={<Portfolio />} />
        </Routes>
      </main>

      <footer className="border-t border-gray-800 py-4 text-center text-xs text-gray-500">
        資料僅供研究參考，不構成任何投資建議。
      </footer>
    </div>
  );
}
