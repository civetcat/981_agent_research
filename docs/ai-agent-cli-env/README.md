# ARM64 AI Agent CLI Docker 環境文件

此資料夾保存 ARM64 Linux 系統上架設 `ai-agent-cli-env` Docker 環境所需的文件與修改檔案副本。此 image 目前同時支援 Hermes-Agent CLI 與 Cursor CLI，並保留 browser automation、Docker CLI、dashboard 與 host 工作目錄 bind mount 等既有工具能力。

## 目前環境

- Host OS: Ubuntu 22.04.5 LTS
- CPU architecture: `aarch64` / ARM64
- Docker: `29.4.1`
- Docker Compose: `v5.1.3`
- Hermes-Agent: `v0.12.0`
- Cursor CLI: `2026.05.05-84a231c`
- Docker image: `ai-agent-cli-env:local`
- Container name: `ai-agent-cli`
- Default source path: `$HOME/.hermes/hermes-agent`
- Default data path: `$HOME/.hermes`
- Container data path: `/opt/data`
- Dashboard URL: `http://127.0.0.1:9119`

## 資料夾內容

```text
ai-agent-cli-env/
├── README.md
├── MODIFIED_FILES.md
├── hermes-agent/
│   ├── .dockerignore
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker/
│       └── entrypoint.sh
└── scripts/
    └── stop-hermes.sh
```

用途：

- `README.md`: ARM64 Docker 架設、使用與驗證說明。
- `MODIFIED_FILES.md`: Hermes-Agent repo 修改檔案清單與修改原因。
- `hermes-agent/*`: 已修改的 Hermes-Agent 檔案副本。
- `scripts/stop-hermes.sh`: 一鍵停止 compose stack 的腳本副本。

## Build Context 注意事項

`hermes-agent/` 目錄只保存 Docker 相關修改檔案，不是完整 Hermes-Agent source tree，不能單獨用來 `docker build` 或 `docker compose up --build`。

此 Dockerfile 需要完整 Hermes-Agent source 作為 build context，因為 build 過程會複製並安裝下列專案檔案：

```text
package.json
package-lock.json
pyproject.toml
web/
ui-tui/
hermes_cli/
docker/
```

建議先將 Hermes-Agent source 放在預設路徑：

```bash
export HERMES_AGENT_DIR="$HOME/.hermes/hermes-agent"
```

若是在全新機器重建此環境，必須先下載或 clone Hermes-Agent source，再把本資料夾保存的 `Dockerfile`、`.dockerignore`、`docker-compose.yml` 與 `docker/entrypoint.sh` 套用到 Hermes-Agent source tree。Cursor CLI 不需要另外手動下載，image build 時會透過 `curl https://cursor.com/install -fsS | bash` 安裝到 container 內。

## 關鍵設計

### 雙 CLI Runtime

同一個 image 內同時提供：

- Hermes-Agent CLI: `hermes`
- Cursor CLI: `agent` / `cursor-agent`

下方範例中的 `ai-agent-cli` 是 Docker container name；`hermes` 與 `agent` 則是 container 內執行的 CLI command。

Cursor CLI 於 build 階段安裝到 `/opt/cursor-agent`，並透過 `/usr/local/bin/agent` 與 `/usr/local/bin/cursor-agent` 提供穩定入口。Runtime 設定使用：

```yaml
HOME=/opt/data
CURSOR_CONFIG_DIR=/opt/data/.cursor
```

這讓 Cursor login/config 與 Hermes profile 一起持久化到 host 的 `$HOME/.hermes`。

### ARM64 Browser Tools

Linux ARM64 沒有 Chrome for Testing build，所以 `agent-browser install` 不能下載 bundled Chrome。Dockerfile 改用 Debian ARM64 `chromium` package，並設定：

```dockerfile
ENV AGENT_BROWSER_EXECUTABLE_PATH=/usr/bin/chromium
```

這讓 Hermes browser tools 與 `agent-browser` 能在 ARM64 container 內穩定使用。

### 常駐 Container

`docker-compose.yml` 預設使用：

```yaml
command: ["sleep", "infinity"]
```

原因是尚未設定 messaging platform 時，`hermes gateway run` 會結束，container 也會停止。使用 `sleep infinity` 可讓環境常駐，方便透過 `docker exec` 執行 Hermes、Cursor、browser 與 Docker 工具。

### Docker Socket

compose 掛載：

```yaml
- /var/run/docker.sock:/var/run/docker.sock
```

entrypoint 會自動把 runtime user 加入 Docker socket 的 group，讓 container 內 `docker-cli` 可以操作 host Docker daemon。

注意：能存取 Docker socket 的 container 具備高權限，只建議在可信任本機 profile 使用。

### Host 工作目錄映射

目前 compose 掛載：

```yaml
- ${HOME}/git:/workspace/git
```

Agent 在 container 內應使用 `/workspace/git` 操作 host `$HOME/git` 內容。若要額外映射其他 host 專案，例如 `$HOME/my-project`，可在 `docker-compose.yml` 增加：

```yaml
volumes:
  - ${HOME}/my-project:/workspace/my-project
```

## 啟動與重建

進入 source 目錄：

```bash
cd "${HERMES_AGENT_DIR:-$HOME/.hermes/hermes-agent}"
```

第一次 build 或 Dockerfile / compose 有修改時：

```bash
HERMES_UID=$(id -u) HERMES_GID=$(id -g) docker compose up -d --build
```

只啟動既有 image：

```bash
HERMES_UID=$(id -u) HERMES_GID=$(id -g) docker compose up -d
```

強制 rebuild image 並重建 container：

```bash
HERMES_UID=$(id -u) HERMES_GID=$(id -g) docker compose up -d --build --force-recreate
```

## 停止方式

使用停止腳本：

```bash
# 請在 ai-agent-cli-env repository root 執行。
./scripts/stop-hermes.sh
```

或手動停止：

```bash
cd "${HERMES_AGENT_DIR:-$HOME/.hermes/hermes-agent}"
docker compose stop
```

停止並移除 container：

```bash
cd "${HERMES_AGENT_DIR:-$HOME/.hermes/hermes-agent}"
docker compose down
```

## Hermes CLI 使用方式

檢查版本：

```bash
docker exec ai-agent-cli hermes version
```

執行 doctor：

```bash
docker exec -it ai-agent-cli hermes doctor
```

設定 Hermes：

```bash
docker exec -it ai-agent-cli hermes setup
```

設定模型與工具：

```bash
docker exec -it ai-agent-cli hermes model
docker exec -it ai-agent-cli hermes tools
```

## Cursor CLI 使用方式

檢查版本：

```bash
docker exec ai-agent-cli agent --version
```

檢查登入狀態：

```bash
docker exec ai-agent-cli agent status
```

登入 Cursor：

```bash
docker exec -it ai-agent-cli agent login
```

執行 headless / print mode：

```bash
docker exec -it ai-agent-cli agent -p "review this workspace" --workspace /workspace/git
```

## Gateway 與 Dashboard

目前 compose 預設不直接執行 gateway。若要設定 messaging platform：

```bash
docker exec -it ai-agent-cli hermes gateway setup
docker exec -it ai-agent-cli hermes gateway run
```

若要正式讓 container 啟動後直接跑 gateway，將 `docker-compose.yml` 的 command 從：

```yaml
command: ["sleep", "infinity"]
```

改為：

```yaml
command: ["gateway", "run"]
```

Dashboard 已由 compose 啟用：

```yaml
HERMES_DASHBOARD=1
HERMES_DASHBOARD_HOST=127.0.0.1
HERMES_DASHBOARD_TUI=1
```

本機瀏覽器開啟：

```text
http://127.0.0.1:9119
```

遠端使用建議透過 SSH tunnel：

```bash
ssh -L 9119:127.0.0.1:9119 <user>@<host>
```

## 快速驗證

```bash
cd "${HERMES_AGENT_DIR:-$HOME/.hermes/hermes-agent}"

HERMES_UID=$(id -u) HERMES_GID=$(id -g) docker compose up -d

docker compose ps

docker inspect ai-agent-cli --format 'Image={{.Config.Image}} Status={{.State.Status}}'

docker exec ai-agent-cli hermes version

docker exec ai-agent-cli agent --version

docker exec ai-agent-cli sh -lc 'agent --version'

docker exec ai-agent-cli docker ps --filter name=ai-agent-cli

curl -fsS http://127.0.0.1:9119/ >/dev/null && echo dashboard-ok
```

## Browser Tools 驗證

檢查 system Chromium：

```bash
docker exec ai-agent-cli chromium --version
```

驗證 `agent-browser`：

```bash
docker exec -e HOME=/opt/data -e HERMES_HOME=/opt/data ai-agent-cli sh -c \
  'cd /opt/hermes && node_modules/.bin/agent-browser open "data:text/html,<title>ok</title><h1>ok</h1>" --json'
```

驗證 Hermes browser wrapper：

```bash
docker exec -e HOME=/opt/data -e HERMES_HOME=/opt/data ai-agent-cli sh -c 'cd /opt/hermes && python - <<'"'"'PY'"'"'
from model_tools import handle_function_call

print(handle_function_call("browser_navigate", {
    "url": "data:text/html,<title>hermes-browser-ok</title><h1>browser-ok</h1>"
}))
print(handle_function_call("browser_snapshot", {"full": True}))
PY'
```

## 已驗證工具

目前已在 container 內驗證：

- `hermes version`
- `hermes doctor`
- `agent --version`
- `agent --help`
- Python 3.13
- Node.js / npm
- `ripgrep`
- `git`
- `ffmpeg`
- `openssh-client`
- `docker-cli`
- Docker socket access
- Playwright Chromium headless launch
- system Chromium `/usr/bin/chromium`
- `agent-browser`
- Hermes `browser_navigate` / `browser_snapshot`
- Dashboard HTTP endpoint

## 套用副本檔案

若需要把本資料夾保存的副本套回 Hermes-Agent source tree：

```bash
cd <path-to-ai-agent-cli-env>
export AI_AGENT_CLI_ENV_DIR="$(pwd)"
export HERMES_AGENT_DIR="${HERMES_AGENT_DIR:-$HOME/.hermes/hermes-agent}"

cp "$AI_AGENT_CLI_ENV_DIR/hermes-agent/Dockerfile" \
  "$HERMES_AGENT_DIR/Dockerfile"

cp "$AI_AGENT_CLI_ENV_DIR/hermes-agent/.dockerignore" \
  "$HERMES_AGENT_DIR/.dockerignore"

cp "$AI_AGENT_CLI_ENV_DIR/hermes-agent/docker-compose.yml" \
  "$HERMES_AGENT_DIR/docker-compose.yml"

cp "$AI_AGENT_CLI_ENV_DIR/hermes-agent/docker/entrypoint.sh" \
  "$HERMES_AGENT_DIR/docker/entrypoint.sh"
```

套用後建議重新 build：

```bash
cd "${HERMES_AGENT_DIR:-$HOME/.hermes/hermes-agent}"
HERMES_UID=$(id -u) HERMES_GID=$(id -g) docker compose up -d --build --force-recreate
```
