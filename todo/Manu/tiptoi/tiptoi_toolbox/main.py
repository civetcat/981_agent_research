#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tiptoi_toolbox / main.py
========================

統一的 CLI 進入點。所有功能都透過 ``--task <name>`` 派發：

  * ``init``     — 把 templates/default_config.yaml 複製到 ``--dst``
  * ``convert``  — 掃 mp3 → 轉 ogg → 寫 yaml → (可選) tttool assemble
  * ``assemble`` — 只跑 tttool assemble (給已經有 yaml + ogg 的情境)
  * ``grid``     — 產出 OID 測試網格 PDF
  * ``all``      — convert + grid (完整 pipeline)
  * ``info``     — 顯示偵測到的工具、字型、套件版本

最少參數示範：

    python main.py --task init     --dst ./my_project
    python main.py --task convert  --src ./audio/src
    python main.py --task assemble --yaml ./audio/test.yaml
    python main.py --task grid     --low 1000 --high 1100
    python main.py --task all      --src ./audio/src --low 1000 --high 1100

含設定檔：

    python main.py --config ./my_project/default_config.yaml --task all

YAML 內的相對路徑會自動以 **設定檔所在目錄** 為基準。
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# 讓三種呼叫方式都可運作 (而且 **不要求** 父目錄叫 tiptoi_toolbox)：
#   1. python main.py                                  (script，cwd 任意)
#   2. python /path/to/tiptoi_toolbox/main.py          (script，跨目錄)
#   3. python -m tiptoi_toolbox.main                   (module，要求父目錄是 import path)
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from core import audio_processor as ap  # noqa: E402
    from core import oid_generator as og    # noqa: E402
    from core import utils                  # noqa: E402
else:
    from .core import audio_processor as ap
    from .core import oid_generator as og
    from .core import utils


# =====================================================================
# Config loader
# =====================================================================


def _load_config(config_path: Optional[Path]) -> Dict[str, Any]:
    """讀 YAML 設定檔；若路徑為 None 回傳 {}。"""
    if config_path is None:
        return {}
    try:
        import yaml  # PyYAML
    except ImportError:
        sys.stderr.write(
            "[ERROR] 使用 --config 需要 PyYAML，請先安裝：pip install pyyaml\n"
        )
        sys.exit(2)
    if not config_path.is_file():
        sys.stderr.write(f"[ERROR] 找不到設定檔: {config_path}\n")
        sys.exit(2)
    with config_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    return cfg


def _resolve_rel(base: Path, value: Optional[str]) -> Optional[Path]:
    """把 cfg 內的字串路徑接到 base；None 維持 None；絕對路徑保留。"""
    if value is None:
        return None
    p = Path(value)
    if not p.is_absolute():
        p = (base / p).resolve()
    return p


# =====================================================================
# Tasks
# =====================================================================


def task_init(args: argparse.Namespace) -> int:
    """複製 templates/default_config.yaml 到 --dst。"""
    src = utils.template_path("default_config.yaml")
    dst_dir: Path = args.dst.resolve()
    dst_dir.mkdir(parents=True, exist_ok=True)
    dst_file = dst_dir / "default_config.yaml"
    if dst_file.exists() and not args.force:
        print(f"[SKIP] {dst_file} 已存在 (--force 可覆寫)")
        return 0
    shutil.copyfile(src, dst_file)
    print(f"[OK] 已複製 {src.name} → {dst_file}")
    print("\n下一步：")
    print(f"  1. 編輯  {dst_file}")
    print(f"  2. 在該目錄放好 audio/src/*.mp3")
    print(f"  3. python {Path(__file__).name} "
          f"--config {dst_file} --task all")
    return 0


def task_info(args: argparse.Namespace) -> int:
    """顯示工具與環境的偵測結果。"""
    print("=" * 70)
    print("tiptoi_toolbox 環境檢查")
    print("=" * 70)
    print(f"  Python:       {sys.version.split()[0]}")
    print(f"  Package root: {utils.package_root()}")

    ffmpeg = utils.find_ffmpeg()
    tttool = utils.find_tttool()
    font = utils.find_chinese_font()
    print(f"  ffmpeg:       {ffmpeg or '(NOT FOUND)'}")
    print(f"  tttool:       {tttool or '(NOT FOUND)'}")
    print(f"  CJK font:     {font or '(NOT FOUND, will fall back to Helvetica)'}")

    for mod in ("PIL", "reportlab", "yaml", "markdown", "pygments"):
        try:
            __import__(mod)
            ver = getattr(sys.modules[mod], "__version__", "?")
            mark = "OK"
        except ImportError:
            ver = "(not installed)"
            mark = "--"
        print(f"  [{mark}] {mod:<12s} {ver}")
    return 0


def task_convert(args: argparse.Namespace, cfg: Dict[str, Any], cfg_base: Path) -> int:
    """跑完整的 convert + yaml + (assemble) 流程。"""
    audio_cfg = cfg.get("audio", {}) or {}
    gme_cfg = cfg.get("gme", {}) or {}
    project_cfg = cfg.get("project", {}) or {}

    src = (
        args.src
        or _resolve_rel(cfg_base, audio_cfg.get("src_dir"))
    )
    if src is None:
        sys.stderr.write("[ERROR] 請用 --src 指定 mp3 目錄 (或在 config 裡填 audio.src_dir)\n")
        return 2
    src = Path(src).resolve()

    out = (
        args.out
        or _resolve_rel(cfg_base, audio_cfg.get("out_dir"))
        or src.parent
    )
    out = Path(out).resolve()

    yaml_path = (
        args.yaml
        or _resolve_rel(cfg_base, gme_cfg.get("yaml"))
        or out / "test.yaml"
    ).resolve() if (args.yaml or gme_cfg.get("yaml")) else (out / "test.yaml").resolve()

    gme_path = (
        args.gme
        or _resolve_rel(cfg_base, gme_cfg.get("output"))
        or yaml_path.with_suffix(".gme")
    ).resolve() if (args.gme or gme_cfg.get("output")) else yaml_path.with_suffix(".gme")

    start_oid = args.start_oid or audio_cfg.get("start_oid", 1000)
    product_id = args.product_id or project_cfg.get("product_id", 999)
    quality = args.quality or audio_cfg.get("quality", utils.AUDIO_QUALITY_DEFAULT)
    overwrite = audio_cfg.get("overwrite", True) and not args.no_overwrite
    assemble = (gme_cfg.get("assemble", True) and not args.no_assemble)

    print("=" * 70)
    print("[convert]  mp3 → ogg vorbis → yaml → (assemble)")
    print("=" * 70)
    print(f"  src:        {src}")
    print(f"  out:        {out}")
    print(f"  yaml:       {yaml_path}")
    print(f"  gme:        {gme_path}")
    print(f"  start_oid:  {start_oid}")
    print(f"  product_id: {product_id}")
    print(f"  quality:    -q:a {quality}  ({utils.AUDIO_CODEC} mono "
          f"{utils.AUDIO_SAMPLE_RATE}Hz)")

    mp3_files = ap.scan_mp3(src)
    if not mp3_files:
        sys.stderr.write(f"[ERROR] {src} 內沒有 .mp3\n")
        return 1

    def progress(i, total, fr):
        mark = "OK  " if fr.ok else "FAIL"
        print(f"  [{i:>3}/{total}] {fr.src.name:<32s} → "
              f"OID {fr.oid} → {fr.dst.name:<14s} {mark}  {fr.message}")

    result = ap.convert_directory(
        src_dir=src, out_dir=out,
        start_oid=start_oid, product_id=product_id,
        yaml_path=yaml_path, gme_path=gme_path,
        overwrite=overwrite, quality=quality, assemble=assemble,
        on_progress=progress,
    )

    print("")
    print(f"  轉檔成功: {len(result.successes)} / {len(result.files)}")
    if result.failures:
        print(f"  轉檔失敗: {len(result.failures)}")
        for fr in result.failures:
            print(f"    - {fr.src.name}: {fr.message}")

    if result.yaml_path:
        print(f"  YAML:    {result.yaml_path}  "
              f"({utils.humanize_size(result.yaml_path.stat().st_size)})")

    if assemble:
        if result.assemble_ok:
            sz = utils.humanize_size(result.gme_path.stat().st_size)
            print(f"  GME:     {result.gme_path}  ({sz})")
        else:
            print(f"  [WARN] tttool assemble 失敗或未執行：")
            for line in result.assemble_log.strip().splitlines():
                print(f"         | {line}")
            if result.successes:
                return 1
    return 0 if not result.failures else 2


def task_assemble(args: argparse.Namespace, cfg: Dict[str, Any], cfg_base: Path) -> int:
    """只跑 tttool assemble。"""
    gme_cfg = cfg.get("gme", {}) or {}
    yaml_path = (
        args.yaml
        or _resolve_rel(cfg_base, gme_cfg.get("yaml"))
    )
    if yaml_path is None:
        sys.stderr.write("[ERROR] 請用 --yaml 指定 yaml 路徑\n")
        return 2
    yaml_path = Path(yaml_path).resolve()
    gme_path = (
        args.gme
        or _resolve_rel(cfg_base, gme_cfg.get("output"))
        or yaml_path.with_suffix(".gme")
    )
    gme_path = Path(gme_path).resolve()

    print("=" * 70)
    print(f"[assemble]  {yaml_path.name} → {gme_path.name}")
    print("=" * 70)
    print(f"  cwd: {yaml_path.parent}")

    ok, log, gme = ap.run_tttool_assemble(yaml_path, gme_path)
    for line in log.strip().splitlines():
        print(f"  | {line}")
    if not ok:
        sys.stderr.write("[ERROR] tttool assemble 失敗\n")
        return 1
    print(f"\n  GME: {gme}  ({utils.humanize_size(gme.stat().st_size)})")
    return 0


def task_grid(args: argparse.Namespace, cfg: Dict[str, Any], cfg_base: Path) -> int:
    """產出 OID 網格 PDF。"""
    grid_cfg = cfg.get("oid_grid", {}) or {}
    project_cfg = cfg.get("project", {}) or {}

    cfg_obj = og.GridConfig(
        low=args.low or grid_cfg.get("low", 1000),
        high=args.high or grid_cfg.get("high", 1100),
        activation_oid=(args.activation_oid
                        if args.activation_oid is not None
                        else grid_cfg.get("activation_oid", 999)),
        product_id=args.product_id or project_cfg.get("product_id", 999),
        code_dim_mm=args.code_dim or grid_cfg.get("code_dim_mm", 20),
        cols=args.cols or grid_cfg.get("cols", 5),
        gap_mm=args.gap_mm or grid_cfg.get("gap_mm", 20),
        oid_dir=Path(
            args.oid_dir
            or _resolve_rel(cfg_base, grid_cfg.get("oid_dir"))
            or "oid_codes_grid"
        ),
        output_pdf=Path(
            args.out
            or _resolve_rel(cfg_base, grid_cfg.get("output_pdf"))
            or "index_test.pdf"
        ),
        regenerate=args.regenerate or grid_cfg.get("regenerate", False),
    )

    print("=" * 70)
    print(f"[grid]  OID {cfg_obj.low}..{cfg_obj.high}  → {cfg_obj.output_pdf}")
    print("=" * 70)
    print(f"  oid_dir:    {cfg_obj.oid_dir}")
    print(f"  code_dim:   {cfg_obj.code_dim_mm} mm @ {utils.OID_DPI} DPI")
    print(f"  layout:     {cfg_obj.cols} 欄 × N 列, 間距 ≥ {cfg_obj.gap_mm} mm")
    print(f"  activation: {cfg_obj.activation_oid}")

    result = og.generate_grid_pdf(cfg_obj)

    sz = utils.humanize_size(result.output_pdf.stat().st_size)
    print(f"\n  完成: {result.output_pdf}  ({sz})")
    print(f"  頁數: {result.pages}")
    print(f"  OID 像素: {result.oid_pixel_size[0]}×{result.oid_pixel_size[1]}")
    for n in result.notes:
        print(f"  [NOTE] {n}")
    return 0


def task_all(args: argparse.Namespace, cfg: Dict[str, Any], cfg_base: Path) -> int:
    """完整 pipeline：先 convert，再 grid。"""
    rc1 = task_convert(args, cfg, cfg_base)
    if rc1 == 1:
        sys.stderr.write("[ERROR] convert 失敗，跳過 grid\n")
        return rc1
    print("")
    rc2 = task_grid(args, cfg, cfg_base)
    return rc2 if rc2 != 0 else rc1


# =====================================================================
# Argparse
# =====================================================================


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tiptoi_toolbox",
        description=(
            "統一的 tiptoi 工作流 CLI。\n"
            "用 --task 指定要做什麼；--config 可選讀 YAML 設定。"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument(
        "--task", required=True,
        choices=["init", "info", "convert", "assemble", "grid", "all"],
        help="要執行的任務",
    )
    p.add_argument(
        "--config", type=Path, default=None,
        help="(可選) YAML 設定檔；CLI 旗標永遠勝過 YAML",
    )

    g = p.add_argument_group("init / 設定範本")
    g.add_argument("--dst", type=Path, default=Path("."),
                   help="init 任務複製範本的目的地目錄")
    g.add_argument("--force", action="store_true",
                   help="init: 若已存在 default_config.yaml 則覆寫")

    g = p.add_argument_group("convert / assemble")
    g.add_argument("--src", type=Path, default=None,
                   help="mp3 來源目錄")
    g.add_argument("--out", type=Path, default=None,
                   help="(convert) ogg 輸出目錄；(grid) PDF 輸出路徑")
    g.add_argument("--start-oid", type=int, default=None,
                   help="convert 起始 OID (預設 1000)")
    g.add_argument("--product-id", type=int, default=None,
                   help="GME product-id (預設 999)")
    g.add_argument("--yaml", type=Path, default=None,
                   help="YAML 路徑 (convert 寫入 / assemble 讀取)")
    g.add_argument("--gme", type=Path, default=None,
                   help="GME 路徑")
    g.add_argument("--no-assemble", action="store_true",
                   help="convert 完不執行 tttool assemble")
    g.add_argument("--no-overwrite", action="store_true",
                   help="convert 時若 ogg 已存在則跳過")
    g.add_argument("--quality", type=int, default=None,
                   help="libvorbis -q:a (0..10, 預設 3)")

    g = p.add_argument_group("grid")
    g.add_argument("--low", type=int, default=None, help="OID 起 (含)")
    g.add_argument("--high", type=int, default=None, help="OID 迄 (含)")
    g.add_argument("--cols", type=int, default=None, help="每列欄數")
    g.add_argument("--code-dim", type=int, default=None, help="OID 邊長 (mm)")
    g.add_argument("--gap-mm", type=int, default=None, help="OID 之間最小間距 (mm)")
    g.add_argument("--oid-dir", type=Path, default=None, help="OID PNG 暫存目錄")
    g.add_argument("--activation-oid", type=int, default=None,
                   help="頁首啟動碼；0 = 關掉")
    g.add_argument("--regenerate", action="store_true",
                   help="grid: 強制重跑 tttool 重產 OID PNG")

    return p


# =====================================================================
# Entry
# =====================================================================


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.INFO,
        format="[%(levelname)s] %(name)s: %(message)s",
    )

    # activation_oid: 允許 0 關掉
    if args.activation_oid == 0:
        args.activation_oid = None

    # config 路徑與 base
    cfg = _load_config(args.config)
    cfg_base = args.config.parent.resolve() if args.config else Path.cwd()

    if args.task == "init":
        return task_init(args)
    if args.task == "info":
        return task_info(args)
    if args.task == "convert":
        return task_convert(args, cfg, cfg_base)
    if args.task == "assemble":
        return task_assemble(args, cfg, cfg_base)
    if args.task == "grid":
        return task_grid(args, cfg, cfg_base)
    if args.task == "all":
        return task_all(args, cfg, cfg_base)

    sys.stderr.write(f"[ERROR] 未知 task: {args.task}\n")
    return 2


if __name__ == "__main__":
    sys.exit(main())
