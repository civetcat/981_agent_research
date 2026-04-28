# Hermes Agent aarch64 (ARM64) Setup Guide

本指南記錄在 **Supermicro aarch64 伺服器 (`g1smp-build`)** 上部署 Hermes Agent 的完整流程，重點解決 Python 版本衝突、Node.js 升級與 Playwright 瀏覽器依賴問題。

**目標環境**
- **架構**：aarch64 (ARM64)
- **作業系統**：Ubuntu 22.04 LTS (Jammy)
- **帳號**：
  - `build`：具備 sudo 權限（用於系統安裝）
  - `derekko`：主要開發帳號

---

## 1. 基礎系統依賴安裝

以具 sudo 權限的帳號執行：

```bash
sudo apt update
sudo apt install -y ripgrep ffmpeg git build-essential
```

### 升級 Node.js 至 v20 LTS

系統預設 Node.js 版本過舊（v12），需透過 NodeSource 安裝 v20：

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs
```

---

## 2. Python 環境設定（避免破壞系統 Python）

**重要原則**：不要修改系統預設的 `/usr/bin/python3`，以免影響 `apt` 等系統工具。

### 安裝 Python 3.11

```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv
```

### 建立專用虛擬環境（在 `derekko` 帳號下執行）

```bash
python3.11 -m venv ~/hermes_env
source ~/hermes_env/bin/activate
```

---

## 3. 安裝 Hermes Agent

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc
```

---

## 4. Playwright 瀏覽器依賴修復（aarch64 專用）

ARM64 架構需手動安裝依賴：

```bash
# 在 build 帳號（具 sudo）下執行
sudo npx playwright install-deps chromium

# 在 derekko 帳號下執行
npx playwright install chromium
```

---

## 5. 執行 Hermes 初始設定 (`hermes setup`)

執行 `hermes setup` 並依照以下選擇配置：

### 主要設定項目
- **Provider**：`xAI (Grok models — direct API)`
- **Base URL**：`https://api.x.ai/v1`（預設即可）
- **API Key**：輸入您的 `xai-...` 金鑰
- **Model**：`grok-4.20-reasoning`（推薦）
- **Execution Backend**：選擇 **Local**（避免 Docker 衝突）

### 設定流程摘要

1. **Setup Mode**
   - 選擇 `Quick setup — provider, model & messaging (recommended)`

2. **選擇 Provider**
   - 選取 `xAI (Grok models — direct API)`

3. **輸入 API Key**
   - 貼上 xAI API Key 後按 Enter（Base URL 保持預設）

4. **選擇模型**
   - 選取 `grok-4.20-reasoning`

5. **Messaging Platform**
   - 可選擇 `Skip — set up later with 'hermes setup gateway'`

完成後會顯示工具可用性摘要與後續指令提示。

---

## 6. 專案開發規範

建議在 `~/.hermes/instructions/git.md` 建立以下 Git Commit 規範：

```markdown
格式要求: [<scope>] <type> - <title>

欄位: 必須包含 [Recipes], [Analysis], [Validator]（預設為 Derek Ko）。
限制: 每行不超過 80 字元。
```

---

## 7. 常見問題排除

### Q1: ModuleNotFoundError: No module named 'apt_pkg'

**原因**：系統 Python 被切換為 3.11，導致 apt 套件無法找到對應模組。  
**解決方案**：
- 使用 `sudo update-alternatives --config python3` 切回 Python 3.10
- 或在虛擬環境 (`~/hermes_env`) 中執行所有開發工作

### Q2: containerd.io 衝突

**原因**：Docker 官方套件與系統內建套件衝突。  
**解決方案**：在 Hermes 設定時選擇 **Local** 執行後端，即可避開 Docker 相關依賴。

---

## 後續指令參考

開啟 python 虛擬環境
```bash
python3.11 -m venv ~/hermes_env
source ~/hermes_env/bin/activate
```

```bash
hermes                  # 啟動對話
hermes setup            # 重新執行設定精靈
hermes setup model      # 修改模型與 Provider
hermes setup terminal   # 修改終端執行後端
hermes doctor           # 診斷系統狀態
hermes config edit      # 編輯設定檔
```

**設定檔位置**：
- `~/.hermes/config.yaml`（主要設定）
- `~/.hermes/.env`（API 金鑰）

---

**完成！** 現在您可以在 aarch64 環境中穩定運行 Hermes Agent 搭配 Grok 模型。
