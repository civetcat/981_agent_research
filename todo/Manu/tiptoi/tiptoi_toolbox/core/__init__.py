# -*- coding: utf-8 -*-
"""
tiptoi_toolbox.core
===================

Programmatic API.  典型用法：

    from tiptoi_toolbox.core.audio_processor import convert_directory
    from tiptoi_toolbox.core.oid_generator import generate_grid_pdf

每個子模組也可以單檔被 import 而不會 side-effect 觸發其他模組
(例如不會強制載 reportlab，除非你要做 PDF)。
"""

from .utils import (
    AUDIO_CHANNELS,
    AUDIO_CODEC,
    AUDIO_QUALITY_DEFAULT,
    AUDIO_SAMPLE_RATE,
    OID_DPI,
    ensure_dir,
    find_ffmpeg,
    find_tttool,
    humanize_size,
    package_root,
    template_path,
)

__all__ = [
    "AUDIO_CHANNELS",
    "AUDIO_CODEC",
    "AUDIO_QUALITY_DEFAULT",
    "AUDIO_SAMPLE_RATE",
    "OID_DPI",
    "ensure_dir",
    "find_ffmpeg",
    "find_tttool",
    "humanize_size",
    "package_root",
    "template_path",
]

__version__ = "0.1.0"
