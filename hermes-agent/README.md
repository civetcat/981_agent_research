# Hermes Agent 客製化設定目錄

此目錄 (`hermes-agent/`) 用於存放 Hermes Agent 的使用者特定配置。

## 目前加入的檔案及其作用

### `.hermes/USER.md`
- **主要作用**：定義 persistent user profile 與 communication preferences，注入到 Hermes Agent 的每一次對話。
- **具體內容**：
  - **Core Tech Stack**：OpenBMC、Yocto Project、Linux Kernel Drivers、C/C++、Python、YOLOv8、Transformer、LangChain、Reinforcement Learning。
  - **Language Preference**：預設使用**繁體中文 (zh-TW)** 回覆，所有專有名詞、變數、函式、程式碼片段維持英文。
  - **Response Tone**：直截了當、專業且極度精簡。禁止不必要的客套語。
  - **Code Generation Rules**：
    - C/Kernel 程式碼必須考量嵌入式系統的記憶體限制與硬體安全性。
    - Yocto 相關變更需直接提供 bitbake recipe 或 bbappend 修改方式。
    - 除錯時優先從 register-level、driver 層面分析（Kernel Panic、hardware communication errors）。
- 此檔案是 Hermes Agent 跨 session 的 **User Profile** 核心，優先級高於一般 memory。


## 使用方式
- 將 `hermes-agent/` 作為 Hermes Agent 的 configuration root。
- Agent 啟動時會自動載入 `.hermes/USER.md` 作為 persona 與偏好。
- 所有後續互動將自動遵循「Simplicity First」、「Surgical Changes」以及 BMC 工程師的硬體導向思維。


更新日期：2026-04-27
