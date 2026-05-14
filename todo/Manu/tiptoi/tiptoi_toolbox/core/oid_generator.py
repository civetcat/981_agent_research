# -*- coding: utf-8 -*-
"""
core/oid_generator.py
=====================

把一段連續的 OID 排成「方便用點讀筆測試」的 A4 PDF：

* 每頁 N 欄 (預設 5)，OID 之間至少留 ``gap_mm`` 公釐 (預設 20 mm = 2 cm)
* 第一頁頂部放標題 + 一個獨立的 *啟動碼* (預設 999)
* 每碼下方標 ``ID: <number>``

公開 API
--------

* :class:`GridConfig` - 排版/檔案路徑參數
* :func:`generate_grid_pdf(config)` - 一站式：(視需要) 跑 tttool → 排版 → 存 PDF

技術重點
~~~~~~~~

* OID PNG 嵌入時 **絕對不縮放**：以 1200 DPI 原解析度貼進 PDF，
  並把 x/y 對齊到 1200 DPI 整數像素網格 (避免次像素抖動)
* PIL 先把 ``LA`` 模式壓平成 ``mode='1'`` 1-bit，避開 ReportLab 對
  ``LA`` 影像的「LA → L + SMask」重新光柵化漂移問題
* 嵌入路徑走 ``ImageReader(pil)``，內部用 FlateDecode 無損 zlib
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from PIL import Image

from .utils import (
    OID_DPI,
    ensure_dir,
    find_tttool,
    register_chinese_font,
)

log = logging.getLogger(__name__)


# =====================================================================
# Config
# =====================================================================


@dataclass
class GridConfig:
    """OID 網格 PDF 的全部參數。"""

    # OID 範圍
    low: int = 1000
    high: int = 1100
    activation_oid: Optional[int] = 999    # None = 不畫頁首啟動碼
    product_id: int = 999                  # 只用在標題文字

    # 物理尺寸
    code_dim_mm: int = 20                  # OID 寬高 (mm)；1200 DPI 下會變 945 px
    cols: int = 5
    gap_mm: int = 20                       # 碼之間最小間距 (mm)，使用者規格 >= 2 cm
    page_margin_mm: int = 10
    label_font_size_pt: int = 11
    label_area_mm: int = 5

    # 路徑 (建議用相對 path)
    oid_dir: Path = Path("oid_codes")      # 暫存 OID PNG
    output_pdf: Path = Path("index_test.pdf")

    # 行為
    regenerate: bool = False               # True = 強制重跑 tttool
    title: Optional[str] = None            # None = 自動 "TipToi 測試索引頁 - 產品 ID: <pid>"
    subtitle: Optional[str] = None

    # 字型 (None = 自動偵測 CJK)
    chinese_font: Optional[str] = None

    @property
    def codes(self) -> List[int]:
        if self.high < self.low:
            return []
        return list(range(self.low, self.high + 1))

    @property
    def needed_codes(self) -> List[int]:
        c = list(self.codes)
        if self.activation_oid is not None and self.activation_oid not in c:
            c = [self.activation_oid] + c
        return c


# =====================================================================
# tttool 產生 / 讀取 OID PNG
# =====================================================================


def find_oid_png(oid_dir: Path, code: int) -> Optional[Path]:
    """tttool 預設輸出 ``oid-<N>.png``；同時容許無連字號版本。"""
    for name in (f"oid-{code}.png", f"oid{code}.png"):
        p = oid_dir / name
        if p.exists():
            return p
    return None


def ensure_oid_pngs(
    oid_dir: Path,
    codes: Sequence[int],
    code_dim_mm: int,
    *,
    tttool: Optional[str] = None,
    regenerate: bool = False,
) -> List[Tuple[int, Path]]:
    """
    確保 ``oid_dir`` 下對每個 ``codes`` 都存在 PNG；缺檔時呼叫 ``tttool``
    補上。回傳 ``[(code, path), ...]`` 已備齊的清單；找不到工具或失敗時
    回傳空 list。
    """
    ensure_dir(oid_dir)

    if regenerate:
        missing = list(codes)
    else:
        missing = [c for c in codes if find_oid_png(oid_dir, c) is None]

    if missing:
        if tttool is None:
            tttool = find_tttool()
        if tttool is None:
            log.error("缺少 %d 個 OID PNG 但找不到 tttool", len(missing))
            return []

        # 連續就用 1000-1100；不連續就逗號展開
        if len(missing) == (max(missing) - min(missing) + 1):
            range_arg = f"{min(missing)}-{max(missing)}"
        else:
            range_arg = ",".join(str(c) for c in missing)

        cmd = [
            tttool,
            "--dpi", str(OID_DPI),
            "--code-dim", f"{code_dim_mm}",
            "oid-code", range_arg,
        ]
        log.info("running: %s  (cwd=%s)", " ".join(cmd), oid_dir)
        result = subprocess.run(cmd, cwd=str(oid_dir),
                                capture_output=True, text=True)
        if result.returncode != 0:
            log.error("tttool failed (exit=%d):\n%s\n%s",
                      result.returncode, result.stdout, result.stderr)
            return []

    pairs: List[Tuple[int, Path]] = []
    for c in codes:
        p = find_oid_png(oid_dir, c)
        if p is None:
            log.error("tttool 跑完仍找不到 oid-%d.png", c)
            return []
        pairs.append((c, p))
    return pairs


# =====================================================================
# PIL 影像預處理：LA → 1-bit
# =====================================================================


def load_oid_as_bilevel(img_path: Path) -> Image.Image:
    """
    讀 OID PNG → 壓平成 ``mode='1'`` (白底 1-bit)。

    這是為了避開 ReportLab 對 ``LA`` 模式 PNG 的「LA → L + SMask」二次重新
    光柵化問題 (會造成 dot 邊緣亞像素漂移)。
    """
    im = Image.open(img_path)
    if im.mode in ("LA", "RGBA", "PA"):
        bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
        im = Image.alpha_composite(bg, im.convert("RGBA")).convert("L")
    elif im.mode != "1":
        im = im.convert("L")
    if im.mode != "1":
        im = im.point(lambda v: 0 if v < 128 else 255, mode="1")
    return im


def snap_to_pixel(pt: float, dpi: int = OID_DPI) -> float:
    """把 pt 座標對齊到指定 DPI 的整數像素網格。"""
    pt_per_px = 72.0 / dpi
    return round(pt / pt_per_px) * pt_per_px


# =====================================================================
# 主要 API
# =====================================================================


@dataclass
class GridResult:
    output_pdf: Path
    pages: int
    codes_total: int
    oid_pixel_size: Tuple[int, int]
    notes: List[str] = field(default_factory=list)


def generate_grid_pdf(config: GridConfig) -> GridResult:
    """
    依 ``config`` 產出 PDF 網格。回傳 :class:`GridResult`。

    呼叫前不需要先準備 OID PNG；本函式會在 ``config.oid_dir`` 下自動補。
    """
    # ReportLab 是「需要時才 import」，因為本模組(整個套件)其實不一定要 PDF
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import inch, mm
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas

    if config.high < config.low:
        raise ValueError("config.high 必須 >= config.low")

    notes: List[str] = []

    # ---- 1. OID 圖檔 -------------------------------------------------
    pairs = ensure_oid_pngs(
        oid_dir=config.oid_dir,
        codes=config.needed_codes,
        code_dim_mm=config.code_dim_mm,
        regenerate=config.regenerate,
    )
    if not pairs:
        raise RuntimeError("OID PNG 準備失敗 (找不到 tttool 或產生失敗)")

    # 拆出啟動碼 (若有)
    activation_img: Optional[Image.Image] = None
    if config.activation_oid is not None:
        for code, p in pairs:
            if code == config.activation_oid:
                activation_img = load_oid_as_bilevel(p)
                break
        grid_pairs = [(c, p) for c, p in pairs if c != config.activation_oid]
    else:
        grid_pairs = list(pairs)

    grid_imgs: List[Tuple[int, Image.Image]] = []
    px_w = px_h = 0
    for code, path in grid_pairs:
        im = load_oid_as_bilevel(path)
        if px_w == 0:
            px_w, px_h = im.size
        elif im.size != (px_w, px_h):
            notes.append(
                f"oid-{code}.png 尺寸 {im.size} 與其他不同 ({px_w}×{px_h})"
            )
        grid_imgs.append((code, im))
    if px_w == 0:
        # 沒有任何 grid OID (可能 only activation)；把 activation 尺寸當基準
        if activation_img is None:
            raise RuntimeError("沒有任何 OID 可排版")
        px_w, px_h = activation_img.size

    expected_px = round(config.code_dim_mm / 25.4 * OID_DPI)
    if abs(px_w - expected_px) > 1:
        notes.append(
            f"OID 像素 {px_w}×{px_h} 與理論 {expected_px}×{expected_px} 不符"
        )

    # ---- 2. 字型 ------------------------------------------------------
    if config.chinese_font:
        font_name = config.chinese_font
    else:
        font_name = register_chinese_font()

    # ---- 3. 排版幾何 -------------------------------------------------
    page_w_pt, page_h_pt = A4
    margin_pt = config.page_margin_mm * mm
    oid_pt = (px_w / OID_DPI) * inch
    cell_h_pt = oid_pt + (config.label_area_mm * mm)

    usable_w_pt = page_w_pt - 2 * margin_pt
    total_oid_w_pt = config.cols * oid_pt
    if total_oid_w_pt > usable_w_pt:
        raise ValueError(
            f"每列 {config.cols} × {config.code_dim_mm} mm = "
            f"{total_oid_w_pt / mm:.1f} mm > 可用寬 {usable_w_pt / mm:.1f} mm"
        )
    h_gap_pt = (usable_w_pt - total_oid_w_pt) / max(config.cols - 1, 1)
    if h_gap_pt < config.gap_mm * mm:
        raise ValueError(
            f"在 {config.code_dim_mm} mm OID + {config.gap_mm} mm 最小間距下，"
            f"A4 一列裝不下 {config.cols} 欄"
        )
    h_pitch_pt = oid_pt + h_gap_pt

    def rows_in_height(h_pt: float) -> int:
        # N 列實際高度 = N*cell_h + (N-1)*gap
        gap_pt = config.gap_mm * mm
        return max(0, int((h_pt + gap_pt) // (cell_h_pt + gap_pt)))

    # 估算頁首佔用
    header_reserve_pt = 0.0
    if config.activation_oid is not None and activation_img is not None:
        header_reserve_pt = (
            18                       # title font
            + 6 * mm
            + 10                     # subtitle font
            + 14 * mm
            + oid_pt
            + 5 * mm
            + 11                     # activation label font
            + 11 * mm
            + 6 * mm
        )
    page1_grid_h_pt = page_h_pt - margin_pt - header_reserve_pt - margin_pt - 12 * mm
    pageN_grid_h_pt = page_h_pt - 2 * margin_pt - 12 * mm

    rows_p1 = rows_in_height(page1_grid_h_pt) if header_reserve_pt > 0 else rows_in_height(pageN_grid_h_pt)
    rows_pn = rows_in_height(pageN_grid_h_pt)
    cells_p1 = rows_p1 * config.cols
    cells_pn = rows_pn * config.cols
    if cells_p1 == 0 or cells_pn == 0:
        raise ValueError("在目前的尺寸與間距下 A4 完全裝不下任何一列")

    # 切頁
    codes = [c for c, _ in grid_imgs]
    pages: List[List[int]] = []
    if codes:
        pages.append(codes[:cells_p1])
        rest = codes[cells_p1:]
        while rest:
            pages.append(rest[:cells_pn])
            rest = rest[cells_pn:]
    if not pages:
        pages = [[]]  # 至少一頁 (header-only)
    page_total = len(pages)

    # ---- 4. PDF -----------------------------------------------------
    ensure_dir(config.output_pdf.parent)
    c = canvas.Canvas(str(config.output_pdf), pagesize=A4)
    c.setTitle(f"tiptoi OID 測試索引 {config.low}-{config.high}")
    c.setAuthor("tiptoi_toolbox.core.oid_generator")
    c.setSubject(f"tiptoi 點讀筆 OID 識別測試 (Product ID {config.product_id})")

    title = config.title or f"TipToi 測試索引頁 - 產品 ID: {config.product_id}"
    subtitle = config.subtitle or (
        f"OID {config.low}–{config.high} (共 {len(codes)} 碼) ‧ "
        f"{config.code_dim_mm} mm @ {OID_DPI} DPI ‧ "
        "列印請選「實際大小 / 100% / 不縮放」"
    )

    for page_idx, page_codes in enumerate(pages, start=1):
        if page_idx == 1 and config.activation_oid is not None and activation_img is not None:
            grid_top_pt = _draw_header(
                c, page_w_pt, page_h_pt, margin_pt,
                activation_img, oid_pt, font_name,
                title=title, subtitle=subtitle,
                activation_oid=config.activation_oid,
            )
        else:
            c.setFont(font_name, 11)
            c.setFillColorRGB(0.3, 0.3, 0.3)
            c.drawString(
                margin_pt, page_h_pt - margin_pt - 4 * mm,
                f"OID 索引 (續) ‧ Product ID {config.product_id}",
            )
            grid_top_pt = page_h_pt - margin_pt - 9 * mm

        for slot, code in enumerate(page_codes):
            row = slot // config.cols
            col = slot % config.cols
            cell_x_pt = margin_pt + col * h_pitch_pt
            cell_y_pt = (
                grid_top_pt
                - row * (cell_h_pt + config.gap_mm * mm)
                - cell_h_pt
            )
            img = next(im for c_, im in grid_imgs if c_ == code)
            _draw_cell(
                c, img, cell_x_pt, cell_y_pt, oid_pt,
                f"ID: {code}", font_name, config.label_font_size_pt,
                config.label_area_mm,
            )

        _draw_footer(c, page_w_pt, margin_pt, font_name,
                     page_idx, page_total, config)
        c.showPage()

    c.save()
    return GridResult(
        output_pdf=config.output_pdf,
        pages=page_total,
        codes_total=len(codes) + (1 if config.activation_oid else 0),
        oid_pixel_size=(px_w, px_h),
        notes=notes,
    )


# =====================================================================
# 內部繪製函式
# =====================================================================


def _draw_cell(
    c, img, cell_x_pt, cell_y_pt, oid_pt,
    label_text, font_name, font_size, label_area_mm,
):
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader

    img_x = snap_to_pixel(cell_x_pt)
    img_y = snap_to_pixel(cell_y_pt + label_area_mm * mm)

    c.drawImage(
        ImageReader(img),
        img_x, img_y,
        width=oid_pt, height=oid_pt,
        preserveAspectRatio=False,
    )
    c.setStrokeColorRGB(0.78, 0.78, 0.78)
    c.setLineWidth(0.25)
    c.rect(img_x, img_y, oid_pt, oid_pt, stroke=1, fill=0)

    c.setFillColorRGB(0, 0, 0)
    c.setFont(font_name, font_size)
    c.drawCentredString(
        img_x + oid_pt / 2,
        cell_y_pt + 1.5 * mm,
        label_text,
    )


def _draw_header(
    c, page_w_pt, page_h_pt, margin_pt,
    activation_img, oid_pt, font_name,
    *, title, subtitle, activation_oid,
):
    from reportlab.lib.units import mm
    from reportlab.lib.utils import ImageReader

    title_y = page_h_pt - margin_pt - 6 * mm
    c.setFillColorRGB(0, 0, 0)
    c.setFont(font_name, 18)
    c.drawCentredString(page_w_pt / 2, title_y, title)

    c.setFont(font_name, 10)
    c.setFillColorRGB(0.25, 0.25, 0.25)
    c.drawCentredString(page_w_pt / 2, title_y - 6 * mm, subtitle)

    activation_y_top = title_y - 14 * mm
    img_y = snap_to_pixel(activation_y_top - oid_pt)
    img_x = snap_to_pixel((page_w_pt - oid_pt) / 2)

    c.drawImage(
        ImageReader(activation_img),
        img_x, img_y,
        width=oid_pt, height=oid_pt,
        preserveAspectRatio=False,
    )
    c.setStrokeColorRGB(0.55, 0.55, 0.55)
    c.setLineWidth(0.4)
    c.rect(img_x, img_y, oid_pt, oid_pt, stroke=1, fill=0)

    c.setFont(font_name, 11)
    c.setFillColorRGB(0, 0, 0)
    c.drawCentredString(
        page_w_pt / 2,
        img_y - 5 * mm,
        f"ID: {activation_oid}  (語系啟動碼 / Aktivierungscode)",
    )

    rule_y = img_y - 11 * mm
    c.setStrokeColorRGB(0.6, 0.6, 0.6)
    c.setLineWidth(0.5)
    c.line(margin_pt, rule_y, page_w_pt - margin_pt, rule_y)

    return rule_y - 6 * mm


def _draw_footer(c, page_w_pt, margin_pt, font_name,
                 page_idx, page_total, config: GridConfig):
    from reportlab.lib.units import mm
    c.setFont(font_name, 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    note = (
        f"列印：A4 100% 不縮放 ‧ 600 DPI 以上雷射印表機 ‧ "
        f"OID 物理 {config.code_dim_mm} mm, 間距 ≥ {config.gap_mm} mm"
    )
    c.drawString(margin_pt, 8 * mm, note)
    c.drawRightString(
        page_w_pt - margin_pt, 8 * mm,
        f"頁 {page_idx} / {page_total}",
    )


__all__ = [
    "GridConfig",
    "GridResult",
    "generate_grid_pdf",
    "ensure_oid_pngs",
    "find_oid_png",
    "load_oid_as_bilevel",
    "snap_to_pixel",
]
