# ======================================================================
# File:         exhibitEnvFunction.sh
# Project:      NebulaFlow
# Description:  OVITO 科研可视化函数库 — 差分电荷密度 / 轨迹 GIF / 碳纤维渲染
#               Scientific visualization with OVITO: differential charge
#               density maps, trajectory-to-GIF, and carbon fiber rendering.
# Author:       rebreath
# Dependencies: ovitos (OVITO Python interpreter), python3, pillow, numpy
# ======================================================================


_EXHIBIT_LIB="$HOME/.rebreath/exhibit_lib"


# =============================================================================
# SECTION 1: Differential Charge Density / 差分电荷密度
# =============================================================================

# ---------------------------------------------------------------------------
# Function: exhibit_diff_charge
# 功能: 使用 OVITO 渲染出版级差分电荷密度图（PNG + GIF 双面板）
#       左侧 = 原子结构（球棍模型），右侧 = 差分电荷等值面（Δρ > 0 积累 / < 0 耗尽）
# 场景: 在 Gaussian Cube 格式的差分电荷密度文件上运行，一键生成论文级别的
#       电荷密度可视化，自动处理等值面、光照、摄像机旋转动画。
# Usage: exhibit_diff_charge <cube_file> [options]
# Options:
#   --level FLOAT    等值面绝对值（默认自动根据 percentile 选取）
#   --quality STR    渲染质量: draft | normal | high（默认 normal）
#   --frames INT     GIF 帧数（默认 72）
#   --fps INT        GIF 帧率（默认 12）
#   --width INT      画布宽度（默认 1800）
#   --height INT     画布高度（默认 980）
#   --elev FLOAT     摄像机仰角（默认 17.0）
#   --spin-axis STR  旋转轴: auto | x | y | z（默认 auto，自动取 PCA 主轴）
#   --alpha-pos FLOAT 正电荷等值面透明度 0-1（默认 0.46）
#   --alpha-neg FLOAT 负电荷等值面透明度 0-1（默认 0.36）
#   --prefix STR     输出文件名前缀（默认基于 cube 文件名）
#   --no-png         不输出 PNG
#   --no-gif         不输出 GIF
# Example:
#   exhibit_diff_charge diff.cube
#   exhibit_diff_charge diff.cube --level 0.005 --quality high --frames 120
#   exhibit_diff_charge diff.cube --quality draft  # 快速预览
# ---------------------------------------------------------------------------
exhibit_diff_charge() {
    local script_path="$_EXHIBIT_LIB/exhibit_diff_charge_ovito.py"

    if [[ ! -f "$script_path" ]]; then
        echo "❌ 未找到渲染脚本: $script_path"
        echo "   请检查 NebulaFlow/exhibit_lib/ 路径"
        return 1
    fi

    if [[ $# -lt 1 ]]; then
        echo "用法: exhibit_diff_charge <cube_file> [options]"
        echo "  运行 exhibit_diff_charge --help 查看完整参数"
        return 1
    fi

    echo "=== 📊 差分电荷密度渲染 ==="
    ovitos "$script_path" "$@"
}


# =============================================================================
# SECTION 2: Trajectory GIF / 轨迹动画
# =============================================================================

# ---------------------------------------------------------------------------
# Function: exhibit_traj_gif
# 功能: 使用 OVITO 将原子轨迹文件渲染为出版级 GIF / PNG 动画
#       支持 xyz / extxyz / LAMMPS dump / LAMMPS trajectory 等多种格式，
#       可选 ASE reader 作为补充读入后端。
# 场景: MD 模拟完成后，将轨迹文件(traj.xyz/dump.lammpstrj等)快速渲染成
#       带图例的发布级动画，可直接用于 PPT/论文支撑材料。
# Usage: exhibit_traj_gif <traj_file> [options]
# Options:
#   --quality STR       渲染质量: draft | normal | high（默认 draft）
#   --max-frames INT    最多渲染帧数（均匀采样，默认全帧）
#   --start INT         起始帧（默认 0）
#   --stride INT        步长（默认 1）
#   --fps INT           GIF 帧率（默认 12）
#   --width INT         画布宽度（默认 1200）
#   --height INT        画布高度（默认 760）
#   --azim FLOAT        方位角（默认 35.0）
#   --elev FLOAT        仰角（默认 18.0）
#   --atom-scale FLOAT  原子缩放（默认 1.0）
#   --no-bonds          不显示化学键
#   --output-dir DIR    输出目录
#   --suffix STR        输出文件名后缀（默认 _ovito_traj）
#   --no-png            不输出 PNG
#   --no-gif            不输出 GIF
#   --title STR         图表标题（默认 auto=文件名）
#   --no-title          无标题
# Example:
#   exhibit_traj_gif traj.xyz
#   exhibit_traj_gif dump.lammpstrj --max-frames 120 --quality normal
#   exhibit_traj_gif traj.xyz --no-bonds --no-title --width 800 --height 600
# ---------------------------------------------------------------------------
exhibit_traj_gif() {
    local script_path="$_EXHIBIT_LIB/exhibit_traj_gif_ovito.py"

    if [[ ! -f "$script_path" ]]; then
        echo "❌ 未找到渲染脚本: $script_path"
        echo "   请检查 NebulaFlow/exhibit_lib/ 路径"
        return 1
    fi

    if [[ $# -lt 1 ]]; then
        echo "用法: exhibit_traj_gif <traj_file> [options]"
        echo "  运行 exhibit_traj_gif --help 查看完整参数"
        return 1
    fi

    echo "=== 🎬 轨迹动画渲染 ==="
    ovitos "$script_path" "$@"
}


# =============================================================================
# SECTION 3: Carbon Fiber Render / 碳纤维结构渲染（ASE + Pillow）
# =============================================================================

# ---------------------------------------------------------------------------
# Function: exhibit_cf_render
# 功能: 使用 ASE + Pillow 渲染出版级碳纤维结构图，支持三视图、board 组合
#       面板、以及带 5/6/7 元环标注的 ROI 局部放大图。
# 场景: 碳纤维多尺度模拟后，将 opted.xyz / POSCAR 等结构文件渲染成论文级
#       可视化，支持环网络标注、Z 深度分层控制、局部放大等高级功能。
# 依赖: pip install ase numpy pillow imageio
# Usage: exhibit_cf_render <structure_file> [options]
# Options:
#   --style STR              配色预设: emerald_paper | paper_green |
#                            professional_black | publication（默认 emerald_paper）
#   --atom-style STR         原子渲染风格: dense_fiber | balanced | bold_balls
#                            （默认 dense_fiber）
#   --zoom-box X0 Y0 X1 Y1  归一化 ROI 框 [0,1]×[0,1]，例如
#                            --zoom-box 0.512 0.645 0.578 0.715
#   --out-dir DIR            输出目录（默认 carbon_render_output_ase）
#
#   【视图控制】
#   --views                  渲染 Front / Top / Side 单张 PNG（默认不渲染）
#   --board                  渲染组合三视图面板（默认不渲染）
#   --gif                    渲染旋转 GIF（较慢，默认关闭）
#   --no-pca                 禁用 PCA 自动对齐
#   --max-points N           最大渲染原子数（默认 70000）
#   --read-index INDEX       ASE 读取帧索引（默认 -1=最后一帧）
#
#   【环放大图控制】
#   --ring-zoom              渲染环放大图（需搭配 --zoom-box 使用）
#   --no-ring-zoom           跳过环放大图
#   --ring-n-layers N        Z 深度分层数（默认 3，越大每层越薄）
#   --ring-show-layers N     展示前 N 层环（默认 1；0=全部）
#   --ring-max-local-atoms N 局部环检测最大碳原子数（默认 1200）
#   --ring-max-degree N      每个 C 原子最多保留 N 根键（默认 4）
#   --ring-layer-alpha-falloff N  逐层透明度衰减（0.0–1.0，默认 1.0=无衰减）
#   --ring-layer-scale-falloff N  逐层尺寸衰减（0.0–1.0，默认 1.0=无衰减）
#   --layer-opacity-boost N  放大图透明度增量（默认 0.08=+8%）
#   --ring-zoom-scale N      放大图缩放系数（0.2–3.0，默认 1.0）
#   --ring-auto-roi          ROI 无环时自动尝试附近区域
#   --ring-context-mode MODE 上下文模式: neighbors | full | off
#                            （默认 neighbors）
#   --ring-cutoff-scale N    C-C 键截断系数（默认 1.22）
#   --ring-roi-margin-px N   ROI 外扩像素（默认 90）
#   --ring-front-depth MODE  Z 深度方向: high-z | low-z（默认 high-z）
#
# Examples:
#   # 快速调试环检测（仅环放大图）
#   exhibit_cf_render opted.xyz --zoom-box 0.512 0.645 0.578 0.715
#
#   # 仅表面一层环（最干净）
#   exhibit_cf_render opted.xyz --ring-n-layers 16 --ring-show-layers 1 \
#       --ring-max-degree 3 --ring-max-local-atoms 800 \
#       --layer-opacity-boost 0.30 \
#       --zoom-box 0.512 0.645 0.578 0.715
#
#   # 三视图 + board + 环放大图全套
#   exhibit_cf_render opted.xyz --views --board \
#       --zoom-box 0.35 0.30 0.65 0.68 \
#       --ring-n-layers 12 --ring-show-layers 2
#
#   # 指定配色和原子风格
#   exhibit_cf_render POSCAR --style professional_black --atom-style bold_balls \
#       --views --board --zoom-box 0.4 0.3 0.6 0.7
# ---------------------------------------------------------------------------
exhibit_cf_render() {
    local script_path="$_EXHIBIT_LIB/render_cf-v13_final.py"

    if [[ ! -f "$script_path" ]]; then
        echo "❌ 未找到渲染脚本: $script_path"
        echo "   请检查 NebulaFlow/exhibit_lib/ 路径"
        return 1
    fi

    if [[ $# -lt 1 ]]; then
        echo "用法: exhibit_cf_render <structure_file> [options]"
        echo "  运行 exhibit_cf_render --help 查看完整参数"
        return 1
    fi

    echo "=== 🧶 碳纤维结构渲染 ==="
    python3 "$script_path" "$@"
}
