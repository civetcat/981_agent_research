# Hermes-Choreographer 專案部署與開發紀錄

## 🎯 專案目標
在本地端 RTX 3060 12GB 部署多個開源 LLM，並為 Hermes Agent 構建一套「多大腦動態調度與路由系統」。實現地端/雲端模型的自由切換、自動化專案綁定，以及場景錯配時的智能提示機制。

## ⚙️ 核心架構設計

1. **本地多模型矩陣 (RTX 3060 12GB)：**
   - **DeepSeek-R1-Distill-Qwen (14B/7B)**：專攻深度邏輯推理與代碼 Debug。
   - **Qwen 3 / Llama 4 Scout (小參數版)**：專攻高速度指令執行、本地文件讀寫。
   - 部署工具：Ollama / LM Studio。

2. **雲端大腦後備 (API 接入)：**
   - **Google AI Studio (Gemini 3.1 Pro)**：超長上下文專案重構。
   - **NV NIM (Llama 4 70B+)**：頂級架構設計與極限智力支援。

3. **智能路由與提示管理層 (Router & Guardrail)：**
   - 提供配置界面或配置文件，定義專案/任務與 LLM 的映射關係。
   - 監聽 Hermes 的 Input/Output，當偵測到「用 8B 模型處理 2000 行代碼」或「用雲端模型處理敏感隱私」時，系統自動阻斷並提示建議。

## 🚀 技術待辦事項
- [ ] 在本地使用 Ollama 部署並測試 DeepSeek-R1 蒸餾版與 Qwen 3 模型。
- [ ] 撰寫 Hermes Agent 的動態切換接口（可透過 CLI 指令或 API 自由切換 Backend）。
- [ ] 設計 `model_rules.json` 配置文件，定義專案場景與模型的綁定關係。
- [ ] 開發「場景錯配提示模組」（例如當 Context 超過模型限制時，自動彈出警告並建議切換至 Gemini）。
