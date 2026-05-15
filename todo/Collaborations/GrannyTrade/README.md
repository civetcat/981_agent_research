# GrannyTrade 👵📈 (阿婆量化交易工具包)

## 🌟 專案願景
打造一個「連隔壁阿婆都能上手」的自動化交易工具。透過封裝複雜的策略邏輯，讓使用者只需簡單部署，即可在自己的電腦（或雲端）運行比特幣自動化交易，並透過手機遠端監控。

## 🎯 核心目標
1. **極簡部署 (One-Click Setup)**：抓下工具包，執行一個指令即可啟動，無需手動配置複雜環境。[cite: 3]
2. **跨平台控制 (Mobile Console)**：透過 Telegram/Discord Bot 實現手機、平板遠端操作與即時損益通知。[cite: 3]
3. **無痛小額實驗 (Low-Risk Lab)**：專為小額策略實驗設計，支持 24/7 不間斷運作，適合作為量化入門。[cite: 3, 4]
4. **Agent 協作友好 (Agent Ready)**：結構化代碼設計，方便 LLM Agent (如 Claude, Gemini, GPT) 直接讀取並執行交易任務。[cite: 3]

## 🚀 技術架構
- **核心語言**：Python 3.10+
- **交易引擎**：CCXT Library (對接全球主流交易所)[cite: 3]
- **部署方式**：Docker 鏡像 / Shell 一鍵腳本[cite: 3]
- **控制中心**：Telegram Bot API (手機即控制台)[cite: 3]
- **資料庫**：SQLite (輕量化、免安裝)

## 🤝 協作說明
本專案目前在 GitHub 上與朋友共同開發。
- `/strategies`: 存放交易策略與邏輯模板。
- `/core`: 系統核心執行模組。
- `/console`: 遠端控制介面代碼。
