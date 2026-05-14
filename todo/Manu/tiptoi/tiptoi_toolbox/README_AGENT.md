# README_AGENT.md — Runbook for AI Agents

> **You are an AI coding agent.** This document is the contract between you
> and the `tiptoi_toolbox/` package. Read it once, then act through the CLI
> or Python API. Do not reinvent any workflow — every primitive you need is
> already exposed below.

---

## 1. What this toolbox does

A self-contained pipeline for building **tiptoi** (point-pen) audio packs:

```
mp3 sources  ─┐
              ├──► ogg vorbis (mono / 22050 Hz)  ─┐
              │                                   ├──►  test.gme  (assembled by tttool)
              │   product-id, OID mapping  ──────►│
              │
oid range  ──►   PDF grid of dot patterns (1200 DPI, no scaling)
                 → printable QA index for the pen
```

Two scripts can be combined for the **complete loop**:
1. `audio_processor` — turns a folder of `.mp3` into a working `.gme`.
2. `oid_generator`   — produces a printable PDF that lets a human (or you)
   tap each OID to confirm the audio plays.

---

## 2. Files at a glance

```
tiptoi_toolbox/
├── README_AGENT.md          ← (this file) machine-friendly runbook
├── User_Manual_CN.md        ← human-friendly (Chinese) manual
├── manual.html              ← rendered from User_Manual_CN.md
├── requirements.txt         ← pip dependencies
├── main.py                  ← CLI entry: `--task {init,info,convert,assemble,grid,all}`
├── generate_html.py         ← Markdown → single-file HTML
├── core/
│   ├── __init__.py          ← package surface (re-exports)
│   ├── utils.py             ← find_ffmpeg / find_tttool / font / paths
│   ├── audio_processor.py   ← mp3 → ogg + yaml + assemble
│   └── oid_generator.py     ← OID PNG ensure + PDF grid
└── templates/
    └── default_config.yaml  ← copy-and-edit project skeleton
```

**Hard rule:** no module hard-codes any absolute path. Everything is either
a relative path or comes from a function argument / CLI flag / config file.
Treat the package as relocatable — copy `tiptoi_toolbox/` anywhere and it
will still work.

---

## 3. External binaries you must have on PATH

| Binary  | Purpose                               | Detection helper       |
| ------- | ------------------------------------- | ---------------------- |
| ffmpeg  | mp3 → ogg vorbis transcoding          | `utils.find_ffmpeg()`  |
| tttool  | OID PNG generation, GME (dis)assembly | `utils.find_tttool()`  |

If either is missing, run `python main.py --task info` to confirm. The
human manual (`User_Manual_CN.md` §環境依賴) covers install commands.

---

## 4. CLI contract — what to call, what you get back

All commands return exit code `0` on success, `1` on hard failure, `2` on
partial failure (e.g. some mp3 files failed but the run continued).

### 4.1 Inspect environment

```bash
python main.py --task info
```

Outputs detected ffmpeg / tttool / CJK font + installed Python packages.
**Always run this first** when picking up an unknown machine.

### 4.2 Bootstrap a new project

```bash
python main.py --task init --dst <project_dir> [--force]
```

Copies `templates/default_config.yaml` to `<project_dir>/default_config.yaml`.
Suggested `<project_dir>` layout the user is expected to populate:

```
<project_dir>/
├── default_config.yaml
└── audio/
    └── src/                      ← put *.mp3 here, sorted by name
```

### 4.3 Convert mp3 → gme

```bash
python main.py --task convert \
    --src <project>/audio/src \
    [--out <project>/audio] \
    [--start-oid 1000] \
    [--product-id 999] \
    [--quality 3] \
    [--no-assemble]
```

Behaviour:
- Sorts `*.mp3` by filename (case-insensitive, stable).
- Renames sequentially to `<start_oid>.ogg`, `<start_oid+1>.ogg`, … in `--out`.
- Re-encodes to **Ogg Vorbis / mono / 22050 Hz** (tiptoi-mandated).
- Writes `test.yaml` next to the OGGs (use `--yaml` to override).
- Runs `tttool assemble` to produce `test.gme` (skip with `--no-assemble`).

Inputs you must supply: `--src` (mandatory unless config provides it).
Outputs: `<out>/<oid>.ogg` files, `<out>/test.yaml`, `<out>/test.gme`.

### 4.4 Re-assemble only

```bash
python main.py --task assemble --yaml <path-to>/test.yaml [--gme <out.gme>]
```

Use when the OGGs / YAML already exist and you only need a fresh `.gme`.
Working directory is forced to `yaml_path.parent`, so `media-path: ./%s.ogg`
resolves correctly.

### 4.5 OID test grid PDF

```bash
python main.py --task grid \
    [--low 1000] [--high 1100] \
    [--cols 5] [--code-dim 20] [--gap-mm 20] \
    [--activation-oid 999] \
    [--oid-dir ./oid_codes_grid] \
    [--out index_test.pdf] \
    [--regenerate]
```

Behaviour:
- Generates `oid-N.png` via `tttool` into `--oid-dir` (skipped if present).
- Pre-flattens each PNG `LA → mode '1'` (avoids ReportLab's LA→L+SMask
  resampling, which subtly shifts dot positions).
- Embeds each at **1:1 pixel ratio at 1200 DPI**, snapped to the integer
  pixel grid. Verified pixel-exact with SHA1 in earlier QA.
- Lays out 5 columns × N rows per A4 page, ≥ 2 cm spacing in both axes.
- Page 1 also shows the activation OID (default 999) at the top.

Use `--activation-oid 0` to disable the page-1 header OID entirely.

### 4.6 Full pipeline

```bash
python main.py --task all --src <project>/audio/src
```

Equivalent to `convert` then `grid`, sharing CLI flags. With a config:

```bash
python main.py --config <project>/default_config.yaml --task all
```

### 4.7 Render the human manual

```bash
python generate_html.py                              # User_Manual_CN.md → manual.html
python generate_html.py --src foo.md --out bar.html  # custom paths
```

---

## 5. Programmatic API (preferred when chaining inside Python)

```python
from pathlib import Path
from tiptoi_toolbox.core.audio_processor import (
    convert_directory, run_tttool_assemble, write_yaml,
)
from tiptoi_toolbox.core.oid_generator import GridConfig, generate_grid_pdf

# 1) Build the GME
result = convert_directory(
    src_dir=Path("audio/src"),
    out_dir=Path("audio"),
    start_oid=1000,
    product_id=999,
    assemble=True,
)
print(f"OK: {len(result.successes)}, FAIL: {len(result.failures)}")
print(f"GME: {result.gme_path}")

# 2) Build a printable QA index
grid = generate_grid_pdf(GridConfig(
    low=1000,
    high=1000 + len(result.successes) - 1,    # exactly the OIDs we built
    activation_oid=999,
    output_pdf=Path("index_test.pdf"),
    oid_dir=Path("oid_codes_grid"),
))
print(f"PDF: {grid.output_pdf}  ({grid.pages} pages)")
```

Any tool absence (`ffmpeg`, `tttool`) is reported through the result
objects / raised exceptions — never via `sys.exit`. You can decide what
to do.

---

## 6. Decision rules for an Agent

If the user asks you to…

| User intent                                  | Run this                                                         |
| -------------------------------------------- | ---------------------------------------------------------------- |
| "Set up a new tiptoi project here"           | `--task init --dst .` then guide user to drop mp3s               |
| "Build the GME from these mp3s"              | `--task convert --src <dir>`                                     |
| "Just rebuild the GME"                       | `--task assemble --yaml <yaml>`                                  |
| "Make me a test sheet for OIDs 1000–1100"    | `--task grid --low 1000 --high 1100`                             |
| "Do everything"                              | `--task all --src <dir>`                                         |
| "What tools / fonts does the machine have?"  | `--task info`                                                    |
| "Generate a nicer HTML manual"               | `python generate_html.py`                                        |

Always show the user the command you ran and the artefacts produced
(use `--out` paths). Never embed your own absolute paths into the code.

---

## 7. Invariants you must preserve when editing this package

1. **No absolute paths anywhere** in source. Use `pathlib.Path`, relative
   to either CWD or `utils.package_root()`.
2. **OID images stay 1:1 at 1200 DPI**: do NOT add `preserveAspectRatio=True`,
   do NOT resize `code_dim_mm` post-generation, do NOT compress the embedded
   PNG to JPEG. The dot pitch must match the pen's optics exactly.
3. **OGG output stays mono / 22050 Hz / libvorbis**. The pen's firmware
   refuses other formats silently.
4. **Logging not printing** in `core/*`: library code uses `logging`; only
   `main.py` and `generate_html.py` print to stdout.
5. **No new pip deps** without adding them to `requirements.txt` AND the
   "環境依賴" section of `User_Manual_CN.md`.
6. **Portability test before declaring done**: `cp -r tiptoi_toolbox /tmp/ &&
   cd /tmp/tiptoi_toolbox && python3 main.py --task info` must succeed.

---

## 8. Known gotchas

- **tttool wrapper script**: some downloads ship a shell wrapper that
  expects `linux/tttool` next to it. If `--task info` shows tttool but
  every command fails with "No such file or directory", the wrapper is
  broken — point `~/bin/tttool` at the actual ELF binary instead.
- **CJK font fallback**: missing CJK font → titles render as Helvetica
  (boxes / tofu in the PDF). Install `fonts-wqy-zenhei` (apt) or
  `fonts-noto-cjk` (apt/brew) and re-run.
- **OID 999 is *not* a generic activation code** — it's the German
  language switch on 4th-gen pens. The toolbox still labels it
  "啟動碼" because that is how the user refers to it.

---

*End of agent runbook. Human-readable docs live in `User_Manual_CN.md`.*
