---
name: build-code-on-docker
description: Builds/tests code inside a Docker container (Go and C/C++). Use when the user asks to build, compile, run tests, or reproduce build errors, and the project must be built in Docker. Replace the default image with your team CI image via BUILD_IMAGE. 常見觸發：幫我 build / 幫我編譯 / 驗證編譯 / 在 docker 裡跑 / go build / go test / cmake / make / ctest / 重現 build 錯誤。
---

# Build code on Docker

## 共用說明（協作者必讀）

- 下文預設映像檔僅為**範例**（Go 1.22 工具鏈）。請改成你們團隊實際使用的 image，例如：`export BUILD_IMAGE=your-registry/your-go-builder:tag`。
- 掛載與工作目錄維持 `-v "$PWD":/work -w /work`，若專案慣例不同請一併調整。

## Quick start（預設流程）

在專案根目錄執行（會把目前目錄掛載到容器 `/work`）：

```bash
export BUILD_IMAGE="${BUILD_IMAGE:-sumbuild/sumgobuild:go1.22.5}"
docker run -i -t \
  -v "$PWD":/work \
  --dns 8.8.8.8 \
  --rm \
  -w /work \
  "$BUILD_IMAGE" \
  bash -lc 'go version && go env && go build ./...'
```

## 規則與優先順序

- **所有 build/test 都在容器內執行**：不要直接在 host 上跑 `go build` / `ctest` / `make`（若專案規範如此）。
- **需要 build Docker image 時，只用 `docker build`**：不要用其他 build 工具替代 docker build。
- **路徑對應**：預設用 `-v "$PWD":/work -w /work`。

## 常用指令模板（直接套用）

先設好：`export BUILD_IMAGE="${BUILD_IMAGE:-sumbuild/sumgobuild:go1.22.5}"`

### Go

**Build**

```bash
docker run -i -t -v "$PWD":/work --dns 8.8.8.8 --rm -w /work "$BUILD_IMAGE" bash -lc 'go build ./...'
```

**Test**

```bash
docker run -i -t -v "$PWD":/work --dns 8.8.8.8 --rm -w /work "$BUILD_IMAGE" bash -lc 'go test ./...'
```

**下載相依**

```bash
docker run -i -t -v "$PWD":/work --dns 8.8.8.8 --rm -w /work "$BUILD_IMAGE" bash -lc 'go mod download'
```

### C/C++（cmake / make）

**CMake configure + build（in-tree build）**

```bash
docker run -i -t -v "$PWD":/work --dns 8.8.8.8 --rm -w /work "$BUILD_IMAGE" bash -lc 'cmake -S . -B build && cmake --build build -j'
```

**CTest**

```bash
docker run -i -t -v "$PWD":/work --dns 8.8.8.8 --rm -w /work "$BUILD_IMAGE" bash -lc 'cd build && ctest --output-on-failure'
```

**Make**

```bash
docker run -i -t -v "$PWD":/work --dns 8.8.8.8 --rm -w /work "$BUILD_IMAGE" bash -lc 'make -j'
```

## 互動除錯（進容器開 shell）

```bash
export BUILD_IMAGE="${BUILD_IMAGE:-sumbuild/sumgobuild:go1.22.5}"
docker run -i -t -v "$PWD":/work --dns 8.8.8.8 --rm -w /work "$BUILD_IMAGE" bash
```

## docker build（只在要產 image 時用）

```bash
docker build -t my-image:dev .
```

## 失敗時要回報的資訊（讓除錯更快）

- **你執行的完整 docker 指令**
- **錯誤輸出全文**
- （Go）`go env` / （CMake）`cmake -S . -B build` 的輸出
