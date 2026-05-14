#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_html.py
================

把 Markdown 文件 (預設：本目錄下的 ``User_Manual_CN.md``) 轉成單一檔案的
``manual.html``，包含：

* CJK-friendly 字型 stack
* 內嵌 Pygments 語法高亮 CSS
* 自動目錄 (``[TOC]`` 標記)
* 表格、fenced code、definition list、footnotes、smarty quotes 等延伸
* 適合列印的 ``@media print`` 區塊

用法：

    python generate_html.py                         # 預設：User_Manual_CN.md → manual.html
    python generate_html.py --src foo.md --out bar.html
    python generate_html.py --no-toc                # 關掉自動目錄

輸出 HTML 是 **單一獨立檔**，不依賴外部 CSS / 字型 / JS — 直接用瀏覽器
打開即可，方便寄給合作對象或丟到 Notion / Confluence。
"""

from __future__ import annotations

import argparse
import datetime
import html
import sys
from pathlib import Path
from typing import Optional

# 預設輸入/輸出 (相對於本檔案所在目錄)
DEFAULT_SRC = "User_Manual_CN.md"
DEFAULT_OUT = "manual.html"


# =====================================================================
# CSS：CJK 字型 + Pygments + 列印樣式
# =====================================================================

_BASE_CSS = """
:root {
  --fg: #1f2328;
  --fg-muted: #57606a;
  --bg: #ffffff;
  --bg-soft: #f6f8fa;
  --border: #d0d7de;
  --link: #0969da;
  --code-bg: #f6f8fa;
  --code-border: #d0d7de;
  --accent: #0969da;
  --warn-bg: #fff8c5;
  --warn-fg: #59450b;
  --warn-border: #d4a72c;
}

@media (prefers-color-scheme: dark) {
  :root {
    --fg: #e6edf3;
    --fg-muted: #8b949e;
    --bg: #0d1117;
    --bg-soft: #161b22;
    --border: #30363d;
    --link: #58a6ff;
    --code-bg: #161b22;
    --code-border: #30363d;
    --accent: #58a6ff;
    --warn-bg: #271c00;
    --warn-fg: #d29922;
    --warn-border: #9e6a03;
  }
}

* { box-sizing: border-box; }

html { -webkit-text-size-adjust: 100%; }

body {
  font-family:
    -apple-system, BlinkMacSystemFont, "Segoe UI",
    "PingFang TC", "Heiti TC", "Microsoft JhengHei",
    "Noto Sans CJK TC", "WenQuanYi Zen Hei",
    Helvetica, Arial, sans-serif;
  font-size: 16px;
  line-height: 1.7;
  color: var(--fg);
  background: var(--bg);
  margin: 0;
  padding: 0;
}

main {
  max-width: 880px;
  margin: 0 auto;
  padding: 32px 28px 96px;
}

header.doc-header {
  border-bottom: 1px solid var(--border);
  padding-bottom: 18px;
  margin-bottom: 28px;
}
header.doc-header .crumbs {
  color: var(--fg-muted);
  font-size: 13px;
  margin-bottom: 6px;
}
header.doc-header h1 {
  margin: 0;
  font-size: 28px;
  letter-spacing: -0.01em;
}
header.doc-header .meta {
  color: var(--fg-muted);
  font-size: 13px;
  margin-top: 6px;
}

h1, h2, h3, h4, h5, h6 {
  font-weight: 600;
  line-height: 1.25;
  margin: 1.6em 0 0.6em;
}
h1 { font-size: 26px; border-bottom: 1px solid var(--border); padding-bottom: 8px; }
h2 { font-size: 22px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }
h3 { font-size: 18px; }
h4 { font-size: 16px; color: var(--fg-muted); }

p { margin: 0.6em 0; }

a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }

ul, ol { padding-left: 1.6em; }
li { margin: 0.25em 0; }
li > p { margin: 0.25em 0; }

blockquote {
  border-left: 4px solid var(--border);
  margin: 1em 0;
  padding: 0.4em 1em;
  color: var(--fg-muted);
  background: var(--bg-soft);
  border-radius: 4px;
}

table {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
  font-size: 14px;
}
table th, table td {
  border: 1px solid var(--border);
  padding: 6px 10px;
  text-align: left;
  vertical-align: top;
}
table th { background: var(--bg-soft); font-weight: 600; }
table tr:nth-child(2n) td { background: var(--bg-soft); }

/* Inline code */
code, kbd, samp {
  font-family:
    ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas,
    "Liberation Mono", "Courier New", monospace;
  font-size: 0.92em;
}
:not(pre) > code {
  background: var(--code-bg);
  border: 1px solid var(--code-border);
  border-radius: 4px;
  padding: 1px 5px;
}

/* Fenced code blocks */
pre {
  background: var(--code-bg);
  border: 1px solid var(--code-border);
  border-radius: 6px;
  padding: 12px 14px;
  overflow: auto;
  font-size: 13.5px;
  line-height: 1.55;
}
pre code { background: transparent; border: 0; padding: 0; }

/* Pygments wraps with .codehilite when codehilite extension is on */
.codehilite { background: var(--code-bg); border-radius: 6px; }

/* TOC */
.toc {
  background: var(--bg-soft);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 16px 24px;
  margin: 0 0 28px;
  font-size: 14px;
}
.toc::before {
  content: "目錄";
  display: block;
  font-weight: 600;
  font-size: 15px;
  margin-bottom: 6px;
  color: var(--fg);
}
.toc > ul { padding-left: 1.2em; }
.toc ul ul { padding-left: 1.2em; }
.toc li { margin: 0.18em 0; }

/* Admonition-ish blockquotes */
blockquote.note { border-left-color: var(--accent); }
blockquote.warn {
  background: var(--warn-bg);
  color: var(--warn-fg);
  border-left-color: var(--warn-border);
}

footer.doc-footer {
  margin-top: 64px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
  color: var(--fg-muted);
  font-size: 12px;
  text-align: center;
}

/* 列印 */
@media print {
  body { background: white; color: black; font-size: 11pt; }
  main { padding: 0 12mm; max-width: none; }
  pre, code { font-size: 9pt; }
  a { color: black; text-decoration: none; }
  a[href^="http"]::after { content: " (" attr(href) ")"; font-size: 9pt; color: #444; }
  h1 { page-break-before: always; }
  h1:first-of-type { page-break-before: auto; }
  .toc { page-break-after: always; }
}
""".strip()


# =====================================================================
# 主流程
# =====================================================================


def render_html(
    md_path: Path,
    out_path: Path,
    *,
    title: Optional[str] = None,
    enable_toc: bool = True,
) -> Path:
    """讀 markdown → 寫單檔 HTML。"""
    try:
        import markdown
    except ImportError as e:
        raise SystemExit(
            "[ERROR] 需要 markdown 套件：pip install markdown pygments"
        ) from e

    if not md_path.is_file():
        raise FileNotFoundError(md_path)

    md_text = md_path.read_text(encoding="utf-8")

    # 自動補目錄標記 (放在第一個 H1 之後)
    if enable_toc and "[TOC]" not in md_text:
        lines = md_text.splitlines()
        for i, line in enumerate(lines):
            if line.startswith("# "):
                lines.insert(i + 1, "")
                lines.insert(i + 2, "[TOC]")
                lines.insert(i + 3, "")
                break
        md_text = "\n".join(lines)

    extensions = [
        "extra",          # tables, fenced_code, def_list, abbr, attr_list, footnotes
        "sane_lists",
        "smarty",
        "admonition",
        "toc",
    ]
    extension_configs = {
        "toc": {"toc_depth": "2-4", "permalink": False, "title": ""},
    }

    # codehilite (pygments) 是可選依賴
    try:
        import pygments  # noqa: F401
        extensions.append("codehilite")
        extension_configs["codehilite"] = {
            "guess_lang": False,
            "css_class": "codehilite",
            "linenums": False,
        }
    except ImportError:
        pass  # 沒有 pygments 也能跑，只是不會有語法高亮

    md = markdown.Markdown(extensions=extensions,
                           extension_configs=extension_configs,
                           output_format="html5")
    body = md.convert(md_text)

    # Pygments inline CSS (兩種 colour scheme，靠 prefers-color-scheme 切換)
    pyg_css = ""
    try:
        from pygments.formatters import HtmlFormatter
        light = HtmlFormatter(style="default").get_style_defs(".codehilite")
        dark_raw = HtmlFormatter(style="monokai").get_style_defs(".codehilite")
        # 把暗色版包進 prefers-color-scheme: dark 的 media query
        pyg_css = (
            light
            + "\n@media (prefers-color-scheme: dark) {\n"
            + dark_raw
            + "\n}\n"
        )
    except ImportError:
        pass

    # 標題：取用 markdown.Meta 或 fallback 到 first H1 / 檔名
    if title is None:
        for line in md_text.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
        if title is None:
            title = md_path.stem

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    word_count = len(md_text)

    html_doc = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="generator" content="tiptoi_toolbox/generate_html.py">
<title>{html.escape(title)}</title>
<style>
{_BASE_CSS}
{pyg_css}
</style>
</head>
<body>
<main>
<header class="doc-header">
  <div class="crumbs">tiptoi_toolbox · 文件</div>
  <h1>{html.escape(title)}</h1>
  <div class="meta">由 generate_html.py 於 {now} 產生 ‧ 來源 {html.escape(md_path.name)} ‧ {word_count:,} 字元</div>
</header>

{body}

<footer class="doc-footer">
  generated from <code>{html.escape(md_path.name)}</code> by
  <code>tiptoi_toolbox/generate_html.py</code>
</footer>
</main>
</body>
</html>
"""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_doc, encoding="utf-8")
    return out_path


def main(argv=None) -> int:
    here = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(
        description="把 markdown 轉成單一檔案的 HTML 說明書",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--src", type=Path, default=here / DEFAULT_SRC,
        help=f"來源 markdown (預設：{DEFAULT_SRC})",
    )
    parser.add_argument(
        "--out", type=Path, default=here / DEFAULT_OUT,
        help=f"輸出 html (預設：{DEFAULT_OUT})",
    )
    parser.add_argument(
        "--title", type=str, default=None,
        help="HTML <title> (預設：第一個 H1)",
    )
    parser.add_argument(
        "--no-toc", action="store_true",
        help="不要自動插入目錄",
    )
    args = parser.parse_args(argv)

    out = render_html(
        md_path=args.src,
        out_path=args.out,
        title=args.title,
        enable_toc=not args.no_toc,
    )
    sz = out.stat().st_size
    print(f"[OK] {args.src} → {out}  ({sz:,} bytes / {sz / 1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
