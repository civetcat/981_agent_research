# tiptoi_toolbox 使用說明書

> 一個自帶 CLI 的小工具箱，把 **mp3 → ogg → tttool 組裝 .gme** 與
> **OID 點讀碼測試 PDF** 兩條流程都封進同一個資料夾，可整包搬走、跨機器執行。
> 適合給 tiptoi 點讀筆做客製語音包與品質驗證。

---

## 1. 這份工具箱能做什麼

| 任務 | 對應指令 | 產出 |
| :-- | :-- | :-- |
| 偵測環境 | `python main.py --task info` | 列出 ffmpeg / tttool / 字型 / Python 套件版本 |
| 建立新專案 | `python main.py --task init --dst ./my_project` | `my_project/default_config.yaml` |
| 音檔轉碼 + 組 GME | `python main.py --task convert --src ./audio/src` | `<oid>.ogg`、`test.yaml`、`test.gme` |
| 只組 GME | `python main.py --task assemble --yaml ./test.yaml` | `test.gme` |
| 印測試索引 PDF | `python main.py --task grid --low 1000 --high 1100` | `index_test.pdf` |
| 一條龍 | `python main.py --task all --src ./audio/src` | 上面全部 |
| 產出 HTML 說明書 | `python generate_html.py` | `manual.html` |

---

## 2. 環境依賴

工具箱本身只是 Python；真正做事的是兩個 **系統二進位** + 幾個 pip 套件。

### 2.1 系統二進位

#### `ffmpeg`（音訊轉碼）

```bash
# Ubuntu / Debian
sudo apt update
sudo apt install -y ffmpeg

# macOS
brew install ffmpeg

# Windows (winget)
winget install Gyan.FFmpeg
```

驗證：

```bash
ffmpeg -version
```

#### `tttool`（OID 點讀碼產生 / GME 組裝）

來源：<https://github.com/entropia/tip-toi-reveng/releases>

```bash
# 範例：Linux x86_64
mkdir -p ~/opt && cd ~/opt
wget https://github.com/entropia/tip-toi-reveng/releases/download/1.11/tttool-1.11.zip
unzip tttool-1.11.zip
# 注意 zip 內的 `tttool` 是 wrapper script，會去找 `linux/tttool` 真檔。
# 最簡單的作法是把 ELF 檔直接放到 PATH：
mkdir -p ~/bin
cp ~/opt/tttool-1.11/linux/tttool ~/bin/tttool
chmod +x ~/bin/tttool
echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

驗證：

```bash
tttool --version
# 預期輸出: tttool 1.11
```

> **常見坑：** 直接把 zip 內的 wrapper symlink 到 `~/bin/tttool` 會出現
> `linux/tttool: No such file or directory`，因為 wrapper 是用相對路徑找
> ELF 檔。改成上面「直接複製 ELF 二進位」的作法即可。

#### CJK 中文字型（PDF 中文標籤需要）

```bash
# Ubuntu / Debian (二擇一即可)
sudo apt install -y fonts-wqy-zenhei      # 文泉驛正黑 (預設第一順位)
sudo apt install -y fonts-noto-cjk        # Noto Sans CJK
```

工具箱會自動偵測並 fallback 到 Helvetica（中文會變方塊），所以
不裝也跑得起來，只是 PDF 標題會看不到中文。

### 2.2 Python 套件

```bash
cd tiptoi_toolbox
pip install -r requirements.txt
```

`requirements.txt` 內容：

| 套件 | 用途 |
| :-- | :-- |
| `reportlab` | 產 PDF |
| `Pillow` | 影像預處理 (LA → 1-bit) |
| `PyYAML` | 讀 `--config` 設定檔 |
| `markdown` | `generate_html.py` 主引擎 |
| `Pygments` | 程式碼語法高亮 |

可選：`pydub`（如果你想用更 high-level 的 Python API 處理音檔，
不過本工具箱用 `subprocess` 直接呼叫 ffmpeg 以求最少依賴與最大可預測性）。

### 2.3 一鍵驗證

```bash
cd tiptoi_toolbox
python3 main.py --task info
```

應看到 ffmpeg / tttool / CJK font 都顯示路徑，五個 Python 套件都標 `[OK]`。
任何一行顯示 `(NOT FOUND)` 或 `(not installed)` 就先補齊它。

---

## 3. 第一次使用（5 分鐘上手）

> 以下範例假設工具箱解壓在 `<TOOLBOX>` 這個位置（例：
> `~/tiptoi_toolbox` 或 `D:\tools\tiptoi_toolbox`）。把 `<TOOLBOX>`
> 整段替換成你電腦上的實際路徑即可。

### 3.1 建立專案資料夾

```bash
cd ~/projects                 # 或任何你喜歡的位置
python <TOOLBOX>/main.py --task init --dst ./my_voice_pack
```

得到：

```
my_voice_pack/
└── default_config.yaml
```

### 3.2 把 mp3 放進去

```bash
mkdir -p my_voice_pack/audio/src
# 把要錄進筆的 mp3 都放進去；建議命名 01_xxx.mp3, 02_xxx.mp3 ...
# 排序順序就是 OID 編號順序
ls my_voice_pack/audio/src
# 01_hello.mp3  02_thanks.mp3  03_goodbye.mp3 ...
```

### 3.3 編輯設定

打開 `my_voice_pack/default_config.yaml`，至少確認：

```yaml
project:
  product_id: 999          # 想用哪個 product-id

audio:
  src_dir: ./audio/src     # 不動 (相對於 yaml 所在目錄)
  out_dir: ./audio
  start_oid: 1000          # 想從哪個 OID 開始

oid_grid:
  low: 1000
  high: 1100               # 視 mp3 數量調整
```

### 3.4 跑一條龍

```bash
cd my_voice_pack
python <TOOLBOX>/main.py --config ./default_config.yaml --task all
```

跑完會產出：

```
my_voice_pack/
├── audio/
│   ├── 1000.ogg       # 從 01_hello.mp3 來
│   ├── 1001.ogg       # 從 02_thanks.mp3 來
│   ├── ...
│   ├── test.yaml      # tttool 用的設定
│   └── test.gme       # 燒進筆的最終檔
├── oid_codes_grid/    # 100 個 oid-NNNN.png (供 PDF 用)
└── index_test.pdf     # A4 測試索引頁
```

### 3.5 把 .gme 灌進筆 + 列印 PDF + 開測

1. 將點讀筆接 USB，會被當隨身碟掛載。
2. 把 `audio/test.gme` 複製到筆內存放 GME 檔的目錄
   （視筆代不同，常見是根目錄或 `gme/`）。
3. 拔筆、開機。
4. 用筆點 PDF 上的 999 啟動碼（或你 product-id 對應的啟動碼）。
5. 依序點 1000、1001 …，每個都應該對應你錄的那段 mp3。

---

## 4. 印表機 1200 DPI 設定建議（**重要**）

OID 是「微點陣列」，每個 dot 約 0.1 mm，要靠 **印表機解析度**
+ **筆的鏡頭** 才讀得到。沒設好就是「全部點不到反應」。

### 4.1 必要硬體條件

| 項目 | 最低 | 建議 |
| :-- | :-- | :-- |
| 印表機 | 600 dpi 雷射 | **1200 dpi 雷射** |
| 紙張 | 80 g/m² 普通影印紙 | 80–100 g/m² 霧面影印紙 |
| 碳粉 | 原廠碳粉 | 原廠碳粉 (副廠常擴散變模糊) |

> ❌ **不要用噴墨印表機。** 噴墨墨點會在紙纖維上擴散，把 dot 糊掉。
> ❌ **不要用熱昇華 / 熱感應。** 對比不夠 / 反光問題。
> ⚠ 如果只有 600 dpi，OID 物理尺寸請拉到 25 mm 以上，dot 還是能讀，
>    但建議升級到 1200 dpi 印表機。

### 4.2 印表機驅動設定

#### Linux (CUPS)

```bash
# 系統設定 → 印表機 → 你的雷射印表機 → Settings
# 把以下都勾上 / 設定:
#   Resolution: 1200 dpi  (而不是 600 / Auto)
#   Color Mode: Black & White / Grayscale
#   Toner Saving / Economy mode: OFF
#   Smoothing / 邊緣強化: OFF       ← 這個會把 dot 圓化導致誤讀
#   Resize / Scaling: 100% / Actual Size  ← 千萬不能 Fit to page
```

#### macOS

`File → Print` 進去後：

- **Show Details** 展開
- 紙張設定選 A4
- 縮放 (Scale) 設 **100%**
- Quality 選 **Best / 1200 dpi**
- 影像處理 / Halftone 關掉

#### Windows

印表機內容 → 進階：

- 列印品質：**1200 × 1200 dpi**
- 色彩模式：黑白 / 灰階
- 紙張處理：實際大小 (不縮放)
- 圖形設定 → 影像平滑化 / TrueType 替代：**關閉**

### 4.3 列印對話框

無論哪個 OS，**「縮放 / Scaling」一定要設 100% / Actual Size**。
任何 “Fit to page”、“Shrink to fit”、“Auto” 都會把 dot pitch 拉跑掉，
筆會完全讀不到。

PDF 第 1 頁的頁尾固定有提醒：

> 列印：A4 100% 不縮放 ‧ 600 DPI 以上雷射印表機

照做就對了。

### 4.4 印完怎麼驗證

1. 拿真的 999 OID 圖卡（隨筆附的活化卡）跟你印的 999 比對：
   兩者用尺量物理尺寸應幾乎一模一樣（差異 < 0.5 mm）。
2. 用筆先點原廠 999 → 換點你印的 999 → 兩者都能切換語系才算過關。
3. 再點 1000、1001 確認音檔對得上。

如果原廠卡能讀、你印的不能讀 → **印表機設定問題**（多半是 dpi
被降回 600 或開了平滑化）。

---

## 5. OID 1000–1100 測試流程（標準 QA 程序）

這是把整個工具箱端到端跑一遍的標準腳本。

### Step 1 — 準備 mp3

把你要驗的所有音檔放進 `audio/src/`，按命名排序。
數量等於你要的 OID 數量；本範例是 101 段（OID 1000 到 1100）。

```bash
ls audio/src | wc -l
# 101
```

### Step 2 — 跑一條龍

```bash
python main.py --config ./default_config.yaml --task all
```

或不用設定檔：

```bash
python main.py --task all \
    --src ./audio/src \
    --start-oid 1000 \
    --product-id 999 \
    --low 1000 --high 1100
```

預期輸出尾段：

```
轉檔成功: 101 / 101
YAML:    .../audio/test.yaml  (3.10 KB)
GME:     .../audio/test.gme  (XX.XX MB)

[grid] OID 1000..1100  → index_test.pdf
完成: index_test.pdf  (~1 MB)
頁數: 4
OID 像素: 945×945
```

### Step 3 — 灌 GME 進筆

```
audio/test.gme  →  (USB 複製)  →  筆內 GME 目錄
```

### Step 4 — 列印 PDF

`index_test.pdf` 用 1200 dpi 雷射印表機 100% 列印（見 §4）。
4 頁全部印好。

### Step 5 — 逐碼點測

| 步驟 | 操作 | 預期結果 |
| :-- | :-- | :-- |
| 1 | 點 PDF 第 1 頁的 999 | 筆切到對應語系 / 提示音 |
| 2 | 點第 1 頁的 1000 | 第 1 段音檔播放 |
| 3 | 點第 1 頁的 1001 | 第 2 段音檔播放 |
| … | 直到第 4 頁的 1100 | 第 101 段音檔播放 |

### Step 6 — 故障排除對照表

| 現象 | 可能原因 | 處理 |
| :-- | :-- | :-- |
| 點任何碼都沒反應 | 沒點 999 啟動 / 印表機 dpi 不夠 / GME 沒灌 | 先確認 §4.4 的驗證步驟 |
| 999 有反應，1000 開始全沒反應 | product-id 對不上 | 確認 `default_config.yaml` 的 `project.product_id` |
| 99% 能讀，少數幾顆不行 | dot 印壞 / 紙皺 | 重印該頁，或用 `--regenerate` 重產 PNG 再印 |
| 點 1000 卻播 1001 的音 | mp3 命名排序跟想的不一樣 | 改 mp3 檔名讓字典序符合預期 |
| 筆唸出錯誤的「啟動碼語言」 | 999 對應第 4 代筆是 *德語* 切換 | 換用筆對應語系的活化碼，而不是硬填 999 |

### Step 7 — 通過驗收

101 個 OID 全對 → 把 `audio/test.gme`、`audio/test.yaml`、`index_test.pdf`
打包封存即可（建議連同當次 `default_config.yaml` 一起存）。

---

## 6. 進階使用

### 6.1 拆步驟跑

```bash
# 只轉檔，不組 GME
python main.py --task convert --src ./mp3 --no-assemble

# 之後手動組
python main.py --task assemble --yaml ./audio/test.yaml

# 換印新一批 OID 但不重做音檔
python main.py --task grid --low 2000 --high 2050 --code-dim 22 --cols 4
```

### 6.2 改 OID 物理尺寸

```bash
# 18 mm × 18 mm OID，5 欄
python main.py --task grid --code-dim 18 --gap-mm 22

# 25 mm × 25 mm OID，4 欄
python main.py --task grid --code-dim 25 --cols 4 --gap-mm 22
```

排版函式會自動算「裝不下就報錯」，不會偷偷縮小 OID。

### 6.3 在 Python 程式裡呼叫

```python
from pathlib import Path
from tiptoi_toolbox.core.audio_processor import convert_directory
from tiptoi_toolbox.core.oid_generator import GridConfig, generate_grid_pdf

result = convert_directory(
    src_dir=Path("audio/src"),
    out_dir=Path("audio"),
    start_oid=1000, product_id=999,
    assemble=True,
)

generate_grid_pdf(GridConfig(
    low=1000,
    high=1000 + len(result.successes) - 1,
    output_pdf=Path("index_test.pdf"),
))
```

### 6.4 自製 HTML 說明書

```bash
# 用預設輸入輸出
python generate_html.py

# 自訂
python generate_html.py --src 我的筆記.md --out output.html --title "客戶版手冊"
```

`manual.html` 是 **單一檔**，所有 CSS / 字型堆疊都嵌進去，可以直接 email 給人。

---

## 7. 整包搬移到別台機器

工具箱所有檔案都是相對路徑，搬移不需要改設定：

```bash
# 從來源機器搬走整個資料夾
scp -r <TOOLBOX> user@<target-host>:~/

# 在新機器
ssh user@<target-host>
cd ~/tiptoi_toolbox            # (或你 scp 過去後的實際資料夾名)
pip install -r requirements.txt
sudo apt install -y ffmpeg fonts-wqy-zenhei      # tttool 自行下載 (見 §2.1)
python3 main.py --task info                      # 確認都綠
python3 main.py --task grid --low 1000 --high 1010   # 跑一個小 sanity test
```

> **資料夾名也可隨便改。** main.py 透過 `__file__` 找自己的 `core/`，
> 不依賴資料夾叫 `tiptoi_toolbox`，所以 `mv tiptoi_toolbox foo && cd foo &&
> python3 main.py --task info` 一樣可以跑。

需要轉移到 Windows、macOS 也是同樣模式。`utils.py` 內的 `FFMPEG_CANDIDATES`
和 `TTTOOL_CANDIDATES` 已含三大平台的常見路徑。

---

## 8. 檔案結構詳細表

```
tiptoi_toolbox/
├── README_AGENT.md          # 給 AI Agent 讀的精簡 runbook
├── User_Manual_CN.md        # 本檔 (給人看)
├── manual.html              # 由 generate_html.py 產生的單檔 HTML
├── requirements.txt         # pip 依賴
├── main.py                  # CLI 進入點
├── generate_html.py         # markdown → html
├── core/
│   ├── __init__.py
│   ├── utils.py             # find_tool / 字型 / 路徑常數
│   ├── audio_processor.py   # mp3 → ogg + yaml + assemble
│   └── oid_generator.py     # OID PNG ensure + PDF 網格
└── templates/
    └── default_config.yaml  # 專案設定範本 (init 任務複製此檔)
```

---

## 9. 常見問題 (FAQ)

**Q: 為什麼要用 `subprocess` 直接叫 ffmpeg，而不用 `pydub`？**
A: 為了最少依賴 + 結果可預測。`pydub` 內部仍然是 ffmpeg，但多一層
   會吞掉部分錯誤訊息。追求簡潔可以裝 `pydub` 自己包；本工具箱核心
   只用 stdlib + ffmpeg + tttool。

**Q: PDF 內 OID 圖會被 ReportLab 壓縮 / 模糊嗎？**
A: 不會。我們先用 PIL 把每個 OID 從 LA 模式壓平成 1-bit，再用
   `ImageReader(pil)` 餵給 ReportLab，內部走 FlateDecode 無損 zlib。
   過去已用 SHA1 比對驗證 102 張全部 pixel-exact。

**Q: 我可以混不同尺寸的 OID 嗎？**
A: 同一份 PDF 內不行（網格假設等寬）。如果要混，請各自用獨立的
   `GridConfig` 做兩份 PDF 再合併。

**Q: 999 是不是任何 product-id 都能用的「萬用啟動碼」？**
A: **不是。** 999 在第 4 代筆上是「切換成德語」的特殊碼，剛好被
   常常用來當示範。實際的「啟動」對應到 `product-id`，所以你
   build 的 GME 用什麼 product-id，就需要對應 product-id 的活化方式。

**Q: 可以把 .gme 還原回 mp3 + yaml 嗎？**
A: 可以：`tttool export <file>.gme`、`tttool play <file>.gme`。本工具箱
   暫未包這個功能，但 `core/utils.find_tttool()` 已經幫你找好二進位。

---

*工具箱版本：0.1.0 — 由 `tiptoi_toolbox` 產生 ‧ 任何問題請看 `README_AGENT.md` 的 §8 已知地雷。*
