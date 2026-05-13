# Bernie 的 981 Agent Research TODO

此資料夾用來存放 Bernie 個人針對 **Agent 架構研究** 的想法、藍圖與實作筆記。

## 專案背景
981_agent_research 是探索如何讓 AI Agent 自主維護知識庫、工具書與動態內容的研發專案。核心目標是減少人工維護成本，並讓不同使用者能以「自己習慣的分類方式」來使用同一份工具書。

## 目前檔案列表

- **Arch_Agent.md**  
  核心架構文件。詳細條列以下概念：
  - Agent 自動化更新 HackMD 網頁工具書系統
  - 動態目錄架構編輯對話框 (Dynamic Directory Structure Editor Dialog)
  - 使用者自訂分類體系（支援 A：日語能力程度分類、B：詞性分類、C：用途分類等多種維度）
  - 使用者丟上網頁或 YouTube 連結 → Agent 自動解析、總結、分類並放入正確架構的完整流程
  - HackMD 作為免費可公開瀏覽的後端方案
  - Agent 所需核心能力與 TODO 清單

- **README.md** (本檔案)  
  本目錄總覽與導覽文件。

## 系統願景 (Vision)

打造一個 **「丟連結就自動更新」的智慧工具書平台**：

1. 使用者先透過對話框告訴 Agent 自己想要的分類方式（例如依照 JLPT 等級、詞性、或實用情境）。
2. 之後只要把網頁連結或 YouTube 影片連結丟給 Agent。
3. Agent 會自動：
   - 抓取內容（transcript、網頁文字）
   - 總結重點教學內容
   - 根據該使用者的分類偏好決定放置位置
   - 生成結構化 Markdown
   - 更新對應的 HackMD 頁面

無需自行架 server，全部使用 HackMD 免費方案即可公開分享與瀏覽。

## 下一步行動項目

參見 Arch_Agent.md 內的 TODO 清單，主要優先事項包含：
- 定義 Classification Template 格式
- 實作動態目錄編輯對話流程
- 開發 HackMD 自動更新機制
- 整合 youtube-content 與 browser tools 進行內容提取
- 建立 per-user 偏好記憶系統

---


