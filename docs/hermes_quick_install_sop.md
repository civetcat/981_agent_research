# Hermes Agent Quick Install SOP

此 SOP 適用於 Ubuntu 22.04 或更新版本，不限定 CPU 架構。若需要
ARM64、Grok 或 Playwright 的進階設定，請再參考
`docs/agent/hermes_w_grok_api_key/aarch64_setup.md`。

## 適用範圍

- OS: Ubuntu 22.04 LTS 或更新版本
- Shell: bash 或 zsh
- 權限: 可使用 `sudo` 安裝系統套件

## 1. 更新系統套件

```bash
sudo apt update && sudo apt upgrade -y
```

## 2. 安裝基本依賴

```bash
sudo apt install -y \
  curl \
  git \
  python3-pip \
  python3-venv \
  ffmpeg \
  ripgrep \
  docker.io
```

## 3. 安裝 Hermes Agent

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
```

## 4. 載入 Shell 設定

若使用 bash：

```bash
source ~/.bashrc
```

若使用 zsh：

```bash
source ~/.zshrc
```

## 5. 驗證安裝

```bash
hermes --version
```

若指令可正常輸出版本號，即表示 Hermes Agent 已安裝完成。

## 6. 初始設定

```bash
hermes setup
```

依照互動式流程設定 provider、model 與 execution backend。若不需要
Docker backend，可在 setup 流程中選擇 Local execution backend。
