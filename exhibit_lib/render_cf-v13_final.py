#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
render_cf-v13.py — 碳纤维结构图 ASE 渲染器（论文级 ROI 环网络图优化版）

功能：
  1. 读取 ASE 支持的原子结构文件（xyz、extxyz、cif、POSCAR、traj 等）
  2. PCA 对齐 → 投影生成 Front / Top / Side 三视图（可跳过）
  3. 可选组合三视图面板（board）
  4. 可选局部放大图：用颜色标注 5/6/7 元环，Z 深度分层控制表面环数量

依赖性：
  pip install ase numpy pillow imageio

=============================================================================
基础用法
=============================================================================

  # 默认渲染：三视图 + board + 环放大图
  python render_cf-v13.py opted.xyz

  # 只出环放大图（跳过三视图和 board，省时间）
  python render_cf-v13.py opted.xyz --no-views --no-board

=============================================================================
环放大图核心参数详解
=============================================================================

以下为实际使用场景的最常用命令：

  python render_cf-v13.py opted.xyz --style emerald_paper --atom-style dense_fiber \\
      --no-views --no-board \\
      --ring-max-local-atoms 800 --ring-max-degree 4 \\
      --ring-n-layers 16 --ring-show-layers 1 \\
      --layer-opacity-boost 0.30 \\
      --zoom-box 0.512 0.645 0.578 0.715

参数分组说明：

────────────────────────────────────────────────────────────────────────
【必选参数】
────────────────────────────────────────────────────────────────────────

  structure                 ASE 可读的结构文件（默认: opted.xyz）

────────────────────────────────────────────────────────────────────────
【样式选择】
────────────────────────────────────────────────────────────────────────

  --style <name>            配色预设，可选: emerald_paper, paper_green,
                            professional_black, publication 等
                            默认: emerald_paper（翠绿论文风格）

  --atom-style <name>       原子渲染风格，可选: dense_fiber, balanced,
                            bold_balls 等
                            默认: dense_fiber（密实纤维风）

────────────────────────────────────────────────────────────────────────
【ROI（放大区域）控制】
────────────────────────────────────────────────────────────────────────

  --zoom-box X0 Y0 X1 Y1   归一化坐标 ROI 框 [0,1]×[0,1]。
                            例如 --zoom-box 0.512 0.645 0.578 0.715
                            表示选取 front 视图中 (51.2%, 64.5%) 至
                            (57.8%, 71.5%) 的矩形区域进行放大。
                            这四个值通常通过交互式预览确定。

────────────────────────────────────────────────────────────────────────
【碳网络图控制】—— 影响环的检测范围
────────────────────────────────────────────────────────────────────────

  --ring-max-local-atoms N  局部环检测的最大碳原子数（默认: 1600）。
                            越大检测范围越广，但越慢。
                            若 ROI 内原子很多，可增大此值保证完整覆盖。
                            常用值: 600–2000

  --ring-max-degree N       每个碳原子最多保留 N 根 C-C 键（默认: 4）。
                            碳网 sp² 碳的正常度数为 3，缺陷处有时为 4。
                            减小到 3 可让图更稀疏、找环更快；
                            增大到 5–6 可捕获更多连接，但 DFS 可能变慢。
                            最常用值: 3（稀疏）或 4（默认）

  --ring-cutoff-scale N     C-C 键截断系数（默认: 1.22）。
                            ASE 在 d < 2 × 共价半径 × scale 时连键。
                            一般无需改动。可调范围 1.10–1.30。

  --ring-roi-margin-px N    ROI 边界外扩像素（默认: 120）。
                            外扩越大，检测到的环越完整。

  --ring-max-cycles-per-size N
                            每种环大小最大检测数量（默认: 120）。
                            在原子密集区域可适当增大。

────────────────────────────────────────────────────────────────────────
【Z 深度分层控制】—— 控制展示哪几层环，最常用调节参数
────────────────────────────────────────────────────────────────────────

  --ring-n-layers N         Z 深度等分成多少层（默认: 3）。
                            把从 Z_min 到 Z_max 的环平均 Z 深度均匀分段。
                            层数越多，每层的 Z 跨度越薄。
                            常用值: 6–16

  --ring-show-layers N      展示前 N 层环（默认: 1）。
                            0 = 展示全部层。
                            典型用法:
                              --ring-n-layers 16 --ring-show-layers 1
                              → 分 16 层，只看最表面的前 1 层
                              → 即只展示 Z 最浅的 1/16 的环
                              分层越细，表面筛选越精确。

  Z_min  ─┬── layer 0 ──┐  ← show (ring-show-layers=1)
          ├── layer 1   │
          ├── layer 2   │
          ├── layer 3   │
          ├── ...       │  (ring-n-layers=16)
          └── layer 15 ─┘
  Z_max

  调整指南:
    - 表面只有 1–2 层环 → ring-n-layers=5, ring-show-layers=1
    - 表面有 3–4 层环重叠 → ring-n-layers=16, ring-show-layers=2 或 3
    - 想看全部环 → ring-show-layers=0
    - 只要最薄一层表面 → ring-n-layers=16, ring-show-layers=1

────────────────────────────────────────────────────────────────────────
【视觉微调】
────────────────────────────────────────────────────────────────────────

  --layer-opacity-boost N   原子层透明度增量（默认: 0.15 = +15%）。
                            放大图中原子通常较暗，此参数可整体提亮。
                            常用值: 0.10–0.40，越大越亮。

  --ring-layer-alpha-falloff N
                            逐层透明度衰减系数（默认: 1.0 = 无衰减）。
                            每深入一层，环键/环原子的 alpha 乘以该系数。
                            例如 --ring-layer-alpha-falloff 0.6：
                              layer 0: alpha = 200 × 1.0  = 200
                              layer 1: alpha = 200 × 0.6  = 120
                              layer 2: alpha = 200 × 0.36 =   72
                            这样深层环更淡，不会把表面层淹没。
                            范围 0.0–1.0，推荐 0.5–0.8。

  --ring-layer-scale-falloff N
                            逐层尺寸衰减系数（默认: 1.0 = 无衰减）。
                            每深入一层，环键宽度和环原子半径等比缩小。
                            配合 alpha 衰减使用，产生强烈的立体纵深感。

  --ring-zoom-scale N        右图（环放大图）缩放系数（默认: 1.0）。
                            右图宽高比始终与 --zoom-box 的宽高比一致。
                            减小该值可让右图整体变小，增大则变大。
                            范围 0.2–3.0，推荐 0.7–1.2。
                            例如 --ring-layer-scale-falloff 0.8：
                              layer 0: 100% 大小（表面最清晰）
                              layer 1: 80%  大小
                              layer 2: 64%  大小

  --ring-auto-roi           如果选定的 ROI 内没有检测到 5/6/7 元环，
                            自动尝试附近其他 ROI。

────────────────────────────────────────────────────────────────────────
【输出控制】
────────────────────────────────────────────────────────────────────────

  --no-views                跳过单张 Front / Top / Side PNG
  --no-board                跳过组合三视图面板
  --gif                     渲染旋转 GIF（较慢，默认关闭）
  --out-dir <path>          输出目录（默认: carbon_render_output_ase）

=============================================================================
快速参考
=============================================================================

  1) 快速调试环检测：
     python render_cf-v13.py opted.xyz --no-views --no-board \\
         --zoom-box 0.512 0.645 0.578 0.715

  2) 仅表面一层环（最干净）：
     python render_cf-v13.py opted.xyz --no-views --no-board \\
         --ring-n-layers 16 --ring-show-layers 1 \\
         --ring-max-degree 3 --ring-max-local-atoms 800 \\
         --layer-opacity-boost 0.30 \\
         --zoom-box 0.512 0.645 0.578 0.715

  3) 展示前两层环：
     python render_cf-v13.py opted.xyz --no-views --no-board \\
         --ring-n-layers 16 --ring-show-layers 2 \\
         --ring-max-degree 4 --ring-max-local-atoms 1200 \\
         --layer-opacity-boost 0.20 \\
         --zoom-box 0.512 0.645 0.578 0.715
"""

import argparse
import math
from pathlib import Path
from collections import defaultdict, deque

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
import imageio.v2 as imageio

from ase.io import read
from ase.data import atomic_numbers, covalent_radii
from ase.data.colors import jmol_colors
from ase.neighborlist import neighbor_list


# =============================================================================
# 1. Default settings
# =============================================================================

OUT_DIR = Path("carbon_render_output_ase")

ASE_READ_INDEX = -1

RENDER_THREE_VIEWS = True
RENDER_BOARD = True
RENDER_GIF = False
RENDER_RING_ZOOM = True

GIF_NAME = "carbon_rotating_ase.gif"
THREE_VIEW_NAME = "carbon_three_views_ase.png"
RING_ZOOM_NAME = "front_view_ring_zoom_ase.png"

# Ring-detection performance controls.
# The v6 script detected rings on the full graph, which can explode on large carbon networks.
# v7 detects rings only inside the selected front-view ROI plus a small margin.
RING_CUTOFF_SCALE_DEFAULT = 1.22
RING_ROI_MARGIN_PX_DEFAULT = 120
RING_MAX_LOCAL_ATOMS_DEFAULT = 750
RING_MAX_DEGREE_DEFAULT = 3
RING_MAX_CYCLES_PER_SIZE_DEFAULT = 120
RING_N_LAYERS_DEFAULT = 20
RING_SHOW_LAYERS_DEFAULT = 5
RING_LAYER_ALPHA_FALLOFF_DEFAULT = 0.74
RING_LAYER_SCALE_FALLOFF_DEFAULT = 0.96

FRAME_COUNT = 72
GIF_SIZE = (900, 900)
VIEW_SIZE = (1200, 900)
RING_FIGURE_SCALE = 1.50
RING_ZOOM_SCALE_DEFAULT = 0.95

GIF_DURATION = 0.055
GIF_TILT_X = -14
ZOOM = 0.76

PCA_ALIGN = True
AXIS_PERM = [1, 0, 2]

MAX_POINTS = 70000


# =============================================================================
# 2. Style settings
# =============================================================================

ACTIVE_STYLE = "emerald_paper"

STYLE_PRESETS = {
    "paper_green": {
        "white_bg": True,
        "board_bg": "#FFFFFF",

        "carbon_dark": "#19461E",
        "carbon_mid": "#38A271",
        "carbon_highlight": "#D2FAAA",

        "glow_color": "#64AF55",

        "title_color": "#282D32",
        "sub_color": "#78828C",

        "title_alpha": 240,
        "sub_alpha": 220,
    },

    "dark_graphite": {
        "white_bg": False,
        "board_bg": "#080A0D",

        "carbon_dark": "#121417",
        "carbon_mid": "#505860",
        "carbon_highlight": "#D2E0E8",

        "glow_color": "#7896AA",

        "title_color": "#EBF2F8",
        "sub_color": "#A0ACB8",

        "title_alpha": 240,
        "sub_alpha": 220,
    },

    "blue_carbon": {
        "white_bg": False,
        "board_bg": "#05080E",

        "carbon_dark": "#0F1E30",
        "carbon_mid": "#3778AA",
        "carbon_highlight": "#B4E6FF",

        "glow_color": "#4696DC",

        "title_color": "#EBF5FF",
        "sub_color": "#96B4CD",

        "title_alpha": 240,
        "sub_alpha": 220,
    },

    "paper_clean": {
        "white_bg": True,
        "board_bg": "#FFFFFF",

        "carbon_dark": "#263326",
        "carbon_mid": "#6A8F5F",
        "carbon_highlight": "#D8E8CC",

        "glow_color": "#7DA870",

        "title_color": "#20242A",
        "sub_color": "#747D87",

        "title_alpha": 240,
        "sub_alpha": 220,
    },

    "emerald_paper": {
        "white_bg": True,
        "board_bg": "#FFFFFF",

        "carbon_dark": "#17352A",
        "carbon_mid": "#2F9C7A",
        "carbon_highlight": "#CFEFDF",

        "glow_color": "#55B290",

        "title_color": "#1F2A2A",
        "sub_color": "#6E7C7C",

        "title_alpha": 240,
        "sub_alpha": 220,
    },

    "mint_sci": {
        "white_bg": True,
        "board_bg": "#FFFFFF",

        "carbon_dark": "#294238",
        "carbon_mid": "#7CBF9A",
        "carbon_highlight": "#E3F5E8",

        "glow_color": "#85CBA6",

        "title_color": "#263033",
        "sub_color": "#7A858C",

        "title_alpha": 240,
        "sub_alpha": 220,
    },

    "neutral_ink": {
        "white_bg": True,
        "board_bg": "#FFFFFF",

        "carbon_dark": "#2B2F33",
        "carbon_mid": "#6B7785",
        "carbon_highlight": "#D7DEE6",

        "glow_color": "#97A6B5",

        "title_color": "#20252B",
        "sub_color": "#6C7680",

        "title_alpha": 240,
        "sub_alpha": 220,
    },

    "warm_gold": {
        "white_bg": True,
        "board_bg": "#FFFDF8",

        "carbon_dark": "#4E3A1F",
        "carbon_mid": "#C29345",
        "carbon_highlight": "#F4E0A6",

        "glow_color": "#D2AA58",

        "title_color": "#31281E",
        "sub_color": "#857668",

        "title_alpha": 240,
        "sub_alpha": 220,
    },

    "cyan_dark": {
        "white_bg": False,
        "board_bg": "#071016",

        "carbon_dark": "#11303B",
        "carbon_mid": "#2FA8C9",
        "carbon_highlight": "#C4F2FF",

        "glow_color": "#4CC1DE",

        "title_color": "#EAFBFF",
        "sub_color": "#9AC4D0",

        "title_alpha": 240,
        "sub_alpha": 220,
    },

    "violet_carbon": {
        "white_bg": False,
        "board_bg": "#0C0B14",

        "carbon_dark": "#211A3B",
        "carbon_mid": "#7C63C9",
        "carbon_highlight": "#DDD6FF",

        "glow_color": "#8B77E6",

        "title_color": "#F2F0FF",
        "sub_color": "#B3ACD8",

        "title_alpha": 240,
        "sub_alpha": 220,
    },

    "red_graphene": {
        "white_bg": False,
        "board_bg": "#12090A",

        "carbon_dark": "#351517",
        "carbon_mid": "#C44F57",
        "carbon_highlight": "#FFD4D7",

        "glow_color": "#D45E67",

        "title_color": "#FFF1F2",
        "sub_color": "#D3A9AE",

        "title_alpha": 240,
        "sub_alpha": 220,
    },

    "copper_dark": {
        "white_bg": False,
        "board_bg": "#120E0A",

        "carbon_dark": "#332215",
        "carbon_mid": "#B9783E",
        "carbon_highlight": "#F2D0A9",

        "glow_color": "#C8864A",

        "title_color": "#FFF5EA",
        "sub_color": "#C6AE95",

        "title_alpha": 240,
        "sub_alpha": 220,
    },
}


# =============================================================================
# 3. Atom style presets
# =============================================================================

ACTIVE_ATOM_STYLE = "dense_fiber"

ATOM_PRESETS = {
    "balanced": {
        "highlight_gamma": 2.6,
        "highlight_strength": 0.16,
        "light_dir": (-0.25, 0.40, 0.58),

        "enable_glow": True,
        "glow_radius": 2.0,
        "glow_alpha_min": 0,
        "glow_alpha_max": 14,
        "glow_blur": 3,
        "glow_downsample": 22000,

        "atom_base_radius_factor": 1.25,
        "atom_radius_depth_min": 0.72,
        "atom_radius_depth_max": 1.22,
        "atom_alpha_min": 95,
        "atom_alpha_max": 225,
        "atom_ellipse_stretch": 1.0,
    },

    "paper_tiny": {
        "highlight_gamma": 2.8,
        "highlight_strength": 0.06,
        "light_dir": (-0.18, 0.28, 0.52),

        "enable_glow": False,
        "glow_radius": 1.5,
        "glow_alpha_min": 0,
        "glow_alpha_max": 0,
        "glow_blur": 2,
        "glow_downsample": 24000,

        "atom_base_radius_factor": 0.92,
        "atom_radius_depth_min": 0.86,
        "atom_radius_depth_max": 1.06,
        "atom_alpha_min": 125,
        "atom_alpha_max": 235,
        "atom_ellipse_stretch": 1.0,
    },

    "flat_2d": {
        "highlight_gamma": 3.0,
        "highlight_strength": 0.03,
        "light_dir": (-0.10, 0.15, 0.50),

        "enable_glow": False,
        "glow_radius": 1.5,
        "glow_alpha_min": 0,
        "glow_alpha_max": 0,
        "glow_blur": 2,
        "glow_downsample": 24000,

        "atom_base_radius_factor": 1.02,
        "atom_radius_depth_min": 0.98,
        "atom_radius_depth_max": 1.02,
        "atom_alpha_min": 150,
        "atom_alpha_max": 220,
        "atom_ellipse_stretch": 1.0,
    },

    "dense_fiber": {
        "highlight_gamma": 2.4,
        "highlight_strength": 0.10,
        "light_dir": (-0.22, 0.34, 0.56),

        "enable_glow": True,
        "glow_radius": 1.8,
        "glow_alpha_min": 0,
        "glow_alpha_max": 8,
        "glow_blur": 2,
        "glow_downsample": 24000,

        "atom_base_radius_factor": 1.08,
        "atom_radius_depth_min": 0.82,
        "atom_radius_depth_max": 1.10,
        "atom_alpha_min": 120,
        "atom_alpha_max": 235,
        "atom_ellipse_stretch": 1.0,
    },

    "large_beads": {
        "highlight_gamma": 2.4,
        "highlight_strength": 0.18,
        "light_dir": (-0.28, 0.42, 0.60),

        "enable_glow": True,
        "glow_radius": 2.2,
        "glow_alpha_min": 0,
        "glow_alpha_max": 10,
        "glow_blur": 3,
        "glow_downsample": 22000,

        "atom_base_radius_factor": 1.70,
        "atom_radius_depth_min": 0.75,
        "atom_radius_depth_max": 1.35,
        "atom_alpha_min": 110,
        "atom_alpha_max": 235,
        "atom_ellipse_stretch": 1.0,
    },

    "soft_dots": {
        "highlight_gamma": 2.6,
        "highlight_strength": 0.08,
        "light_dir": (-0.20, 0.32, 0.50),

        "enable_glow": True,
        "glow_radius": 2.6,
        "glow_alpha_min": 0,
        "glow_alpha_max": 12,
        "glow_blur": 4,
        "glow_downsample": 20000,

        "atom_base_radius_factor": 1.12,
        "atom_radius_depth_min": 0.86,
        "atom_radius_depth_max": 1.14,
        "atom_alpha_min": 72,
        "atom_alpha_max": 180,
        "atom_ellipse_stretch": 1.0,
    },

    "poster_glow": {
        "highlight_gamma": 2.2,
        "highlight_strength": 0.24,
        "light_dir": (-0.30, 0.48, 0.62),

        "enable_glow": True,
        "glow_radius": 2.8,
        "glow_alpha_min": 4,
        "glow_alpha_max": 26,
        "glow_blur": 5,
        "glow_downsample": 18000,

        "atom_base_radius_factor": 1.28,
        "atom_radius_depth_min": 0.72,
        "atom_radius_depth_max": 1.25,
        "atom_alpha_min": 95,
        "atom_alpha_max": 235,
        "atom_ellipse_stretch": 1.0,
    },

    "fiber_ellipses": {
        "highlight_gamma": 2.5,
        "highlight_strength": 0.14,
        "light_dir": (-0.24, 0.36, 0.58),

        "enable_glow": True,
        "glow_radius": 1.8,
        "glow_alpha_min": 0,
        "glow_alpha_max": 8,
        "glow_blur": 2,
        "glow_downsample": 24000,

        "atom_base_radius_factor": 1.18,
        "atom_radius_depth_min": 0.78,
        "atom_radius_depth_max": 1.18,
        "atom_alpha_min": 105,
        "atom_alpha_max": 228,
        "atom_ellipse_stretch": 1.24,
    },
}


# =============================================================================
# 4. Ring annotation colors 环颜色控制
# =============================================================================

RING_COLORS = {
    # Okabe-Ito-inspired, color-blind friendly publication palette.
    # Keep ring colors separate from ROI/connector colors to avoid semantic overload.
    5: "#868DEC",  # orange: non-hexagonal defect ring
    6: "#71BEA1",  # blue: six-member ring
    7: "#CC89AE",  # purple: non-hexagonal defect ring
}

RING_ATOM_COLORS = {
    5: "#A8AEE6",   # 更淡的紫 — 原子
    6: "#A0D5C0",   # 更淡的绿  
    7: "#D4A9C5",   # 更淡的粉
}


RING_FRONT_DEPTH_MODE_DEFAULT = "high-z"

# Right-panel context controls (v13).
# The key change versus v11 is that the gray background network is no longer
# forced to show the entire local ROI graph.  By default only the displayed
# rings and their immediate neighborhood are shown, which greatly reduces the
# visual noise in the publication figure.
RING_CONTEXT_MODE_DEFAULT = "full"
RING_CONTEXT_HOPS_DEFAULT = 1
RING_CONTEXT_MAX_ATOMS_DEFAULT = 220
RING_CONTEXT_EDGE_ALPHA_DEFAULT = 10
RING_CONTEXT_ATOM_ALPHA_DEFAULT = 0


# =============================================================================
# 5. Text / labels
# =============================================================================

TITLE_TEXT = "Carbon Fiber Model"
BOARD_TITLE = "Carbon Fiber Model — Three-View Presentation"
BOARD_SUBTITLE_TEMPLATE = "Generated with ASE · {n:,} rendered atoms"
BOARD_FOOTER = (
    "Static PNG views are for fast debugging; enable GIF only for final dynamic display."
)

RING_ZOOM_TITLE = "Front-view ROI mapping and local 5/6/7-member ring-network analysis"
RING_ZOOM_SUBTITLE = "Publication layout: extracted ROI, reduced context clutter, color-consistent rings"


# =============================================================================
# 6. Color helpers
# =============================================================================

def hex_to_rgb(hex_color):
    s = str(hex_color).strip()

    if s.startswith("#"):
        s = s[1:]

    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)

    if len(s) != 6:
        raise ValueError(f"Expected HEX color like '#64AF55', got: {hex_color!r}")

    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def hex_to_rgba(hex_color, alpha=255):
    r, g, b = hex_to_rgb(hex_color)
    return (r, g, b, int(alpha))


def hex_to_np_rgb(hex_color):
    return np.array(hex_to_rgb(hex_color), dtype=np.float32)


def load_style(style_name):
    if style_name not in STYLE_PRESETS:
        options = ", ".join(STYLE_PRESETS.keys())
        raise ValueError(f"Unknown style {style_name!r}. Available styles: {options}")

    raw = STYLE_PRESETS[style_name]
    style = dict(raw)
    style["board_bg_rgba"] = hex_to_rgba(raw["board_bg"], 255)
    style["carbon_dark_np"] = hex_to_np_rgb(raw["carbon_dark"])
    style["carbon_mid_np"] = hex_to_np_rgb(raw["carbon_mid"])
    style["carbon_highlight_np"] = hex_to_np_rgb(raw["carbon_highlight"])
    style["glow_rgb"] = hex_to_rgb(raw["glow_color"])
    style["title_rgba"] = hex_to_rgba(raw["title_color"], raw.get("title_alpha", 240))
    style["sub_rgba"] = hex_to_rgba(raw["sub_color"], raw.get("sub_alpha", 220))
    return style


def load_atom_style(atom_style_name):
    if atom_style_name not in ATOM_PRESETS:
        options = ", ".join(ATOM_PRESETS.keys())
        raise ValueError(f"Unknown atom style {atom_style_name!r}. Available atom styles: {options}")

    raw = dict(ATOM_PRESETS[atom_style_name])
    raw["light_dir_np"] = np.array(raw["light_dir"], dtype=np.float32)
    return raw


STYLE = None
ATOM_STYLE = None


# =============================================================================
# 7. Math helpers
# =============================================================================

def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array(
        [[1, 0, 0],
         [0, c, -s],
         [0, s, c]],
        dtype=np.float32
    )


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array(
        [[c, 0, s],
         [0, 1, 0],
         [-s, 0, c]],
        dtype=np.float32
    )


def load_font(size=28, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/Library/Fonts/Arial Unicode.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]

    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)

    return ImageFont.load_default()


# =============================================================================
# 8. ASE loading / preprocessing
# =============================================================================

def load_atoms_with_ase(path, read_index=ASE_READ_INDEX):
    atoms = read(str(path), index=read_index)
    positions = atoms.get_positions().astype(np.float32)
    numbers = atoms.get_atomic_numbers()

    if len(positions) == 0:
        raise ValueError("ASE did not read any atoms.")

    return atoms, positions, numbers


def pca_align(points, axis_perm=AXIS_PERM):
    points = points - points.mean(axis=0, keepdims=True)

    cov = np.cov(points.T)
    vals, vecs = np.linalg.eigh(cov)

    order = np.argsort(vals)[::-1]
    vecs = vecs[:, order]

    if np.linalg.det(vecs) < 0:
        vecs[:, -1] *= -1

    aligned = points @ vecs
    aligned = aligned[:, axis_perm]

    return aligned


def normalize_points(points):
    points = points - points.mean(axis=0, keepdims=True)
    scale = np.ptp(points, axis=0).max()

    if scale <= 1e-12:
        scale = 1.0

    return points / scale


def downsample_if_needed(points, numbers, max_points=MAX_POINTS, seed=7):
    if len(points) <= max_points:
        return points, numbers

    rng = np.random.default_rng(seed)
    idx = rng.choice(len(points), max_points, replace=False)

    return points[idx], numbers[idx]


# =============================================================================
# 9. Orthographic views
# =============================================================================

def get_three_view_rotations():
    front = np.eye(3, dtype=np.float32)

    top = np.array(
        [[1, 0, 0],
         [0, 0, 1],
         [0, -1, 0]],
        dtype=np.float32
    )

    side = np.array(
        [[0, 0, 1],
         [0, 1, 0],
         [-1, 0, 0]],
        dtype=np.float32
    )

    return {
        "Front View": front,
        "Top View": top,
        "Side View": side,
    }


# =============================================================================
# 10. Rendering
# =============================================================================

def make_background(size, transparent=False, white=False):
    w, h = size

    if transparent:
        return Image.new("RGBA", size, (0, 0, 0, 0))

    if white:
        return Image.new("RGBA", size, (255, 255, 255, 255))

    y = np.linspace(0, 1, h)[:, None]
    x = np.linspace(0, 1, w)[None, :]

    r = np.sqrt((x - 0.5) ** 2 + (y - 0.42) ** 2)
    base = np.clip(26 - 34 * r, 5, 26)

    bg = np.dstack([base, base + 2, base + 5]).astype(np.uint8)

    return Image.fromarray(bg, "RGB").convert("RGBA")


def project(points, R, size, zoom=ZOOM):
    w, h = size

    view_points = points @ R.T

    x = view_points[:, 0]
    y = view_points[:, 1]
    z = view_points[:, 2]

    span = max(np.ptp(x), np.ptp(y))
    if span <= 1e-12:
        span = 1.0

    scale = min(w, h) * zoom / span

    u = w / 2 + (x - (x.max() + x.min()) / 2) * scale
    v = h / 2 - (y - (y.max() + y.min()) / 2) * scale

    return u, v, z, view_points


def get_atom_radius_factors(numbers):
    if len(numbers) == 0:
        return np.array([], dtype=np.float32)

    radii = np.array([covalent_radii[z] for z in numbers], dtype=np.float32)
    c_radius = covalent_radii[atomic_numbers["C"]]
    radii = radii / c_radius
    radii = np.clip(radii, 0.55, 1.80)
    return radii


def get_base_colors(numbers, depth, light):
    carbon_dark = STYLE["carbon_dark_np"]
    carbon_mid = STYLE["carbon_mid_np"]
    carbon_highlight = STYLE["carbon_highlight_np"]

    if USE_ASE_JMOL_COLORS:
        colors = np.array([jmol_colors[z] for z in numbers], dtype=np.float32) * 255.0

        shade = 0.55 + 0.35 * depth[:, None]
        light_boost = 0.85 + 0.18 * light[:, None]

        colors = colors * shade * light_boost
        colors += carbon_highlight * (light[:, None] ** ATOM_STYLE["highlight_gamma"]) * 0.08

    else:
        base = carbon_dark * (1 - depth[:, None]) + carbon_mid * depth[:, None]
        highlight = (
            carbon_highlight
            * (light[:, None] ** ATOM_STYLE["highlight_gamma"])
            * ATOM_STYLE["highlight_strength"]
        )
        colors = base + highlight

    return np.clip(colors, 0, 255).astype(np.uint8)


USE_ASE_JMOL_COLORS = False


def render(points, numbers, radius_factors, R, size=(900, 900),
           title=None, label=None, transparent=False, white_bg=False,
           enable_glow=None, atom_ellipse_stretch=None):
    w, h = size

    if enable_glow is None:
        enable_glow = ATOM_STYLE["enable_glow"]
    if atom_ellipse_stretch is None:
        atom_ellipse_stretch = ATOM_STYLE["atom_ellipse_stretch"]

    img = make_background(size, transparent=transparent, white=white_bg)

    u, v, z, view_points = project(points, R, size)

    order = np.argsort(z)

    u = u[order]
    v = v[order]
    z = z[order]
    view_points = view_points[order]
    numbers = numbers[order]
    radius_factors = radius_factors[order]

    depth = (z - z.min()) / (z.max() - z.min() + 1e-8)

    light_dir = ATOM_STYLE["light_dir_np"] / np.linalg.norm(ATOM_STYLE["light_dir_np"])
    normals = view_points / (np.linalg.norm(view_points, axis=1, keepdims=True) + 1e-8)
    light = np.clip(normals @ light_dir, 0, 1)

    colors = get_base_colors(numbers, depth, light)

    if enable_glow and ATOM_STYLE["glow_alpha_max"] > 0:
        glow = Image.new("RGBA", size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow, "RGBA")

        step = max(1, len(u) // ATOM_STYLE["glow_downsample"])

        for x, y, d in zip(u[::step], v[::step], depth[::step]):
            alpha = int(
                ATOM_STYLE["glow_alpha_min"]
                + (ATOM_STYLE["glow_alpha_max"] - ATOM_STYLE["glow_alpha_min"]) * d
            )

            gd.ellipse(
                (
                    x - ATOM_STYLE["glow_radius"],
                    y - ATOM_STYLE["glow_radius"],
                    x + ATOM_STYLE["glow_radius"],
                    y + ATOM_STYLE["glow_radius"],
                ),
                fill=(*STYLE["glow_rgb"], alpha)
            )

        glow = glow.filter(ImageFilter.GaussianBlur(ATOM_STYLE["glow_blur"]))
        img = Image.alpha_composite(img, glow)

    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer, "RGBA")

    base_radius = max(1.1, min(w, h) / 720 * ATOM_STYLE["atom_base_radius_factor"])

    for x, y, d, c, rf in zip(u, v, depth, colors, radius_factors):
        r = base_radius * rf * (
            ATOM_STYLE["atom_radius_depth_min"]
            + (ATOM_STYLE["atom_radius_depth_max"] - ATOM_STYLE["atom_radius_depth_min"]) * d
        )

        alpha = int(
            ATOM_STYLE["atom_alpha_min"]
            + (ATOM_STYLE["atom_alpha_max"] - ATOM_STYLE["atom_alpha_min"]) * d
        )

        draw.ellipse(
            (
                x - r * atom_ellipse_stretch,
                y - r,
                x + r * atom_ellipse_stretch,
                y + r,
            ),
            fill=(int(c[0]), int(c[1]), int(c[2]), alpha)
        )

    img = Image.alpha_composite(img, layer)

    draw = ImageDraw.Draw(img, "RGBA")
    title_color = STYLE["title_rgba"]

    label_bg = (255, 255, 255, 190) if STYLE["white_bg"] else (10, 14, 18, 145)
    label_outline = (160, 170, 180, 110)

    if title:
        font = load_font(32, bold=True)
        draw.text((30, 28), title, font=font, fill=title_color)

    if label:
        font = load_font(24, bold=True)
        bbox = draw.textbbox((0, 0), label, font=font)
        tw = bbox[2] - bbox[0]

        draw.rounded_rectangle(
            (w - tw - 52, 28, w - 28, 72),
            radius=16,
            fill=label_bg,
            outline=label_outline,
            width=1
        )

        draw.text((w - tw - 40, 36), label, font=font, fill=title_color)

    if transparent:
        return img

    return img.convert("RGB")


# =============================================================================
# 11. Fast local ring detection
# =============================================================================

def canonical_cycle(cycle):
    """
    Canonicalize a cycle so the same ring found through different DFS paths
    is represented uniquely.
    """
    cyc = list(cycle)
    if len(cyc) > 1 and cyc[0] == cyc[-1]:
        cyc = cyc[:-1]

    n = len(cyc)
    candidates = []

    for k in range(n):
        candidates.append(tuple(cyc[k:] + cyc[:k]))

    rev = list(reversed(cyc))
    for k in range(n):
        candidates.append(tuple(rev[k:] + rev[:k]))

    return min(candidates)


def select_roi_candidate_indices(u, v, numbers, roi_px, margin_px=90, max_local_atoms=1200):
    """
    Select atoms whose front-view projected positions fall inside the ROI
    plus a small pixel margin. This is the key performance fix.

    The ring graph is built only from this local subset.
    """
    x0, y0, x1, y1 = roi_px
    numbers = np.asarray(numbers)

    mask = (
        (numbers == 6)
        & (u >= x0 - margin_px)
        & (u <= x1 + margin_px)
        & (v >= y0 - margin_px)
        & (v <= y1 + margin_px)
    )

    idx = np.where(mask)[0]

    if len(idx) <= max_local_atoms:
        return idx.astype(int)

    # If the ROI is still too dense, keep the atoms closest to the ROI center.
    cx = 0.5 * (x0 + x1)
    cy = 0.5 * (y0 + y1)

    d2 = (u[idx] - cx) ** 2 + (v[idx] - cy) ** 2
    keep = np.argsort(d2)[:max_local_atoms]

    return idx[keep].astype(int)


def build_local_carbon_graph(points_angstrom, numbers, candidate_global_indices,
                             cutoff_scale=1.22, max_degree=4):
    """
    Build a local C-C graph using ASE neighbor_list.

    Important:
      points_angstrom must be the PCA-aligned but NOT normalized coordinates.
      This keeps the C-C cutoff physically meaningful.

    ASE cutoff behavior:
      If we pass per-atom radii, ASE connects i-j when:
        distance(i, j) < cutoff_i + cutoff_j

      For carbon:
        cutoff_i = covalent_radius_C * cutoff_scale
      Therefore C-C bond threshold is roughly:
        2 * covalent_radius_C * cutoff_scale
    """
    candidate_global_indices = np.asarray(candidate_global_indices, dtype=int)

    if len(candidate_global_indices) == 0:
        return np.array([], dtype=int), {}

    is_carbon = np.asarray(numbers)[candidate_global_indices] == 6
    local_to_global = candidate_global_indices[is_carbon]

    if len(local_to_global) == 0:
        return np.array([], dtype=int), {}

    from ase import Atoms

    sub_points = np.asarray(points_angstrom, dtype=np.float32)[local_to_global]
    carbon_atoms = Atoms(numbers=[6] * len(local_to_global), positions=sub_points)

    c_radius = covalent_radii[atomic_numbers["C"]]
    cutoffs = np.full(len(local_to_global), c_radius * cutoff_scale, dtype=float)

    try:
        i_list, j_list, d_list = neighbor_list(
            "ijd",
            carbon_atoms,
            cutoffs,
            self_interaction=False,
        )
    except TypeError:
        # Older ASE fallback: no distance output.
        i_list, j_list = neighbor_list(
            "ij",
            carbon_atoms,
            cutoffs,
            self_interaction=False,
        )
        d_list = np.linalg.norm(sub_points[i_list] - sub_points[j_list], axis=1)

    # Keep distances so we can trim suspicious over-coordination.
    neighbor_dists = defaultdict(dict)

    for i, j, d in zip(i_list.tolist(), j_list.tolist(), np.asarray(d_list).tolist()):
        if i == j:
            continue

        old_ij = neighbor_dists[i].get(j)
        old_ji = neighbor_dists[j].get(i)

        if old_ij is None or d < old_ij:
            neighbor_dists[i][j] = float(d)
        if old_ji is None or d < old_ji:
            neighbor_dists[j][i] = float(d)

    # Limit degree. Carbon networks are usually degree 3, sometimes 4 near defects.
    # This cap prevents a too-large cutoff from making DFS explode.
    graph = defaultdict(set)

    for i, nbd in neighbor_dists.items():
        kept = sorted(nbd.items(), key=lambda kv: kv[1])[:max_degree]
        for j, _d in kept:
            graph[i].add(j)
            graph[j].add(i)

    # Soft second pass: if a node still has too many neighbors due reciprocal additions,
    # keep the nearest max_degree neighbors.
    pruned = defaultdict(set)

    for i, nbs in graph.items():
        ranked = []
        for j in nbs:
            d = neighbor_dists.get(i, {}).get(j)
            if d is None:
                d = neighbor_dists.get(j, {}).get(i, 1e9)
            ranked.append((j, d))

        for j, _d in sorted(ranked, key=lambda kv: kv[1])[:max_degree]:
            pruned[i].add(j)
            pruned[j].add(i)

    return local_to_global.astype(int), pruned


def find_cycles_of_sizes_local(graph, sizes=(5, 6, 7), max_cycles_per_size=120):
    """
    Bounded DFS ring search.

    Why this is safe enough now:
      - the graph is local to ROI, not the whole carbon fiber
      - DFS depth is capped at 7
      - each ring size has a hard maximum output count
      - nodes smaller than start are not visited, which removes many duplicates
    """
    sizes = sorted(set(int(s) for s in sizes))
    found = {s: set() for s in sizes}

    if not graph or not sizes:
        return found

    nodes = sorted(graph.keys())
    max_size = max(sizes)
    max_cycles_per_size = int(max_cycles_per_size)

    def all_caps_reached():
        return all(len(found[s]) >= max_cycles_per_size for s in sizes)

    def dfs(start, current, path, visited):
        if len(path) > max_size or all_caps_reached():
            return

        for nb in sorted(graph.get(current, ())):
            if nb == start:
                n = len(path)
                if n in found and len(found[n]) < max_cycles_per_size:
                    found[n].add(canonical_cycle(path))
                continue

            # Symmetry pruning:
            # start should be the smallest local index in this cycle.
            if nb < start:
                continue

            if nb in visited:
                continue

            if len(path) >= max_size:
                continue

            visited.add(nb)
            path.append(nb)

            dfs(start, nb, path, visited)

            path.pop()
            visited.remove(nb)

    for start in nodes:
        if all_caps_reached():
            break
        dfs(start, start, [start], {start})

    return found


def filter_chordless_cycles(cycles_by_size, graph):
    """
    Keep only chordless cycles.

    A chordless 6-cycle is closer to a real six-member carbon ring.
    If there is an internal shortcut edge, the detected cycle is usually not
    the clean polygon ring we want to label.
    """
    out = {}

    for size, cycset in cycles_by_size.items():
        keep = []

        for cyc in cycset:
            cyc = list(cyc)
            n = len(cyc)
            ok = True

            ring_edges = set()
            for i in range(n):
                a = cyc[i]
                b = cyc[(i + 1) % n]
                ring_edges.add(tuple(sorted((a, b))))

            for i in range(n):
                for j in range(i + 1, n):
                    if j == i + 1 or (i == 0 and j == n - 1):
                        continue

                    a, b = cyc[i], cyc[j]
                    if b in graph.get(a, set()):
                        if tuple(sorted((a, b))) not in ring_edges:
                            ok = False
                            break

                if not ok:
                    break

            if ok:
                keep.append(tuple(cyc))

        out[size] = keep

    return out


def map_local_cycles_to_global(cycles_by_size, local_to_global):
    mapped = {}

    for size, cycles in cycles_by_size.items():
        mapped[size] = [
            tuple(int(local_to_global[i]) for i in cyc)
            for cyc in cycles
        ]

    return mapped


def detect_rings_in_roi(points_angstrom, numbers, u_full, v_full, roi_px,
                        cutoff_scale=1.22, margin_px=90,
                        max_local_atoms=1200, max_degree=4,
                        max_cycles_per_size=120):
    """
    Detect 5/6/7-member rings only in the selected ROI.

    Returns:
      global_cycles:
        {5: [(global_atom_idx, ...), ...],
         6: [...],
         7: [...]}

      info:
        debug information for printing
    """
    candidate_global = select_roi_candidate_indices(
        u_full,
        v_full,
        numbers,
        roi_px,
        margin_px=margin_px,
        max_local_atoms=max_local_atoms,
    )

    local_to_global, graph = build_local_carbon_graph(
        points_angstrom,
        numbers,
        candidate_global,
        cutoff_scale=cutoff_scale,
        max_degree=max_degree,
    )

    info = {
        "candidate_atoms": int(len(candidate_global)),
        "local_carbon_atoms": int(len(local_to_global)),
        "local_edges": int(sum(len(nbs) for nbs in graph.values()) // 2),
    }

    if len(local_to_global) == 0 or len(graph) == 0:
        return {5: [], 6: [], 7: []}, info

    cycles = find_cycles_of_sizes_local(
        graph,
        sizes=(5, 6, 7),
        max_cycles_per_size=max_cycles_per_size,
    )
    cycles = filter_chordless_cycles(cycles, graph)
    global_cycles = map_local_cycles_to_global(cycles, local_to_global)

    # Keep rings that intersect the exact ROI.
    # This is broader than centroid-only filtering and improves full-ROI coverage.
    for size in (5, 6, 7):
        kept = []
        for cyc in global_cycles.get(size, []):
            if ring_inside_roi(cyc, u_full, v_full, roi_px, mode="all"):
                kept.append(cyc)
                continue

            if ring_touches_roi(cyc, u_full, v_full, roi_px):
                kept.append(cyc)

        global_cycles[size] = kept

    info["rings_5"] = int(len(global_cycles.get(5, [])))
    info["rings_6"] = int(len(global_cycles.get(6, [])))
    info["rings_7"] = int(len(global_cycles.get(7, [])))

    return global_cycles, info

# =============================================================================
# 12. Three-view / GIF output
# =============================================================================

def render_gif(points, numbers, radius_factors, out_dir, gif_size=GIF_SIZE):
    print("Step 4a/6: Rendering rotating GIF...")

    frames = []

    for i in range(FRAME_COUNT):
        angle = 2 * math.pi * i / FRAME_COUNT
        R = rot_x(math.radians(GIF_TILT_X)) @ rot_y(angle)

        frame = render(
            points,
            numbers,
            radius_factors,
            R,
            size=gif_size,
            title=TITLE_TEXT,
            transparent=False,
            white_bg=STYLE["white_bg"]
        )

        frames.append(frame)

    gif_path = out_dir / GIF_NAME
    imageio.mimsave(gif_path, frames, duration=GIF_DURATION)

    print(f"Saved GIF: {gif_path}")
    return gif_path


def render_three_views(points, numbers, radius_factors, out_dir, view_size=VIEW_SIZE):
    print("Step 4b/6: Rendering strict orthographic three views...")

    views = get_three_view_rotations()
    single_images = []

    for name, R in views.items():
        img = render(
            points,
            numbers,
            radius_factors,
            R,
            size=view_size,
            title=TITLE_TEXT,
            label=name,
            transparent=True,
            white_bg=False,
            enable_glow=ATOM_STYLE["enable_glow"],
            atom_ellipse_stretch=1.0 if name in ("Front View", "Top View", "Side View") else ATOM_STYLE["atom_ellipse_stretch"],
        )

        out_name = out_dir / f"{name.lower().replace(' ', '_')}_ase.png"
        img.save(out_name, quality=95)

        single_images.append((name, img))
        print(f"Saved: {out_name}")

    return single_images


def render_three_view_board(single_images, atom_count, out_dir, view_size=VIEW_SIZE):
    print("Step 5/6: Rendering three-view board...")

    gap = 28
    panel_w, panel_h = view_size
    title_h = 100
    footer_h = 42

    board_w = panel_w * 3 + gap * 4
    board_h = panel_h + title_h + footer_h

    board = Image.new("RGBA", (board_w, board_h), STYLE["board_bg_rgba"])
    draw = ImageDraw.Draw(board, "RGBA")

    title_font = load_font(42, bold=True)
    sub_font = load_font(20)
    foot_font = load_font(18)

    draw.text((gap, 26), BOARD_TITLE, font=title_font, fill=STYLE["title_rgba"])
    draw.text(
        (gap + 2, 74),
        BOARD_SUBTITLE_TEMPLATE.format(n=atom_count),
        font=sub_font,
        fill=STYLE["sub_rgba"]
    )

    for i, (name, img) in enumerate(single_images):
        x = gap + i * (panel_w + gap)
        y = title_h

        panel_color = (245, 247, 250, 230) if STYLE["white_bg"] else (12, 16, 22, 190)
        outline_color = (170, 180, 190, 105)

        draw.rounded_rectangle(
            (x, y, x + panel_w, y + panel_h),
            radius=26,
            fill=panel_color,
            outline=outline_color,
            width=2
        )

        panel_canvas = Image.new(
            "RGBA",
            (panel_w, panel_h),
            (255, 255, 255, 255) if STYLE["white_bg"] else (8, 10, 13, 255)
        )
        panel_canvas.paste(img, (0, 0), img)
        board.paste(panel_canvas, (x, y), panel_canvas)

    draw.text((gap, board_h - 34), BOARD_FOOTER, font=foot_font, fill=STYLE["sub_rgba"])

    board_path = out_dir / THREE_VIEW_NAME
    board.convert("RGB").save(board_path, quality=96)

    print(f"Saved three-view board: {board_path}")
    return board_path


# =============================================================================
# 13. Ring zoom figure
# =============================================================================

def get_default_zoom_box():
    """
    Default ROI in normalized front-view image coordinates.
    Format: x0, y0, x1, y1 in [0, 1].

    v9 uses a smaller default region than v8, because the right panel is meant
    to show only one local patch instead of a large column-like crop.
    """
    return (0.512, 0.645, 0.578, 0.715)


def validate_zoom_box_or_raise(box):
    """
    Validate user-provided normalized ROI.

    The internal helper normalized_box_to_pixels() can clamp values, but user
    input should be checked explicitly so mistakes are visible.
    """
    if box is None:
        return None

    if len(box) != 4:
        raise ValueError("--zoom-box must contain exactly four numbers: X0 Y0 X1 Y1")

    x0, y0, x1, y1 = [float(v) for v in box]

    vals = [x0, y0, x1, y1]
    if not all(np.isfinite(vals)):
        raise ValueError("--zoom-box values must be finite numbers.")

    if not all(0.0 <= v <= 1.0 for v in vals):
        raise ValueError("--zoom-box values must be in [0, 1].")

    if not (x0 < x1 and y0 < y1):
        raise ValueError("--zoom-box must satisfy X0 < X1 and Y0 < Y1.")

    if (x1 - x0) < 0.02 or (y1 - y0) < 0.02:
        raise ValueError("--zoom-box is too small. Use at least about 0.02 in width and height.")

    return (x0, y0, x1, y1)


def validate_ring_options_or_raise(args):
    """
    Validate parameters that strongly affect ring detection cost and correctness.
    """
    if args.ring_cutoff_scale <= 0:
        raise ValueError("--ring-cutoff-scale must be positive.")

    if not (0.80 <= args.ring_cutoff_scale <= 1.80):
        raise ValueError("--ring-cutoff-scale is suspicious. A typical value is 1.10–1.30.")

    if args.ring_roi_margin_px < 0:
        raise ValueError("--ring-roi-margin-px must be non-negative.")

    if args.ring_max_local_atoms < 7:
        raise ValueError("--ring-max-local-atoms must be at least 7.")

    if args.ring_max_degree < 1:
        raise ValueError("--ring-max-degree must be at least 1.")

    if args.ring_max_degree > 8:
        raise ValueError("--ring-max-degree is too large and may make DFS explode.")

    if args.ring_n_layers < 1:
        raise ValueError("--ring-n-layers must be at least 1.")

    if args.ring_show_layers < 0:
        raise ValueError("--ring-show-layers must be >= 0 (0 = show all).")

    if args.ring_show_layers > args.ring_n_layers:
        raise ValueError("--ring-show-layers cannot exceed --ring-n-layers.")

    if not (0.0 <= args.ring_layer_alpha_falloff <= 1.0):
        raise ValueError("--ring-layer-alpha-falloff must be in [0.0, 1.0].")

    if not (0.0 <= args.ring_layer_scale_falloff <= 1.0):
        raise ValueError("--ring-layer-scale-falloff must be in [0.0, 1.0].")

    if args.ring_zoom_scale < 0.2 or args.ring_zoom_scale > 3.0:
        raise ValueError("--ring-zoom-scale must be in [0.2, 3.0].")

    if args.ring_max_cycles_per_size < 1:
        raise ValueError("--ring-max-cycles-per-size must be at least 1.")

    if args.layer_opacity_boost < -0.95:
        raise ValueError("--layer-opacity-boost is too negative; opacity would almost disappear.")

    if args.layer_opacity_boost > 2.0:
        raise ValueError("--layer-opacity-boost is too large; use a value <= 2.0.")

    if getattr(args, "ring_front_depth", RING_FRONT_DEPTH_MODE_DEFAULT) not in ("high-z", "low-z"):
        raise ValueError("--ring-front-depth must be either high-z or low-z.")

    if getattr(args, "ring_context_mode", RING_CONTEXT_MODE_DEFAULT) not in ("neighbors", "full", "off"):
        raise ValueError("--ring-context-mode must be one of: neighbors, full, off.")

    if getattr(args, "ring_context_hops", RING_CONTEXT_HOPS_DEFAULT) < 0:
        raise ValueError("--ring-context-hops must be >= 0.")

    if getattr(args, "ring_context_max_atoms", RING_CONTEXT_MAX_ATOMS_DEFAULT) < 1:
        raise ValueError("--ring-context-max-atoms must be >= 1.")

    if not (0 <= getattr(args, "ring_context_edge_alpha", RING_CONTEXT_EDGE_ALPHA_DEFAULT) <= 255):
        raise ValueError("--ring-context-edge-alpha must be in [0, 255].")

    if not (0 <= getattr(args, "ring_context_atom_alpha", RING_CONTEXT_ATOM_ALPHA_DEFAULT) <= 255):
        raise ValueError("--ring-context-atom-alpha must be in [0, 255].")


def normalized_box_to_pixels(box, size):
    w, h = size
    x0, y0, x1, y1 = box

    x0 = int(round(max(0.0, min(1.0, x0)) * w))
    y0 = int(round(max(0.0, min(1.0, y0)) * h))
    x1 = int(round(max(0.0, min(1.0, x1)) * w))
    y1 = int(round(max(0.0, min(1.0, y1)) * h))

    if x1 <= x0 + 5:
        x1 = min(w, x0 + max(20, w // 8))
    if y1 <= y0 + 5:
        y1 = min(h, y0 + max(20, h // 8))

    return (x0, y0, x1, y1)


def ring_centroid_pixels(ring_indices, u, v):
    pts = np.column_stack([u[list(ring_indices)], v[list(ring_indices)]])
    return pts.mean(axis=0)


def ring_inside_roi(ring_indices, u, v, roi_px, mode="centroid"):
    x0, y0, x1, y1 = roi_px
    pts = np.column_stack([u[list(ring_indices)], v[list(ring_indices)]])

    if mode == "all":
        return np.all(
            (pts[:, 0] >= x0)
            & (pts[:, 0] <= x1)
            & (pts[:, 1] >= y0)
            & (pts[:, 1] <= y1)
        )

    c = pts.mean(axis=0)
    return (x0 <= c[0] <= x1) and (y0 <= c[1] <= y1)


def ring_touches_roi(ring_indices, u, v, roi_px):
    """
    Return True if any atom of the ring falls inside the exact ROI.

    Why this is added in v11:
      v10 used centroid-based filtering, which can miss edge rings.
      For paper figures, users usually expect the whole selected rectangular
      patch to be analyzed, including rings near the ROI boundary.
    """
    x0, y0, x1, y1 = roi_px
    pts = np.column_stack([u[list(ring_indices)], v[list(ring_indices)]])
    inside = (
        (pts[:, 0] >= x0)
        & (pts[:, 0] <= x1)
        & (pts[:, 1] >= y0)
        & (pts[:, 1] <= y1)
    )
    return bool(np.any(inside))


def _panel_label(draw, x, y, text, fg):
    font = load_font(22, bold=True)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]

    draw.rounded_rectangle(
        (x, y, x + tw + 24, y + 38),
        radius=12,
        fill=(255, 255, 255, 220) if STYLE["white_bg"] else (10, 14, 18, 180),
        outline=(160, 170, 180, 110),
        width=1,
    )
    draw.text((x + 12, y + 7), text, font=font, fill=fg)


def auto_try_rois(points_angstrom, numbers, u_full, v_full, image_size,
                  cutoff_scale=1.22, margin_px=90, max_local_atoms=1200,
                  max_degree=4, max_cycles_per_size=120):
    """
    Optional local ROI search. This never performs global ring detection.
    It simply tries several small image-space windows and picks the one with
    the most 5/6/7-member rings.
    """
    w, h = image_size
    box_w = int(w * 0.08)
    box_h = int(h * 0.14)

    xs = np.linspace(int(w * 0.18), int(w * 0.82 - box_w), 5).astype(int)
    ys = np.linspace(int(h * 0.16), int(h * 0.84 - box_h), 5).astype(int)

    best = None

    for x0 in xs:
        for y0 in ys:
            roi_px = (int(x0), int(y0), int(x0 + box_w), int(y0 + box_h))
            rings, info = detect_rings_in_roi(
                points_angstrom,
                numbers,
                u_full,
                v_full,
                roi_px,
                cutoff_scale=cutoff_scale,
                margin_px=margin_px,
                max_local_atoms=max_local_atoms,
                max_degree=max_degree,
                max_cycles_per_size=max_cycles_per_size,
            )

            score = (
                5 * min(len(rings.get(6, [])), 8)
                + 4 * min(len(rings.get(5, [])), 5)
                + 4 * min(len(rings.get(7, [])), 5)
            )
            score += sum(1 for s in (5, 6, 7) if len(rings.get(s, [])) > 0)

            candidate = (score, sum(len(rings.get(s, [])) for s in (5, 6, 7)), roi_px, rings, info)

            if best is None or candidate[:2] > best[:2]:
                best = candidate

    if best is None:
        return None, {5: [], 6: [], 7: []}, {}

    _score, _count, roi_px, rings, info = best
    return roi_px, rings, info


def _fit_roi_to_panel(roi_px, panel_size, padding=70):
    """
    Return a scale and offset so that the selected ROI fills the local panel.
    """
    panel_w, panel_h = panel_size
    x0, y0, x1, y1 = roi_px

    roi_w = max(1, x1 - x0)
    roi_h = max(1, y1 - y0)

    sx = (panel_w - 2 * padding) / roi_w
    sy = (panel_h - 2 * padding) / roi_h

    scale = max(0.1, min(sx, sy))
    ox = (panel_w - roi_w * scale) / 2.0
    oy = (panel_h - roi_h * scale) / 2.0

    return scale, ox, oy


def _transform_roi_points(u, v, roi_px, scale, ox, oy):
    """
    Convert full-image pixel coordinates to local-panel coordinates.
    """
    x0, y0, _x1, _y1 = roi_px
    px = ox + (np.asarray(u) - x0) * scale
    py = oy + (np.asarray(v) - y0) * scale
    return px, py


def _build_ring_edge_sets(rings):
    """
    Build:
      - ring_atoms_by_size: atoms participating in each ring size
      - ring_edges_by_size: colored edges for each ring size
      - atom_primary_size: one color label per atom for drawing highlighted atoms

    When an atom belongs to multiple rings, non-hexagonal rings are prioritized,
    because 5/7 rings are usually the defect rings the viewer cares about.
    """
    ring_atoms_by_size = {5: set(), 6: set(), 7: set()}
    ring_edges_by_size = {5: set(), 6: set(), 7: set()}

    for size in (5, 6, 7):
        for cyc in rings.get(size, []):
            cyc = list(cyc)
            n = len(cyc)

            for a in cyc:
                ring_atoms_by_size[size].add(int(a))

            for i in range(n):
                a = int(cyc[i])
                b = int(cyc[(i + 1) % n])
                ring_edges_by_size[size].add(tuple(sorted((a, b))))

    atom_primary_size = {}

    # Priority: 5 > 7 > 6（缺陷环优先于正常六元环）
    for size in (6, 7, 5):
        for a in ring_atoms_by_size[size]:
            atom_primary_size[int(a)] = int(size)

    return ring_atoms_by_size, ring_edges_by_size, atom_primary_size


def _get_local_graph_for_drawing(points_angstrom, numbers, u_full, v_full, roi_px,
                                 cutoff_scale, margin_px, max_local_atoms, max_degree):
    """
    Build a local C-C graph for visualizing the selected patch.

    This is separate from detect_rings_in_roi() so the drawing can include
    non-ring neighboring atoms and bonds as a pale environment.
    """
    candidate_global = select_roi_candidate_indices(
        u_full,
        v_full,
        numbers,
        roi_px,
        margin_px=margin_px,
        max_local_atoms=max_local_atoms,
    )

    local_to_global, graph = build_local_carbon_graph(
        points_angstrom,
        numbers,
        candidate_global,
        cutoff_scale=cutoff_scale,
        max_degree=max_degree,
    )

    edges_global = set()

    for i_local, nbs in graph.items():
        if i_local >= len(local_to_global):
            continue

        gi = int(local_to_global[i_local])

        for j_local in nbs:
            if j_local >= len(local_to_global):
                continue

            gj = int(local_to_global[j_local])
            if gi == gj:
                continue

            edges_global.add(tuple(sorted((gi, gj))))

    return local_to_global.astype(int), edges_global



def _estimate_panel_pixels_per_angstrom(atom_indices, points_angstrom, u_full, v_full, panel_scale):
    """
    Estimate the final-panel pixel/Å conversion for the orthographic front view.

    The rendered coordinates are generated from normalized coordinates, while the
    scale bar must be based on the original Å coordinates.  Because the front
    projection is linear, a local robust slope estimate from x→u and y→v gives a
    reliable pixel/Å factor after the ROI zoom scale is applied.
    """
    atoms = np.asarray(sorted(set(int(a) for a in atom_indices)), dtype=int)
    if len(atoms) < 3:
        return None

    pts = np.asarray(points_angstrom, dtype=float)[atoms]
    u = np.asarray(u_full, dtype=float)[atoms]
    v = np.asarray(v_full, dtype=float)[atoms]

    slopes = []
    for coord, pix in ((pts[:, 0], u), (pts[:, 1], v)):
        c = coord - coord.mean()
        p = pix - pix.mean()
        denom = float(np.dot(c, c))
        if denom > 1e-10:
            slope = abs(float(np.dot(c, p) / denom))
            if np.isfinite(slope) and slope > 1e-8:
                slopes.append(slope)

    if not slopes:
        return None

    return float(np.median(slopes) * panel_scale)


def _nice_scale_bar_length(max_px, px_per_angstrom):
    """
    Pick a readable, conservative scale-bar length.
    Returns (length_in_angstrom, length_in_pixels).
    """
    if px_per_angstrom is None or not np.isfinite(px_per_angstrom) or px_per_angstrom <= 1e-8:
        return None, None

    candidates = [0.5, 1, 2, 5, 10, 20, 50, 100]
    usable = [c for c in candidates if c * px_per_angstrom <= max_px]
    if not usable:
        bar_ang = candidates[0]
    else:
        bar_ang = usable[-1]

    return bar_ang, int(round(bar_ang * px_per_angstrom))


def _format_angstrom_label(value):
    if value is None:
        return ""
    if abs(value - round(value)) < 1e-8:
        return f"{int(round(value))} Å"
    return f"{value:g} Å"


def _build_edge_adjacency(edges):
    adj = defaultdict(set)
    for a, b in edges:
        a = int(a)
        b = int(b)
        if a == b:
            continue
        adj[a].add(b)
        adj[b].add(a)
    return adj


def _select_context_subgraph(visible_atoms, visible_edges, seed_atoms, u_full=None, v_full=None,
                             max_hops=1, max_atoms=220):
    """
    Select a compact context subgraph around the displayed ring atoms.

    v12 motivation:
      v11 drew the whole local ROI graph in gray, which often produced a dense
      fog of edges on the right panel.  Here we keep only a bounded graph
      neighborhood around the actually displayed colored rings.
    """
    visible_atoms = {int(a) for a in visible_atoms}
    visible_edges = {tuple(sorted((int(a), int(b)))) for a, b in visible_edges}
    seed_atoms = [int(a) for a in seed_atoms if int(a) in visible_atoms]

    if not seed_atoms:
        return set(visible_atoms), set(visible_edges), {}

    adj = _build_edge_adjacency(visible_edges)
    dist = {}
    q = deque()

    for a in seed_atoms:
        if a in dist:
            continue
        dist[a] = 0
        q.append(a)

    while q:
        a = q.popleft()
        if dist[a] >= max_hops:
            continue
        for nb in sorted(adj.get(a, ())):
            if nb not in visible_atoms or nb in dist:
                continue
            dist[nb] = dist[a] + 1
            q.append(nb)

    selected_atoms = [a for a, d in dist.items() if d <= max_hops]

    if max_atoms is not None and len(selected_atoms) > int(max_atoms):
        max_atoms = int(max_atoms)
        if u_full is not None and v_full is not None and seed_atoms:
            cx = float(np.mean(u_full[seed_atoms]))
            cy = float(np.mean(v_full[seed_atoms]))
            selected_atoms = sorted(
                selected_atoms,
                key=lambda a: (dist.get(a, 10**9), float((u_full[a] - cx) ** 2 + (v_full[a] - cy) ** 2), a),
            )[:max_atoms]
        else:
            selected_atoms = sorted(selected_atoms, key=lambda a: (dist.get(a, 10**9), a))[:max_atoms]

    selected_atoms = set(selected_atoms)
    selected_edges = {e for e in visible_edges if e[0] in selected_atoms and e[1] in selected_atoms}
    return selected_atoms, selected_edges, dist


def _draw_depth_aware_local_patch(base_front_img, points_angstrom, numbers, u_full, v_full, z_full,
                                  roi_px, rings, panel_size,
                                  cutoff_scale, margin_px,
                                  max_local_atoms, max_degree,
                                  n_ring_layers=RING_N_LAYERS_DEFAULT,
                                  ring_show_layers=RING_SHOW_LAYERS_DEFAULT,
                                  ring_layer_alpha_falloff=RING_LAYER_ALPHA_FALLOFF_DEFAULT,
                                  ring_layer_scale_falloff=RING_LAYER_SCALE_FALLOFF_DEFAULT,
                                  layer_opacity_boost=0.15,
                                  ring_front_depth=RING_FRONT_DEPTH_MODE_DEFAULT,
                                  ring_context_mode=RING_CONTEXT_MODE_DEFAULT,
                                  ring_context_hops=RING_CONTEXT_HOPS_DEFAULT,
                                  ring_context_max_atoms=RING_CONTEXT_MAX_ATOMS_DEFAULT,
                                  ring_context_edge_alpha=RING_CONTEXT_EDGE_ALPHA_DEFAULT,
                                  ring_context_atom_alpha=RING_CONTEXT_ATOM_ALPHA_DEFAULT):
    """
    Draw the right panel as a paper-style local ring-network analysis panel.

    Design choices in v13:
      - the base crop is kept only as a very faint spatial cue;
      - by default the gray context graph is restricted to the displayed rings
        and their immediate graph neighborhood, instead of the entire ROI graph;
      - the same 5/6/7 palette is used for bonds, atoms and legend;
      - displayed counts refer to the rings actually drawn after depth filtering;
      - the scale bar is estimated from the original Å coordinates, not from the
        already-normalized image coordinates;
      - frontmost depth defaults to high-z, matching the draw order used by
        render(), while --ring-front-depth low-z is available for reversed views;
      - ring atoms and bonds are drawn with strict depth/z-ordering: deeper
        layers are painted first and front layers are painted last.
    """
    if ring_front_depth not in ("high-z", "low-z"):
        raise ValueError("ring_front_depth must be either 'high-z' or 'low-z'.")

    panel_w, panel_h = panel_size
    panel = Image.new("RGBA", (panel_w, panel_h), (255, 255, 255, 255))

    x0, y0, x1, y1 = roi_px
    roi_w = max(1, x1 - x0)
    roi_h = max(1, y1 - y0)

    crop = base_front_img.crop((x0, y0, x1, y1)).convert("RGBA")

    # Keep more breathing room than v10; the legend/scale bar should not feel
    # pressed against the frame in a two-column paper figure.
    panel_padding_x = 94
    panel_padding_y = 92
    sx = (panel_w - 2 * panel_padding_x) / roi_w
    sy = (panel_h - 2 * panel_padding_y) / roi_h
    scale = max(0.1, min(sx, sy))

    zoom_w = max(1, int(round(roi_w * scale)))
    zoom_h = max(1, int(round(roi_h * scale)))

    crop_zoom = crop.resize((zoom_w, zoom_h), Image.Resampling.LANCZOS)

    # Use the raster crop only as a subtle spatial texture.  Scientific category
    # information is carried by the explicit graph overlay below.
    gray = ImageOps.grayscale(crop_zoom.convert("RGB")).filter(ImageFilter.GaussianBlur(1.2))
    light_gray = ImageOps.colorize(gray, black="#F2F4F6", white="#FFFFFF").convert("RGBA")
    crop_zoom = Image.alpha_composite(light_gray, Image.new("RGBA", light_gray.size, (255, 255, 255, 242)))

    # Slightly left-of-center placement leaves room for an internal legend while
    # keeping connector lines short.
    ox = int(round(max(42, (panel_w - zoom_w) * 0.30)))
    oy = int(round((panel_h - zoom_h) / 2))
    panel.paste(crop_zoom, (ox, oy), crop_zoom)

    def map_to_panel_coords(atom_indices):
        atom_indices = np.asarray(atom_indices, dtype=int)
        px = ox + (u_full[atom_indices] - x0) * scale
        py = oy + (v_full[atom_indices] - y0) * scale
        return px, py

    local_atoms, local_edges = _get_local_graph_for_drawing(
        points_angstrom,
        numbers,
        u_full,
        v_full,
        roi_px,
        cutoff_scale=cutoff_scale,
        margin_px=margin_px,
        max_local_atoms=max_local_atoms,
        max_degree=max_degree,
    )

    exact_mask = (
        (u_full[local_atoms] >= x0)
        & (u_full[local_atoms] <= x1)
        & (v_full[local_atoms] >= y0)
        & (v_full[local_atoms] <= y1)
    )
    visible_atoms = set(int(a) for a in local_atoms[exact_mask])

    if len(visible_atoms) == 0:
        draw = ImageDraw.Draw(panel, "RGBA")
        font = load_font(26, bold=True)
        msg = "No carbon atoms inside this ROI"
        bbox = draw.textbbox((0, 0), msg, font=font)
        draw.text(
            ((panel_w - (bbox[2] - bbox[0])) / 2, panel_h / 2),
            msg,
            font=font,
            fill=STYLE["title_rgba"],
        )
        return panel, {5: 0, 6: 0, 7: 0}, (ox, oy, ox + zoom_w, oy + zoom_h)

    visible_edges = set()
    for a, b in local_edges:
        if int(a) in visible_atoms and int(b) in visible_atoms:
            visible_edges.add((int(a), int(b)))

    # ------------------------------------------------------------------
    # Depth-filtered displayed rings.  Counts are computed from this set,
    # not from the raw detected-ring list.
    # ------------------------------------------------------------------
    _n_ring_layers = int(max(1, n_ring_layers))
    _show_layers = _n_ring_layers if ring_show_layers == 0 else int(ring_show_layers)
    _show_layers = max(1, min(_show_layers, _n_ring_layers))

    ring_z_records = []  # (cycle_tuple, size, avg_z)
    for size in (5, 6, 7):
        for cyc in rings.get(size, []):
            cyc_ints = tuple(int(a) for a in cyc)
            if len(cyc_ints) != size:
                continue
            if not all(a in visible_atoms for a in cyc_ints):
                continue
            z_vals = [float(z_full[a]) for a in cyc_ints]
            ring_z_records.append((cyc_ints, int(size), float(sum(z_vals) / len(z_vals))))

    displayed_rings_by_size = {5: [], 6: [], 7: []}
    surface_ring_atoms_by_size = {5: set(), 6: set(), 7: set()}
    surface_ring_edges_by_size = {5: set(), 6: set(), 7: set()}
    ring_atom_min_layer = {}
    ring_edge_min_layer = {}
    ring_atom_front_rank = {}
    ring_edge_front_rank = {}

    def element_front_rank(z_value):
        # Larger front-rank is always visually closer to the viewer.
        z_value = float(z_value)
        return z_value if ring_front_depth == "high-z" else -z_value

    if ring_z_records:
        z_arr = np.array([r[2] for r in ring_z_records], dtype=float)
        z_min = float(z_arr.min())
        z_max = float(z_arr.max())
        z_span = max(z_max - z_min, 1e-6)

        for cyc, size, avg_z in ring_z_records:
            if ring_front_depth == "high-z":
                depth_fraction = (z_max - avg_z) / z_span
            else:
                depth_fraction = (avg_z - z_min) / z_span

            layer = min(int(_n_ring_layers * depth_fraction), _n_ring_layers - 1)
            if layer >= _show_layers:
                continue

            displayed_rings_by_size[size].append(cyc)
            cyc_list = list(cyc)
            for a in cyc_list:
                surface_ring_atoms_by_size[size].add(a)
                a_rank = element_front_rank(z_full[a])
                if (
                    a not in ring_atom_min_layer
                    or layer < ring_atom_min_layer[a]
                    or (layer == ring_atom_min_layer[a] and a_rank > ring_atom_front_rank.get(a, -1e30))
                ):
                    ring_atom_min_layer[a] = layer
                    ring_atom_front_rank[a] = a_rank

            for i in range(len(cyc_list)):
                a = cyc_list[i]
                b = cyc_list[(i + 1) % len(cyc_list)]
                edge = tuple(sorted((a, b)))
                surface_ring_edges_by_size[size].add(edge)
                edge_rank = element_front_rank(0.5 * (float(z_full[a]) + float(z_full[b])))
                if (
                    edge not in ring_edge_min_layer
                    or layer < ring_edge_min_layer[edge]
                    or (layer == ring_edge_min_layer[edge] and edge_rank > ring_edge_front_rank.get(edge, -1e30))
                ):
                    ring_edge_min_layer[edge] = layer
                    ring_edge_front_rank[edge] = edge_rank

    displayed_ring_atoms = set()
    displayed_ring_edges = set()
    for size in (5, 6, 7):
        displayed_ring_atoms.update(surface_ring_atoms_by_size[size])
        displayed_ring_edges.update(surface_ring_edges_by_size[size])

    # ------------------------------------------------------------------
    # Reduced context graph (v12): show only the colored rings and a compact
    # local neighborhood by default, instead of the whole ROI graph.
    # ------------------------------------------------------------------
    if ring_context_mode == "off":
        context_atoms_to_draw = set()
        context_edges_to_draw = set()
    elif ring_context_mode == "full" or not displayed_ring_atoms:
        context_atoms_to_draw = set(visible_atoms)
        context_edges_to_draw = set(visible_edges)
    else:
        context_atoms_to_draw, context_edges_to_draw, _dist = _select_context_subgraph(
            visible_atoms,
            visible_edges,
            displayed_ring_atoms,
            u_full=u_full,
            v_full=v_full,
            max_hops=ring_context_hops,
            max_atoms=ring_context_max_atoms,
        )

    # Do not let the gray context compete with the actual highlighted ring graph.
    context_atoms_to_draw = {int(a) for a in context_atoms_to_draw if int(a) not in displayed_ring_atoms}
    context_edges_to_draw = {
        tuple(sorted((int(a), int(b))))
        for a, b in context_edges_to_draw
        if tuple(sorted((int(a), int(b)))) not in displayed_ring_edges
    }

    if context_edges_to_draw or (ring_context_atom_alpha > 0 and context_atoms_to_draw):
        context_layer = Image.new("RGBA", (panel_w, panel_h), (0, 0, 0, 0))
        context_draw = ImageDraw.Draw(context_layer, "RGBA")

        for a, b in sorted(context_edges_to_draw):
            ax, ay = map_to_panel_coords([a])
            bx, by = map_to_panel_coords([b])
            context_draw.line(
                [(float(ax[0]), float(ay[0])), (float(bx[0]), float(by[0]))],
                fill=(155, 163, 171, int(ring_context_edge_alpha)),
                width=2,
            )

        if ring_context_atom_alpha > 0:
            for a in sorted(context_atoms_to_draw):
                px, py = map_to_panel_coords([a])
                px, py = float(px[0]), float(py[0])
                r = 2.8
                context_draw.ellipse(
                    (px - r, py - r, px + r, py + r),
                    fill=(132, 140, 148, int(ring_context_atom_alpha)),
                )

        panel = Image.alpha_composite(panel, context_layer)

    # Primary atom color: non-hexagonal defect rings should remain visible over
    # normal six-member rings when an atom belongs to multiple rings.
    atom_primary_size = {}
    for size in (6, 7, 5):
        for a in surface_ring_atoms_by_size[size]:
            atom_primary_size[int(a)] = int(size)

    ring_layer = Image.new("RGBA", (panel_w, panel_h), (0, 0, 0, 0))
    ring_draw = ImageDraw.Draw(ring_layer, "RGBA")


    # 控制环样式
    base_bond_alpha = 230
    base_bond_w = 10
    base_halo_w = 17

    base_atom_outline_r = 22  #环外面白圈的半径
    base_atom_r = 16   # 环节点原子半径

    def layer_alpha(layer):
        return max(int(base_bond_alpha * (ring_layer_alpha_falloff ** layer)), 24)

    def layer_scale(layer):
        return max(float(ring_layer_scale_falloff ** layer), 0.22)

    # Atoms: one primary color per atom avoids misleading multi-colored nodes.
    atoms_by_primary = {5: [], 6: [], 7: []}
    for a, size in atom_primary_size.items():
        atoms_by_primary[size].append(a)

    # Strict depth/z-order drawing.
    # Larger layer index = deeper layer.  Draw order is therefore:
    #   deepest layer → ... → frontmost layer
    # Within the same layer, continuous projected Z is used as a tie-breaker.
    # This fixes the visual artifact where deeper atoms could cover front bonds.
    size_priority = {6: 0, 7: 1, 5: 2}
    draw_records = []

    for size in (6, 7, 5):
        for edge in sorted(surface_ring_edges_by_size[size]):
            layer_idx = ring_edge_min_layer.get(edge)
            if layer_idx is None or layer_idx >= _show_layers:
                continue
            draw_records.append((
                int(layer_idx),
                float(ring_edge_front_rank.get(edge, 0.0)),
                0,  # bond first at the same local depth; atoms sit on top of bonds
                size_priority[size],
                int(size),
                edge,
            ))

    for size in (6, 7, 5):
        for a in sorted(atoms_by_primary[size]):
            layer_idx = ring_atom_min_layer.get(a)
            if layer_idx is None or layer_idx >= _show_layers:
                continue
            draw_records.append((
                int(layer_idx),
                float(ring_atom_front_rank.get(a, element_front_rank(z_full[a]))),
                1,  # atom after bond at the same local depth
                size_priority[size],
                int(size),
                int(a),
            ))

    # Sort for painter's algorithm:
    #   - deeper layers first: layer 9, 8, ..., 0
    #   - within a layer, back-to-front continuous z-rank
    #   - bonds before atoms at exactly the same rank
    draw_records.sort(key=lambda rec: (-rec[0], rec[1], rec[2], rec[3]))

    for layer_idx, _front_rank, kind, _size_pri, size, payload in draw_records:
        sc = layer_scale(layer_idx)
        alpha = layer_alpha(layer_idx)

        if kind == 0:
            a, b = payload
            bond_w = max(2, int(round(base_bond_w * sc)))
            halo_w = max(4, int(round(base_halo_w * sc)))
            ax, ay = map_to_panel_coords([a])
            bx, by = map_to_panel_coords([b])
            pts = [(float(ax[0]), float(ay[0])), (float(bx[0]), float(by[0]))]
            ring_draw.line(pts, fill=(255, 255, 255, min(255, alpha + 18)), width=halo_w)
            ring_draw.line(pts, fill=hex_to_rgba(RING_COLORS[size], alpha), width=bond_w)
        else:
            a = payload
            ol_r = max(3, int(round(base_atom_outline_r * sc)))
            r = max(2, int(round(base_atom_r * sc)))
            px, py = map_to_panel_coords([a])
            px, py = float(px[0]), float(py[0])
            ring_draw.ellipse(
                (px - ol_r, py - ol_r, px + ol_r, py + ol_r),
                fill=(255, 255, 255, min(255, alpha + 20)),
            )
            ring_draw.ellipse(
                (px - r, py - r, px + r, py + r),
                fill=hex_to_rgba(RING_ATOM_COLORS[size], alpha),
            )

    panel = Image.alpha_composite(panel, ring_layer)
    draw = ImageDraw.Draw(panel, "RGBA")

    # Paper-like straight frame, intentionally not a rounded UI card.
    outline_color = hex_to_rgb("#787878")
    # 环画框的颜色
    frame_bbox = (
        max(20, ox - 18),
        max(20, oy - 18),
        min(panel_w - 20, ox + zoom_w + 18),
        min(panel_h - 20, oy + zoom_h + 18),
    )
    draw.rectangle(frame_bbox, outline=outline_color, width=2)

    visible_counts = {size: len(displayed_rings_by_size[size]) for size in (5, 6, 7)}

    # ------------------------------------------------------------------
    # Scale bar based on original Å coordinates.  If the local geometry is too
    # degenerate to estimate a slope, skip the bar rather than drawing a wrong one.
    # ------------------------------------------------------------------
    px_per_A = _estimate_panel_pixels_per_angstrom(visible_atoms, points_angstrom, u_full, v_full, scale)
    bar_ang, bar_px = _nice_scale_bar_length(max_px=max(70, int(zoom_w * 0.34)), px_per_angstrom=px_per_A)

    if bar_ang is not None and bar_px is not None and bar_px >= 36:
        sb_font = load_font(23, bold=True)
        sb_x0 = frame_bbox[0] + 44
        sb_y = frame_bbox[3] - 58
        # white halo first, then ink line; this survives both screen viewing and print.
        draw.line([(sb_x0, sb_y), (sb_x0 + bar_px, sb_y)], fill=(255, 255, 255, 240), width=9)
        draw.line([(sb_x0, sb_y), (sb_x0 + bar_px, sb_y)], fill=(44, 48, 52, 255), width=5)
        draw.line([(sb_x0, sb_y - 10), (sb_x0, sb_y + 10)], fill=(44, 48, 52, 255), width=4)
        draw.line([(sb_x0 + bar_px, sb_y - 10), (sb_x0 + bar_px, sb_y + 10)], fill=(44, 48, 52, 255), width=4)

        label = _format_angstrom_label(bar_ang)
        bbox = draw.textbbox((0, 0), label, font=sb_font)
        draw.text(
            (sb_x0 + (bar_px - (bbox[2] - bbox[0])) / 2, sb_y - 40),
            label,
            font=sb_font,
            fill=(44, 48, 52, 255),
            stroke_width=2,
            stroke_fill=(255, 255, 255, 225),
        )

    return panel, visible_counts, frame_bbox


# 控制放大图位置
def render_front_ring_zoom(display_points, display_numbers, display_radius_factors,
                           out_dir, zoom_box=None, view_size=VIEW_SIZE,
                           graph_points_angstrom=None, graph_numbers=None,
                           projection_points=None,
                           cutoff_scale=RING_CUTOFF_SCALE_DEFAULT,
                           margin_px=RING_ROI_MARGIN_PX_DEFAULT,
                           max_local_atoms=RING_MAX_LOCAL_ATOMS_DEFAULT,
                           max_degree=RING_MAX_DEGREE_DEFAULT,
                           max_cycles_per_size=RING_MAX_CYCLES_PER_SIZE_DEFAULT,
                           n_ring_layers=RING_N_LAYERS_DEFAULT,
                           ring_show_layers=RING_SHOW_LAYERS_DEFAULT,
                           ring_layer_alpha_falloff=RING_LAYER_ALPHA_FALLOFF_DEFAULT,
                           ring_layer_scale_falloff=RING_LAYER_SCALE_FALLOFF_DEFAULT,
                           auto_roi=False,
                           layer_opacity_boost=0.15,
                           ring_front_depth=RING_FRONT_DEPTH_MODE_DEFAULT,
                           ring_context_mode=RING_CONTEXT_MODE_DEFAULT,
                           ring_context_hops=RING_CONTEXT_HOPS_DEFAULT,
                           ring_context_max_atoms=RING_CONTEXT_MAX_ATOMS_DEFAULT,
                           ring_context_edge_alpha=RING_CONTEXT_EDGE_ALPHA_DEFAULT,
                           ring_context_atom_alpha=RING_CONTEXT_ATOM_ALPHA_DEFAULT,
                           ring_zoom_scale=RING_ZOOM_SCALE_DEFAULT):
    """
    v13 article-style layout:
      - left full-view model is enlarged by cropping and refitting
      - ROI box and connector lines use neutral navigation styling
      - right panel uses a color-consistent 5/6/7 ring palette
      - legend is placed on the right and only explains ring categories
      - ring_front_depth controls whether high-z or low-z is treated as the visible surface
    """
    print("Step 6/6: Rendering front-view ROI mapping + local ring highlight...")

    front_R = get_three_view_rotations()["Front View"]

    if graph_points_angstrom is None:
        graph_points_angstrom = display_points

    if graph_numbers is None:
        graph_numbers = display_numbers

    if projection_points is None:
        projection_points = display_points

    base_h = int(round(view_size[1] * RING_FIGURE_SCALE))
    left_fig_size = (int(round(base_h * 0.66)), base_h)
    right_render_size = (int(round(base_h * 1.05)), base_h)  # render resolution (keep pixel density)

    saved_alpha_min = ATOM_STYLE["atom_alpha_min"]
    saved_alpha_max = ATOM_STYLE["atom_alpha_max"]
    saved_base_radius = ATOM_STYLE["atom_base_radius_factor"]

    # Left full-view image: do NOT over-fade. User preferred the clearer earlier version.
    try:
        ATOM_STYLE["atom_alpha_min"] = saved_alpha_min
        ATOM_STYLE["atom_alpha_max"] = saved_alpha_max
        ATOM_STYLE["atom_base_radius_factor"] = saved_base_radius * 1.02
        left_front_img_raw = render(
            display_points,
            display_numbers,
            display_radius_factors,
            front_R,
            size=left_fig_size,
            title=None,
            label=None,
            transparent=False,
            white_bg=STYLE["white_bg"],
            enable_glow=False,
            atom_ellipse_stretch=1.0,
        ).convert("RGBA")
    finally:
        ATOM_STYLE["atom_alpha_min"] = saved_alpha_min
        ATOM_STYLE["atom_alpha_max"] = saved_alpha_max
        ATOM_STYLE["atom_base_radius_factor"] = saved_base_radius

    # Right crop source: softened, but still visible.
    try:
        alpha_boost_factor = 1 + float(layer_opacity_boost)
        ATOM_STYLE["atom_alpha_min"] = max(35, int(round(saved_alpha_min * 0.65 * alpha_boost_factor)))
        ATOM_STYLE["atom_alpha_max"] = max(85, int(round(saved_alpha_max * 0.78 * alpha_boost_factor)))
        ATOM_STYLE["atom_base_radius_factor"] = saved_base_radius * 0.92
        right_front_img = render(
            display_points,
            display_numbers,
            display_radius_factors,
            front_R,
            size=right_render_size,
            title=None,
            label=None,
            transparent=False,
            white_bg=STYLE["white_bg"],
            enable_glow=False,
            atom_ellipse_stretch=1.0,
        ).convert("RGBA")
    finally:
        ATOM_STYLE["atom_alpha_min"] = saved_alpha_min
        ATOM_STYLE["atom_alpha_max"] = saved_alpha_max
        ATOM_STYLE["atom_base_radius_factor"] = saved_base_radius

    u_right, v_right, z_right, _view_right = project(projection_points, front_R, right_render_size)

    if zoom_box is None:
        zoom_box_use = get_default_zoom_box()
    else:
        zoom_box_use = zoom_box

    roi_px_right = normalized_box_to_pixels(zoom_box_use, right_render_size)

    # 右面板尺寸 = zoom-box 宽高比 × ring_zoom_scale
    zw = zoom_box_use[2] - zoom_box_use[0]
    zh = zoom_box_use[3] - zoom_box_use[1]
    zoom_aspect = zw / zh if zh > 0 else 1.0
    right_h = int(round(base_h * ring_zoom_scale))
    right_w = max(1, int(round(right_h * zoom_aspect)))
    right_panel_size = (right_w, right_h)

    rings, info = detect_rings_in_roi(
        graph_points_angstrom,
        graph_numbers,
        u_right,
        v_right,
        roi_px_right,
        cutoff_scale=cutoff_scale,
        margin_px=margin_px,
        max_local_atoms=max_local_atoms,
        max_degree=max_degree,
        max_cycles_per_size=max_cycles_per_size,
    )

    if sum(len(rings.get(s, [])) for s in (5, 6, 7)) == 0 and auto_roi:
        print("No rings in the selected/default ROI. Trying local auto-ROI search...")
        auto_roi_px, auto_cycles, auto_info = auto_try_rois(
            graph_points_angstrom,
            graph_numbers,
            u_right,
            v_right,
            right_render_size,
            cutoff_scale=cutoff_scale,
            margin_px=margin_px,
            max_local_atoms=max_local_atoms,
            max_degree=max_degree,
            max_cycles_per_size=max_cycles_per_size,
        )
        if auto_roi_px is not None and sum(len(auto_cycles.get(s, [])) for s in (5, 6, 7)) > 0:
            roi_px_right = auto_roi_px
            rings = auto_cycles
            info = auto_info

    print(
        "Local ring search:"
        f" candidate_atoms={info.get('candidate_atoms', 0):,},"
        f" local_carbon_atoms={info.get('local_carbon_atoms', 0):,},"
        f" local_edges={info.get('local_edges', 0):,}"
    )
    print(
        "Detected in ROI ->"
        f" 5: {len(rings.get(5, []))},"
        f" 6: {len(rings.get(6, []))},"
        f" 7: {len(rings.get(7, []))}"
    )

    # Convert the right ROI normalized coordinates to left panel coordinates.
    roi_norm = (
        roi_px_right[0] / right_render_size[0],
        roi_px_right[1] / right_render_size[1],
        roi_px_right[2] / right_render_size[0],
        roi_px_right[3] / right_render_size[1],
    )
    roi_px_left_raw = normalized_box_to_pixels(roi_norm, left_fig_size)

    # Crop the left panel to enlarge the full model and reduce white margins.
    lxw, lyh = left_fig_size
    crop_box = (
        int(round(lxw * 0.22)),
        int(round(lyh * 0.06)),
        int(round(lxw * 0.78)),
        int(round(lyh * 0.94)),
    )
    cx0, cy0, cx1, cy1 = crop_box
    crop_w = max(1, cx1 - cx0)
    crop_h = max(1, cy1 - cy0)
    sx_left = lxw / crop_w
    sy_left = lyh / crop_h

    left_panel = left_front_img_raw.crop(crop_box).resize(left_fig_size, Image.Resampling.LANCZOS)

    x0r, y0r, x1r, y1r = roi_px_left_raw
    x0l = int(round((x0r - cx0) * sx_left))
    y0l = int(round((y0r - cy0) * sy_left))
    x1l = int(round((x1r - cx0) * sx_left))
    y1l = int(round((y1r - cy0) * sy_left))

    # Clamp after crop transform.
    x0l = max(0, min(left_fig_size[0] - 1, x0l))
    x1l = max(0, min(left_fig_size[0] - 1, x1l))
    y0l = max(0, min(left_fig_size[1] - 1, y0l))
    y1l = max(0, min(left_fig_size[1] - 1, y1l))

    if x1l <= x0l + 4:
        x1l = min(left_fig_size[0] - 1, x0l + 48)
    if y1l <= y0l + 4:
        y1l = min(left_fig_size[1] - 1, y0l + 70)

    left_draw = ImageDraw.Draw(left_panel, "RGBA")

    # ROI is a navigation cue, not a scientific category.  Use neutral ink rather
    # than the ring palette so color semantics remain clean.
    roi_outline = (58, 66, 73, 255)
    roi_halo = (255, 255, 255, 235)

    left_draw.rectangle((x0l, y0l, x1l, y1l), outline=roi_halo, width=11)
    left_draw.rectangle((x0l, y0l, x1l, y1l), outline=roi_outline, width=5)

    roi_font = load_font(30, bold=True)
    tag_x = max(14, min(left_fig_size[0] - 86, x0l))
    tag_y = max(14, y0l - 44)
    left_draw.text(
        (tag_x, tag_y),
        "ROI",
        font=roi_font,
        fill=roi_outline,
        stroke_width=4,
        stroke_fill=(255, 255, 255, 235),
    )

    local_panel, visible_counts, zoom_frame_bbox = _draw_depth_aware_local_patch(
        right_front_img,
        graph_points_angstrom,
        graph_numbers,
        u_right,
        v_right,
        z_right,
        roi_px_right,
        rings,
        right_panel_size,
        cutoff_scale=cutoff_scale,
        margin_px=margin_px,
        max_local_atoms=max_local_atoms,
        max_degree=max_degree,
        n_ring_layers=n_ring_layers,
        ring_show_layers=ring_show_layers,
        ring_layer_alpha_falloff=ring_layer_alpha_falloff,
        ring_layer_scale_falloff=ring_layer_scale_falloff,
        layer_opacity_boost=layer_opacity_boost,
        ring_front_depth=ring_front_depth,
        ring_context_mode=ring_context_mode,
        ring_context_hops=ring_context_hops,
        ring_context_max_atoms=ring_context_max_atoms,
        ring_context_edge_alpha=ring_context_edge_alpha,
        ring_context_atom_alpha=ring_context_atom_alpha,
    )

    # Compact board layout without center divider.  右图的位置
    outer_pad = 24    #左右边距
    gap = 54          #左右面板之间的间距
    top_pad = 16      #顶部标题区
    bottom_pad = 12   #底部留白

    left_w, left_h = left_fig_size
    right_w, right_h = right_panel_size
    legend_gap = 24
    legend_w = 240
    board_w = outer_pad * 2 + left_w + gap + right_w + legend_gap + legend_w

    # 面板位置
    left_x = outer_pad
    left_y = top_pad
    right_x = left_x + left_w + gap
    right_y = top_pad + 50
    legend_x = right_x + right_w + legend_gap
    legend_y = right_y + max(18, right_h - 190)

    board_h = max(left_y + left_h, right_y + right_h, legend_y + 170) + bottom_pad
    board = Image.new("RGBA", (board_w, board_h), STYLE["board_bg_rgba"])
    draw = ImageDraw.Draw(board, "RGBA")

    # No central divider line and no strong outer panel outlines.
    board.paste(left_panel, (left_x, left_y), left_panel)
    board.paste(local_panel, (right_x, right_y), local_panel)

    # Titles drawn AFTER panels so they stay on top layer (not covered by panel edges)
    title_font = load_font(38, bold=True)
    draw.text((left_x, 8), "(a) Full-view projection", font=title_font, fill=STYLE["title_rgba"])
    draw.text((right_x, 8), "(b) Ring-network extracted from ROI", font=title_font, fill=STYLE["title_rgba"])

    def draw_dashed_line(draw_obj, p0, p1, dash=14, gap_len=10, fill=(124, 132, 140, 170), width=2):
        x0, y0 = p0
        x1, y1 = p1
        dx = x1 - x0
        dy = y1 - y0
        dist = (dx * dx + dy * dy) ** 0.5
        if dist < 1e-8:
            return
        ux = dx / dist
        uy = dy / dist
        t = 0.0
        while t < dist:
            t2 = min(dist, t + dash)
            xa = x0 + ux * t
            ya = y0 + uy * t
            xb = x0 + ux * t2
            yb = y0 + uy * t2
            draw_obj.line([(xa, ya), (xb, yb)], fill=fill, width=width)
            t += dash + gap_len

    # Connector lines are neutral navigation aids, not ring-category colors.
    p1 = (left_x + x1l, left_y + y0l)
    p2 = (left_x + x1l, left_y + y1l)
    q1 = (right_x + zoom_frame_bbox[0], right_y + zoom_frame_bbox[1])
    q2 = (right_x + zoom_frame_bbox[0], right_y + zoom_frame_bbox[3])

    line_fill = (124, 132, 140, 170)
    draw_dashed_line(draw, p1, q1, dash=14, gap_len=10, fill=line_fill, width=2)
    draw_dashed_line(draw, p2, q2, dash=14, gap_len=10, fill=line_fill, width=2)

    # ── Legend on the right side ──
    # Keep it outside the right panel so it explains colors without covering structure.
    legend_title_font = load_font(26, bold=True)
    legend_font = load_font(25, bold=False)
    draw.text((legend_x, legend_y), "Rings", font=legend_title_font, fill=(52, 58, 64, 240))

    row_y = legend_y + 42
    swatch_size = 23
    for size, label in [(5, "5-member"), (6, "6-member"), (7, "7-member")]:
        c = hex_to_rgba(RING_COLORS[size], 250)
        draw.rounded_rectangle(
            (legend_x, row_y + 3, legend_x + swatch_size, row_y + swatch_size + 3),
            radius=5,
            fill=c,
            outline=c,
        )
        draw.text(
            (legend_x + swatch_size + 10, row_y),
            label,
            font=legend_font,
            fill=(30, 35, 40, 250),
        )
        row_y += 38

    out_path = out_dir / RING_ZOOM_NAME
    board.convert("RGB").save(out_path, dpi=(600, 600), optimize=True)
    print(f"Saved ring-zoom figure: {out_path}")

    return out_path# =============================================================================
# 13b. Internal tests
# =============================================================================

def _test_cycle_detection_normal_case():
    """
    Normal case:
      A simple 6-cycle should be detected exactly as a 6-member ring.
    """
    graph = defaultdict(set)
    for i in range(6):
        a = i
        b = (i + 1) % 6
        graph[a].add(b)
        graph[b].add(a)

    found = find_cycles_of_sizes_local(
        graph,
        sizes=(5, 6, 7),
        max_cycles_per_size=10,
    )
    found = filter_chordless_cycles(found, graph)

    assert len(found[6]) == 1, f"Expected one 6-ring, got {len(found[6])}"
    assert len(found[5]) == 0, f"Expected zero 5-rings, got {len(found[5])}"
    assert len(found[7]) == 0, f"Expected zero 7-rings, got {len(found[7])}"


def _test_zoom_box_edge_case():
    """
    Edge case:
      A valid ROI near the image boundary should convert to pixels without
      becoming inverted or zero-sized.
    """
    box = validate_zoom_box_or_raise((0.00, 0.02, 0.08, 0.15))
    px = normalized_box_to_pixels(box, (1000, 800))
    x0, y0, x1, y1 = px

    assert x0 == 0, f"Expected x0=0, got {x0}"
    assert x1 > x0, "Pixel ROI width must be positive."
    assert y1 > y0, "Pixel ROI height must be positive."




def _test_fit_roi_to_panel_rectangular_case():
    """
    Edge case:
      A tall rectangular ROI should remain rectangular after fitting, not collapse
      to a circular or square-looking transform.
    """
    roi_px = (100, 120, 180, 360)  # width 80, height 240
    scale, ox, oy = _fit_roi_to_panel(roi_px, (1200, 900), padding=70)
    roi_w = roi_px[2] - roi_px[0]
    roi_h = roi_px[3] - roi_px[1]

    zoom_w = roi_w * scale
    zoom_h = roi_h * scale

    assert zoom_h > zoom_w * 2.0, "Tall rectangular ROI should stay tall after fitting."



def _test_ring_touches_roi_edge_case():
    """
    Edge case:
      A ring whose centroid is outside the ROI but one atom lies inside should
      still count as touching the ROI in v12.
    """
    u = np.array([10.0, 30.0, 50.0, 70.0, 90.0], dtype=float)
    v = np.array([10.0, 10.0, 10.0, 10.0, 10.0], dtype=float)
    roi_px = (0, 0, 20, 20)

    # Atom 0 is inside ROI, the rest are outside.
    ring = (0, 1, 2, 3, 4)

    assert ring_touches_roi(ring, u, v, roi_px) is True



def _test_default_zoom_box_is_small():
    """
    Ensure the default ROI remains relatively small in normalized image area.
    """
    x0, y0, x1, y1 = get_default_zoom_box()
    area = (x1 - x0) * (y1 - y0)
    assert area < 0.01, f"Default ROI should stay small; got normalized area {area:.4f}"



def _test_ring_colors_distinct():
    """
    Ensure the publication palette remains visually distinct.
    """
    c5 = hex_to_rgb(RING_COLORS[5])
    c6 = hex_to_rgb(RING_COLORS[6])
    c7 = hex_to_rgb(RING_COLORS[7])

    assert c5 != c6 and c6 != c7 and c5 != c7, "Ring colors should be distinct."



def _test_layer_opacity_boost_argument_exists():
    """
    Static sanity check:
      render_front_ring_zoom should expose layer_opacity_boost for user tuning.
    """
    import inspect
    sig = inspect.signature(render_front_ring_zoom)
    assert "layer_opacity_boost" in sig.parameters
    assert abs(sig.parameters["layer_opacity_boost"].default - 0.15) < 1e-12
    assert "ring_front_depth" in sig.parameters


def _test_scale_bar_estimation_linear_case():
    """
    A linear 10 px/Å mapping followed by a 2x ROI zoom should give 20 px/Å.
    """
    pts = np.array([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [2.0, 0.0, 0.0], [3.0, 0.0, 0.0]])
    u = np.array([100.0, 110.0, 120.0, 130.0])
    v = np.array([50.0, 50.0, 50.0, 50.0])
    px_per_A = _estimate_panel_pixels_per_angstrom({0, 1, 2, 3}, pts, u, v, panel_scale=2.0)
    assert abs(px_per_A - 20.0) < 1e-8


def _test_context_neighborhood_selection_case():
    """
    Ensure the compact-context selector keeps only a bounded neighborhood.
    """
    visible_atoms = {0, 1, 2, 3, 4}
    visible_edges = {(0, 1), (1, 2), (2, 3), (3, 4)}
    u = np.array([0, 1, 2, 3, 4], dtype=float)
    v = np.array([0, 0, 0, 0, 0], dtype=float)
    selected_atoms, selected_edges, dist = _select_context_subgraph(
        visible_atoms, visible_edges, {2}, u_full=u, v_full=v, max_hops=1, max_atoms=10
    )
    assert selected_atoms == {1, 2, 3}, f"Unexpected selected atoms: {selected_atoms}"
    assert selected_edges == {(1, 2), (2, 3)}, f"Unexpected selected edges: {selected_edges}"
    assert dist[2] == 0 and dist[1] == 1 and dist[3] == 1


def _test_depth_zorder_sort_case():
    """
    Deeper ring layers must be painted before front layers.
    For the same layer, bonds should be painted before atoms at the same local depth.
    """
    records = [
        (0, 0.1, 1, 0),  # front atom
        (2, 9.9, 1, 0),  # deeper atom, even if its continuous rank is large
        (0, 0.1, 0, 0),  # front bond at same rank
        (1, 2.0, 0, 0),
    ]
    ordered = sorted(records, key=lambda rec: (-rec[0], rec[1], rec[2], rec[3]))
    assert ordered[0][0] == 2, "Deepest layer should be drawn first."
    assert ordered[-1] == (0, 0.1, 1, 0), "Front atom should be drawn after its same-depth bond."


def _test_publication_palette_values():
    """
    Check that the publication palette uses non-background-like colors.
    """
    assert RING_COLORS[6].lower() != "#38a271", "6-ring color should not match the old green background."
    assert RING_COLORS[5].startswith("#") and RING_COLORS[7].startswith("#")

def run_internal_tests():
    print("Running internal tests...")
    _test_cycle_detection_normal_case()
    print("  OK: cycle detection normal case")
    _test_zoom_box_edge_case()
    print("  OK: zoom-box edge case")
    _test_fit_roi_to_panel_rectangular_case()
    print("  OK: rectangular ROI fitting case")
    _test_ring_touches_roi_edge_case()
    print("  OK: ring touch ROI edge case")
    _test_default_zoom_box_is_small()
    print("  OK: default ROI smallness case")
    _test_ring_colors_distinct()
    print("  OK: ring color distinction case")
    _test_publication_palette_values()
    print("  OK: publication palette case")
    _test_context_neighborhood_selection_case()
    print("  OK: compact context neighborhood case")
    _test_depth_zorder_sort_case()
    print("  OK: depth z-order sort case")
    _test_layer_opacity_boost_argument_exists()
    print("  OK: layer opacity boost argument case")
    _test_scale_bar_estimation_linear_case()
    print("  OK: scale bar estimation case")
    print("All internal tests passed.")

# =============================================================================
# 14. CLI / main flow
# =============================================================================

def parse_args():
    parser = argparse.ArgumentParser(
        description="Render an ASE-readable atomic structure as carbon-style PNG views, optional GIF, and front-view ring zoom."
    )

    parser.add_argument(
        "structure",
        nargs="?",
        default="opted.xyz",
        help="Input structure file readable by ASE, e.g. xyz, extxyz, cif, POSCAR, traj."
    )

    parser.add_argument(
        "--style",
        default=ACTIVE_STYLE,
        choices=sorted(STYLE_PRESETS.keys()),
        help="Color style preset."
    )

    parser.add_argument(
        "--atom-style",
        default=ACTIVE_ATOM_STYLE,
        choices=sorted(ATOM_PRESETS.keys()),
        help="Atom rendering style preset."
    )

    parser.add_argument(
        "--out-dir",
        default=str(OUT_DIR),
        help="Output directory."
    )

    parser.add_argument(
        "--gif",
        action="store_true",
        help="Render rotating GIF. OFF by default because it is slow."
    )

    parser.add_argument(
        "--views",
        action="store_true",
        help="Render Front / Top / Side PNGs. Off by default."
    )

    parser.add_argument(
        "--board",
        action="store_true",
        help="Render the combined three-view board PNG. Off by default."
    )

    parser.add_argument(
        "--no-pca",
        action="store_true",
        help="Disable PCA auto-alignment."
    )

    parser.add_argument(
        "--max-points",
        type=int,
        default=MAX_POINTS,
        help="Maximum rendered atoms after random downsampling."
    )

    parser.add_argument(
        "--read-index",
        default=ASE_READ_INDEX,
        help="ASE read index. Use -1 for last frame, 0 for first frame, etc."
    )

    parser.add_argument(
        "--ring-zoom",
        action="store_true",
        help="Render the extra front-view local zoom figure with 5/6/7-member ring annotation."
    )

    parser.add_argument(
        "--no-ring-zoom",
        action="store_true",
        help="Skip the extra front-view local zoom figure."
    )

    parser.add_argument(
        "--zoom-box",
        type=float,
        nargs=4,
        metavar=("X0", "Y0", "X1", "Y1"),
        help="Normalized front-view ROI box in [0,1], e.g. --zoom-box 0.35 0.30 0.65 0.68"
    )

    parser.add_argument(
        "--ring-cutoff-scale",
        type=float,
        default=RING_CUTOFF_SCALE_DEFAULT,
        help=(
            "C-C neighbor cutoff scale. ASE connects C-C if distance < "
            "2 * covalent_radius_C * scale. Default: 1.22"
        )
    )

    parser.add_argument(
        "--ring-roi-margin-px",
        type=int,
        default=RING_ROI_MARGIN_PX_DEFAULT,
        help="Extra pixel margin around the ROI for local ring detection. Default: 90"
    )

    parser.add_argument(
        "--ring-max-local-atoms",
        type=int,
        default=RING_MAX_LOCAL_ATOMS_DEFAULT,
        help="Maximum carbon atoms used for local ring detection. Default: 1200"
    )

    parser.add_argument(
        "--ring-max-degree",
        type=int,
        default=RING_MAX_DEGREE_DEFAULT,
        help="Maximum C-C graph degree retained per atom. Default: 4"
    )

    parser.add_argument(
        "--ring-n-layers",
        type=int,
        default=RING_N_LAYERS_DEFAULT,
        help="Number of equal Z-depth layers for ring filtering. Higher = thinner surface slice. Default: 3"
    )

    parser.add_argument(
        "--ring-show-layers",
        type=int,
        default=RING_SHOW_LAYERS_DEFAULT,
        help="How many of the frontmost Z layers to display. Default: 1 (only the top layer). "
             "Use 0 to show all layers."
    )

    parser.add_argument(
        "--ring-front-depth",
        choices=("high-z", "low-z"),
        default=RING_FRONT_DEPTH_MODE_DEFAULT,
        help=(
            "Which projected Z side is treated as the front surface for ring-layer filtering. "
            "Default: high-z, matching the drawing order in render(). Use low-z if your view is reversed."
        )
    )

    parser.add_argument(
        "--ring-layer-alpha-falloff",
        type=float,
        default=RING_LAYER_ALPHA_FALLOFF_DEFAULT,
        help="Per-layer alpha decay factor (0.0–1.0). "
             "Each deeper layer multiplies alpha by this factor. "
             "Default: 1.0 (no decay). "
             "e.g. 0.6 → layer 0: full alpha, layer 1: 60%%, layer 2: 36%%."
    )

    parser.add_argument(
        "--ring-layer-scale-falloff",
        type=float,
        default=RING_LAYER_SCALE_FALLOFF_DEFAULT,
        help="Per-layer size decay factor (0.0–1.0). "
             "Each deeper layer multiplies bond width and atom radius by this factor. "
             "Default: 1.0 (no decay). "
             "e.g. 0.8 → layer 0: full size, layer 1: 80%%, layer 2: 64%%. "
             "Combined with --ring-layer-alpha-falloff for stronger 3D depth."
    )

    parser.add_argument(
        "--ring-max-cycles-per-size",
        type=int,
        default=RING_MAX_CYCLES_PER_SIZE_DEFAULT,
        help="Maximum detected cycles per ring size inside the ROI. Default: 120"
    )

    parser.add_argument(
        "--ring-zoom-scale",
        type=float,
        default=RING_ZOOM_SCALE_DEFAULT,
        help="Scale factor for the right ring-zoom panel (0.2–3.0). "
             "The panel's aspect ratio always matches the --zoom-box aspect ratio. "
             "Default: 1.0. e.g. 0.7 → 70%% of default height."
    )

    parser.add_argument(
        "--ring-auto-roi",
        action="store_true",
        help="Try several local ROIs if the selected/default ROI contains no 5/6/7 rings. Still local, not global."
    )

    parser.add_argument(
        "--layer-opacity-boost",
        type=float,
        default=0.08,
        help=(
            "Increase far/mid/near layer opacity in the ring-zoom panel. "
            "Default 0.08 means +8%% opacity. Use 0 to disable."
        )
    )

    parser.add_argument(
        "--ring-context-mode",
        choices=("neighbors", "full", "off"),
        default=RING_CONTEXT_MODE_DEFAULT,
        help=(
            "How much gray structural context to show in the right ROI panel. "
            "neighbors = only displayed rings and their local graph neighborhood (recommended); "
            "full = full local ROI graph; off = no explicit gray graph."
        )
    )

    parser.add_argument(
        "--ring-context-hops",
        type=int,
        default=RING_CONTEXT_HOPS_DEFAULT,
        help="Graph hops included around the displayed rings when --ring-context-mode neighbors. Default: 1"
    )

    parser.add_argument(
        "--ring-context-max-atoms",
        type=int,
        default=RING_CONTEXT_MAX_ATOMS_DEFAULT,
        help="Maximum gray-context atoms kept in neighbors mode. Lower values make the right panel cleaner. Default: 220"
    )

    parser.add_argument(
        "--ring-context-edge-alpha",
        type=int,
        default=RING_CONTEXT_EDGE_ALPHA_DEFAULT,
        help="Gray-context bond alpha in the right panel (0–255). Default: 34"
    )

    parser.add_argument(
        "--ring-context-atom-alpha",
        type=int,
        default=RING_CONTEXT_ATOM_ALPHA_DEFAULT,
        help="Gray-context atom alpha in the right panel (0–255). Default: 0 (hide gray atoms for a cleaner paper figure)"
    )

    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run internal tests and exit without reading a structure file."
    )

    return parser.parse_args()


def main():
    """
    Main flow:
      Step 1: Read the structure with ASE.
      Step 2: PCA-align coordinates, then keep two coordinate arrays:
              - points_aligned_angstrom: physical Å coordinates for ring graph
              - full_render_points: normalized coordinates for rendering/projection
      Step 3: Downsample only the display points if needed.
      Step 4: Render static three-view PNGs, and optionally render GIF.
      Step 5: Render combined three-view board.
      Step 6: Optionally render front-view local zoom with ring annotation.
    """
    global STYLE, ATOM_STYLE

    args = parse_args()

    if args.run_tests:
        # Load minimal default style objects required by helper functions.
        STYLE = load_style(args.style)
        ATOM_STYLE = load_atom_style(args.atom_style)
        run_internal_tests()
        return

    validate_ring_options_or_raise(args)
    validated_zoom_box = validate_zoom_box_or_raise(args.zoom_box) if args.zoom_box is not None else None

    structure_path = Path(args.structure)
    if not structure_path.exists():
        raise FileNotFoundError(f"Input structure file does not exist: {structure_path}")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    STYLE = load_style(args.style)
    ATOM_STYLE = load_atom_style(args.atom_style)

    print("=" * 80)
    print("ASE renderer started")
    print(f"Input file  : {structure_path}")
    print(f"Output dir  : {out_dir}")
    print(f"Color style : {args.style}")
    print(f"Atom style  : {args.atom_style}")
    print(f"Render GIF  : {bool(args.gif)}")
    print("=" * 80)

    print("Step 1/6: Reading structure with ASE...")
    atoms, raw_points, numbers = load_atoms_with_ase(structure_path, read_index=args.read_index)

    print(f"ASE formula : {atoms.get_chemical_formula()}")
    print(f"Loaded atoms: {len(raw_points):,}")

    print("Step 2/6: Aligning and normalizing coordinates...")

    if not args.no_pca and PCA_ALIGN:
        points_aligned_angstrom = pca_align(raw_points, axis_perm=AXIS_PERM)
        print(f"PCA aligned with AXIS_PERM = {AXIS_PERM}")
    else:
        points_aligned_angstrom = raw_points - raw_points.mean(axis=0, keepdims=True)
        print("PCA alignment skipped.")

    # This normalized array is used for rendering and for image-space projection.
    # Do not use it for C-C neighbor cutoff, because normalization destroys Å units.
    full_render_points = normalize_points(points_aligned_angstrom.copy())

    print("Step 3/6: Preparing render data...")

    display_points, display_numbers = downsample_if_needed(
        full_render_points,
        numbers,
        max_points=args.max_points,
        seed=7,
    )

    if len(display_points) < len(raw_points):
        print(f"Downsampled display atoms to: {len(display_points):,}")
        print("Ring detection still uses the full local ROI graph, not the display downsample.")

    display_radius_factors = get_atom_radius_factors(display_numbers)

    single_images = None

    if args.views and RENDER_THREE_VIEWS:
        single_images = render_three_views(display_points, display_numbers, display_radius_factors, out_dir)
    else:
        print("Step 4b/6: Three-view PNG rendering skipped.")

    if args.gif or RENDER_GIF:
        render_gif(display_points, display_numbers, display_radius_factors, out_dir)
    else:
        print("Step 4a/6: GIF skipped. Use --gif when you need the animation.")

    if args.board and RENDER_BOARD:
        if single_images is None:
            single_images = render_three_views(display_points, display_numbers, display_radius_factors, out_dir)
        render_three_view_board(single_images, len(display_points), out_dir)
    else:
        print("Step 5/6: Three-view board skipped.")

    do_ring_zoom = False
    if args.no_ring_zoom:
        do_ring_zoom = False
    elif args.ring_zoom or RENDER_RING_ZOOM:
        do_ring_zoom = True

    if do_ring_zoom:
        zoom_box = validated_zoom_box

        render_front_ring_zoom(
            display_points,
            display_numbers,
            display_radius_factors,
            out_dir,
            zoom_box=zoom_box,
            graph_points_angstrom=points_aligned_angstrom,
            graph_numbers=numbers,
            projection_points=full_render_points,
            cutoff_scale=args.ring_cutoff_scale,
            margin_px=args.ring_roi_margin_px,
            max_local_atoms=args.ring_max_local_atoms,
            max_degree=args.ring_max_degree,
            max_cycles_per_size=args.ring_max_cycles_per_size,
            n_ring_layers=args.ring_n_layers,
            ring_show_layers=args.ring_show_layers,
            ring_layer_alpha_falloff=args.ring_layer_alpha_falloff,
            ring_layer_scale_falloff=args.ring_layer_scale_falloff,
            auto_roi=args.ring_auto_roi,
            layer_opacity_boost=args.layer_opacity_boost,
            ring_front_depth=args.ring_front_depth,
            ring_context_mode=args.ring_context_mode,
            ring_context_hops=args.ring_context_hops,
            ring_context_max_atoms=args.ring_context_max_atoms,
            ring_context_edge_alpha=args.ring_context_edge_alpha,
            ring_context_atom_alpha=args.ring_context_atom_alpha,
            ring_zoom_scale=args.ring_zoom_scale,
        )
    else:
        print("Step 6/6: Ring zoom figure skipped.")

    print("=" * 80)
    print("Done.")
    print("=" * 80)




if __name__ == "__main__":
    main()

