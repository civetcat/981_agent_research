# -*- coding: utf-8 -*-
"""
core/utils.py
=============

可重用的小工具：

* External-binary discovery (`ffmpeg`, `tttool`)
* Chinese-font discovery + ReportLab registration
* Path/file helpers (humanize size, atomic mkdir, …)
* Constants shared across the toolbox

所有路徑皆為相對 / 由參數帶入；本模組 **不寫死** 任何絕對路徑，
也不依賴任何環境變數，可以直接搬到別台機器。
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Iterable, List, Optional

# =====================================================================
# 共用常數 (tiptoi 規格)
# =====================================================================

OID_DPI = 1200                       # tttool 預設輸出解析度
AUDIO_CODEC = "libvorbis"            # tiptoi OGG 容器內必需
AUDIO_CHANNELS = 1                   # mono
AUDIO_SAMPLE_RATE = 22050            # Hz
AUDIO_QUALITY_DEFAULT = 3            # libvorbis -q:a (0..10)

# =====================================================================
# 候選工具路徑：依平台 + 常見安裝位置順序嘗試
#   - 純檔名 → 走 PATH (shutil.which)
#   - 含 / 的路徑 → 直接檢查可執行
# =====================================================================

FFMPEG_CANDIDATES: List[str] = [
    "ffmpeg",
    "/usr/bin/ffmpeg",
    "/usr/local/bin/ffmpeg",
    "/opt/homebrew/bin/ffmpeg",
    "C:/ffmpeg/bin/ffmpeg.exe",
]

TTTOOL_CANDIDATES: List[str] = [
    "tttool",
    os.path.expanduser("~/bin/tttool"),
    os.path.expanduser("~/.local/bin/tttool"),
    os.path.expanduser("~/opt/tttool-1.11/tttool"),
    os.path.expanduser("~/opt/tttool/tttool"),
    "/usr/local/bin/tttool",
    "/opt/tttool/tttool",
]

# 常見 CJK TrueType / TrueType-Collection 字型
CHINESE_FONT_CANDIDATES: List[str] = [
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "C:/Windows/Fonts/msjh.ttc",
    "C:/Windows/Fonts/mingliu.ttc",
]


# =====================================================================
# Helpers
# =====================================================================


def find_tool(candidates: Iterable[str]) -> Optional[str]:
    """
    回傳第一個可執行的工具路徑；找不到回 None。

    >>> find_tool(["ls"]) is not None
    True
    """
    for cand in candidates:
        if "/" in cand or "\\" in cand:
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        else:
            found = shutil.which(cand)
            if found:
                return found
    return None


def find_ffmpeg() -> Optional[str]:
    """快捷：找 ffmpeg。"""
    return find_tool(FFMPEG_CANDIDATES)


def find_tttool() -> Optional[str]:
    """快捷：找 tttool。"""
    return find_tool(TTTOOL_CANDIDATES)


def find_chinese_font() -> Optional[str]:
    """回傳第一個存在的 CJK 字型檔；找不到回 None。"""
    for path in CHINESE_FONT_CANDIDATES:
        if os.path.isfile(path):
            return path
    return None


def register_chinese_font(font_name: str = "ChineseFont") -> str:
    """
    嘗試把第一支可用 CJK 字型註冊進 ReportLab。
    回傳字型名 (`font_name` 或 fallback `"Helvetica"`)。

    這個函式只在被呼叫時才 import reportlab，方便不依賴 PDF 的子任務
    (例如音檔轉檔) 不必背 reportlab。
    """
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    path = find_chinese_font()
    if path is None:
        return "Helvetica"
    try:
        pdfmetrics.registerFont(TTFont(font_name, path, subfontIndex=0))
        return font_name
    except Exception:  # noqa: BLE001 — 字型載入失敗就降級到 Helvetica
        return "Helvetica"


def humanize_size(n: int) -> str:
    """1234567 → '1.18 MB'。"""
    if n < 1024:
        return f"{n} B"
    f = float(n)
    for unit in ("KB", "MB", "GB"):
        f /= 1024.0
        if f < 1024:
            return f"{f:.2f} {unit}"
    return f"{f:.2f} TB"


def ensure_dir(path: Path) -> Path:
    """mkdir -p，回傳同一個路徑物件。"""
    path.mkdir(parents=True, exist_ok=True)
    return path


def package_root() -> Path:
    """
    回傳 `tiptoi_toolbox/` 根目錄 (= 本檔案所在目錄的上一層)。

    任何想引用 `templates/` 內預設檔案的程式碼，都應該透過這個函式
    取得相對路徑，而 **不要** 假設工作目錄。
    """
    return Path(__file__).resolve().parent.parent


def template_path(name: str) -> Path:
    """回傳 `templates/<name>` 的絕對路徑 (但相對 package 根)。"""
    return package_root() / "templates" / name


__all__ = [
    "OID_DPI",
    "AUDIO_CODEC",
    "AUDIO_CHANNELS",
    "AUDIO_SAMPLE_RATE",
    "AUDIO_QUALITY_DEFAULT",
    "FFMPEG_CANDIDATES",
    "TTTOOL_CANDIDATES",
    "CHINESE_FONT_CANDIDATES",
    "find_tool",
    "find_ffmpeg",
    "find_tttool",
    "find_chinese_font",
    "register_chinese_font",
    "humanize_size",
    "ensure_dir",
    "package_root",
    "template_path",
]
