# AI Agent CLI Docker 修改檔案清單

此文件列出為了在 ARM64 Linux 系統上建立可同時運行 Hermes-Agent CLI 與 Cursor CLI 的 Docker 環境，對 Hermes-Agent source tree 所做的檔案修改。

## 修改檔案總覽

| Hermes-Agent 原始路徑 | 本資料夾副本路徑 | 修改目的 |
| --- | --- | --- |
| `.dockerignore` | `hermes-agent/.dockerignore` | 排除 host virtualenv 與 runtime state，避免把本機環境打包進 Docker image。 |
| `Dockerfile` | `hermes-agent/Dockerfile` | 安裝 ARM64 browser runtime、Docker tooling、Cursor CLI，並設定穩定 runtime PATH。 |
| `docker-compose.yml` | `hermes-agent/docker-compose.yml` | 建立可常駐的雙 CLI container，掛載資料、Docker socket 與本機工作目錄。 |
| `docker/entrypoint.sh` | `hermes-agent/docker/entrypoint.sh` | 修正 HOME / Cursor config 位置、Docker socket group 權限、資料目錄初始化。 |

## `.dockerignore`

新增排除項目：

```text
venv
**/venv
```

原因：host 端 Hermes-Agent source tree 內的 `venv` 不應進入 Docker build context。若 host virtualenv 被複製到 image，可能與 image 內 `.venv` 混雜，影響 `hermes` entrypoint 與 PATH。

## `Dockerfile`

關鍵修改：

- 安裝 `ca-certificates`，確保 `curl https://...` 具備 CA trust store。
- 安裝 Debian ARM64 `chromium` package。
- 設定 `AGENT_BROWSER_EXECUTABLE_PATH=/usr/bin/chromium`。
- 保留 Playwright build-time browser cache 在 `/opt/hermes/.playwright`。
- 安裝 Cursor CLI 到 `/opt/cursor-agent`。
- 建立 `/usr/local/bin/agent` 與 `/usr/local/bin/cursor-agent` symlink，避免 login shell 重設 PATH 後找不到 Cursor CLI。
- 將 `/opt/hermes/.venv/bin`、`/opt/data/.local/bin`、Cursor CLI bin 加入 `PATH`。

ARM64 特別處理：

`agent-browser install` 在 Linux ARM64 無法下載 Chrome for Testing，因此改用 Debian `chromium` package。這是讓 browser tools 可在 ARM64 container 內運作的關鍵。

## `docker-compose.yml`

關鍵修改：

- 使用本機 build image `ai-agent-cli-env:local`。
- 設定中性的 service / container name `ai-agent-cli`，避免與 Hermes-Agent CLI 指令混淆。
- 使用 `network_mode: host`，讓 container 可連本機模型服務。
- 設定 `shm_size: 1g`，避免 Chromium / Playwright `/dev/shm` 太小。
- 掛載 `${HOME}/.hermes` 到 `/opt/data`，保存 Hermes profile 與 Cursor CLI config。
- 掛載 `/var/run/docker.sock`，讓 container 內 `docker-cli` 可控制 host Docker daemon。
- 預設掛載 `${HOME}/git` 到 `/workspace/git`，提供 agent 可操作的 host 工作目錄。
- 設定 `HOME=/opt/data` 與 `CURSOR_CONFIG_DIR=/opt/data/.cursor`。
- 預設 `command: ["sleep", "infinity"]`，讓 container 在 gateway 尚未設定 messaging platform 前仍可常駐。

## `docker/entrypoint.sh`

關鍵修改：

- 若 Docker runtime 的 `HOME` 是 `/root`，自動改為 `HERMES_HOME`。
- 設定 `CURSOR_CONFIG_DIR` 預設為 `$HOME/.cursor`。
- 若掛載 `/var/run/docker.sock`，自動將 `hermes` runtime user 加入 socket group。
- 初始化 `/opt/data/.local/bin` 與 Cursor config 目錄。
- 保持 dashboard side-process 啟動邏輯，並支援 `sleep infinity` 作為前景 process。
- 第一個參數若是 PATH 上存在的 executable，直接執行該命令；否則沿用 Hermes subcommand wrapper 行為。

## 非 Hermes-Agent Repo 檔案

| 路徑 | 副本路徑 | 用途 |
| --- | --- | --- |
| `scripts/stop-hermes.sh` | `scripts/stop-hermes.sh` | 一鍵執行 `docker compose stop`，停止整個 compose stack。 |
| `README.md` | `README.md` | ARM64 雙 Agent CLI Docker 架設與使用說明。 |
