# 981 Agent Research - Arch_Agent 架構概念

## 專案目標
打造一個 **Agent 自動化更新網頁工具書** 的系統，全部內容放置於 **HackMD**（滿足免費、可公開瀏覽 server 需求）。核心是讓不同使用者能以自己偏好的分類方式動態維護同一份工具書。

## 核心概念條列

1. **HackMD Web Toolbook 系統**
   - 以 HackMD 作為主要呈現介面與儲存後端
   - 所有工具書內容皆為 Markdown 格式
   - 支援公開瀏覽、無需登入即可閱讀
   - Agent 負責自動更新頁面內容與目錄結構

2. **動態目錄架構編輯對話框 (Dynamic Directory Structure Editor Dialog)**
   - 提供聊天式或表單式對話框，讓使用者即時定義/修改工具書的目錄分類架構
   - 使用者可自訂多層級分類維度
   - Agent 會將此分類偏好持久化儲存 (使用 memory tool 或專屬設定檔)

3. **使用者自訂分類體系 (User-defined Classification Systems)**
   - **A 使用者情境**：依照日語能力程度分類
     - 範例結構：N5 基礎 / N4 初級 / N3 中級 / N2 上級 / N1 進階
     - 或使用 CEFR 等級 (A1~C2)
     - 每個分類下介紹對應的學習資訊、單字、文法、資源
   - **B 使用者情境**：依照詞性分類
     - 範例：Noun (名詞) / Verb (動詞) / Adjective (形容詞) / Particle (助詞) / Grammar Pattern
     - 適合語言學習工具書的文法與單字整理
   - **C 使用者情境**：依照用途分類
     - 範例：日常對話 / 商務日語 / 旅遊實用 / 考試準備 / 動漫文化 / 技術文件
     - 適合以「實用情境」為導向的工具書
   - 支援「多維度標籤」：同一內容可同時出現在多個分類下 (cross-reference)

4. **使用者上傳連結自動整理機制 (Link-to-Structured-Content Pipeline)**
   - 使用者只需丟上「網頁連結」或「YouTube 連結」
   - Agent 自動執行以下流程：
     - 抓取內容 (使用 youtube-content skill 取得逐字稿、browser tools 擷取網頁)
     - 解析重點、總結教學內容
     - 根據該使用者的分類偏好，決定最適合的目錄位置
     - 產生格式化的 Markdown 教學檔案 (含標題、重點整理、範例、連結來源)
     - 自動插入對應的 HackMD 頁面 section 或子頁面
   - 支援批次處理多個連結

5. **Agent 核心能力需求**
   - 內容提取與理解 (web scraping, transcript processing)
   - 智慧分類 (根據使用者定義的規則或 few-shot learning 進行分類)
   - Markdown 生成與 HackMD 更新 (可能透過 HackMD API 或 git-based sync)
   - 使用者偏好記憶 (memory tool + per-user classification template)
   - 衝突處理與版本控制 (更新前備份、衝突時通知使用者)

6. **系統優勢**
   - 無需自行架設 server (全靠 HackMD 免費方案)
   - 每個使用者看到的是「個人化視角」的同一份工具書
   - 完全由 Agent 自動維護，降低人工更新成本
   - 可延伸至其他領域工具書 (程式、設計、投資等)

## 待實作項目 (TODO)
- [ ] 設計 Classification Template 格式 (JSON/YAML)
- [ ] 實作「動態目錄編輯對話框」對話流程
- [ ] 整合 youtube-content + browser tools 進行內容提取
- [ ] 開發 HackMD 自動更新機制 (API 或 clipboard-to-HackMD)
- [ ] 建立 per-user memory 機制儲存分類偏好
- [ ] 測試端到端流程：丟連結 → 自動分類 → 更新 HackMD
- [ ] 考慮加入 review 機制 (Agent 先產生 draft 讓使用者確認)

---

