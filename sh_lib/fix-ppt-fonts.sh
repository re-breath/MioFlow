#!/bin/bash
# ==============================================================================
# fix-ppt-fonts.sh — PPTX 字体批量替换（纯 bash 版）
# 中文 → 微软雅黑，英文/数字/符号 → Times New Roman
#
# 原理：PPTX = ZIP 包，解压后直接修改 XML 中的字体定义
# 无需安装 Office / PowerShell / Python，只要有 unzip+zip+sed 就行
#
# 用法：
#   ./fix-ppt-fonts.sh -i presentation.pptx
#   ./fix-ppt-fonts.sh -i in.pptx -o out.pptx -c "思源黑体" -l "Arial"
#
# 适用于 MioFlow / WSL / Git Bash / Linux / macOS
# ==============================================================================

set -euo pipefail

VERSION="1.0.0"

usage() {
    cat <<EOF
用法: $(basename "$0") -i INPUT [选项]

必要参数:
    -i, --input FILE       输入 .pptx 文件路径

选项:
    -o, --output FILE      输出路径（默认覆盖原文件）
    -c, --cjk FONT         中文字体名（默认"微软雅黑"）
    -l, --latin FONT       英文字体名（默认"Times New Roman"）
    -v, --verbose          显示详细替换信息
    -h, --help             显示此帮助

示例:
    $(basename "$0") -i presentation.pptx
    $(basename "$0") -i in.pptx -o out.pptx
    $(basename "$0") -i in.pptx -c "Noto Sans CJK SC" -l "Arial"
EOF
    exit 0
}

# ---- 颜色输出 ----
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info()  { echo -e "${CYAN}$1${NC}"; }
ok()    { echo -e "${GREEN}$1${NC}"; }
warn()  { echo -e "${YELLOW}$1${NC}"; }
err()   { echo -e "${RED}$1${NC}" >&2; }

# ====== 参数解析 ======
INPUT=""
OUTPUT=""
CJK_FONT="微软雅黑"
LATIN_FONT="Times New Roman"
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        -i|--input)    INPUT="$2";          shift 2 ;;
        -o|--output)   OUTPUT="$2";         shift 2 ;;
        -c|--cjk)      CJK_FONT="$2";       shift 2 ;;
        -l|--latin)    LATIN_FONT="$2";     shift 2 ;;
        -v|--verbose)  VERBOSE=true;         shift ;;
        -h|--help)     usage ;;
        *) err "❌ 未知参数: $1"; usage ;;
    esac
done

# ====== 前置检查 ======
[[ -z "$INPUT" ]] && { err "❌ 请指定输入文件 (-i)"; usage; }
[[ ! -f "$INPUT" ]] && { err "❌ 文件不存在: $INPUT"; exit 1; }

# 检查必需命令
for cmd in unzip zip sed grep find dirname basename realpath; do
    command -v "$cmd" &>/dev/null || { err "❌ 缺少必需工具: $cmd（请先安装）"; exit 1; }
done

INPUT="$(realpath "$INPUT")"
if [[ -z "$OUTPUT" ]]; then
    OUTPUT="$INPUT"
else
    OUTDIR="$(dirname "$(realpath "$OUTPUT" 2>/dev/null || realpath "$(dirname "$OUTPUT")")" 2>/dev/null)"
    mkdir -p "$OUTDIR"
    OUTPUT="$OUTDIR/$(basename "$OUTPUT")"
fi

info "📂 输入: $INPUT"
info "📂 输出: $OUTPUT"
info "📝 中文 → ${CJK_FONT}  |  英文 → ${LATIN_FONT}"

# ====== 开始处理 ======
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

info "📦 解压 PPTX..."
unzip -q "$INPUT" -d "$WORKDIR/pptx"

# ====== 核心替换逻辑 ======
stats_mod=0
stats_skip=0

font_sub() {
    local file="$1"
    local relpath="${file#$WORKDIR/pptx/}"
    local modified=false

    # 只处理可能含字体定义的 XML
    case "$relpath" in
        ppt/slides/*.xml)         ;;
        ppt/slidesMasters/*.xml)  ;;
        ppt/slideLayouts/*.xml)   ;;
        ppt/notesSlides/*.xml)    ;;
        ppt/notesMasters/*.xml)   ;;
        ppt/theme/theme*.xml)     ;;
        ppt/slideMasters/*.xml)   ;;
        *)                         return 1 ;;  # 跳过
    esac

    # ==== 1. 替换 <a:latin typeface="xxx"/> → Times New Roman ====
    #    处理双引号
    if grep -q 'a:latin typeface=' "$file" 2>/dev/null; then
        sed -i "s|\(<a:latin typeface=\"\)[^\"]*\(\"\)|\1${LATIN_FONT}\2|g" "$file"
        modified=true
    fi
    #    处理单引号
    if grep -q "a:latin typeface='" "$file" 2>/dev/null; then
        sed -i "s|\(<a:latin typeface='\)[^']*\('\)|\1${LATIN_FONT}\2|g" "$file"
        modified=true
    fi

    # ==== 2. 替换 <a:ea typeface="xxx"/> → 微软雅黑 ====
    if grep -q 'a:ea typeface=' "$file" 2>/dev/null; then
        sed -i "s|\(<a:ea typeface=\"\)[^\"]*\(\"\)|\1${CJK_FONT}\2|g" "$file"
        modified=true
    fi
    if grep -q "a:ea typeface='" "$file" 2>/dev/null; then
        sed -i "s|\(<a:ea typeface='\)[^']*\('\)|\1${CJK_FONT}\2|g" "$file"
        modified=true
    fi

    # ==== 3. 处理 <a:cs typeface="xxx"/> → 也改成 Times New Roman ====
    #     CS = Complex Script（阿拉伯/希伯来等），一般保持与 Latin 一致
    if grep -q 'a:cs typeface=' "$file" 2>/dev/null; then
        sed -i "s|\(<a:cs typeface=\"\)[^\"]*\(\"\)|\1${LATIN_FONT}\2|g" "$file"
        sed -i "s|\(<a:cs typeface='\)[^']*\('\)|\1${LATIN_FONT}\2|g" "$file"
        modified=true
    fi

    # ==== 4. 处理内联属性形式 a:rPr latin="xxx" ea="xxx" ====
    #     PPTX 中 latin= 和 ea= 只有字体上下文出现
    if grep -q ' latin="' "$file" 2>/dev/null; then
        sed -i "s|\( latin=\"\)[^\"]*\(\"\)\(.*/\?>\)|\1${LATIN_FONT}\2\3|g" "$file"
        modified=true
    fi
    if grep -q ' ea="' "$file" 2>/dev/null; then
        sed -i "s|\( ea=\"\)[^\"]*\(\"\)\(.*/\?>\)|\1${CJK_FONT}\2\3|g" "$file"
        modified=true
    fi

    if $modified; then
        return 0
    else
        return 1
    fi
}

# 处理所有内容 XML
while IFS= read -r -d '' xmlfile; do
    if font_sub "$xmlfile"; then
        : $((stats_mod++))
        $VERBOSE && echo "   ✓ ${xmlfile#$WORKDIR/pptx/}"
    else
        : $((stats_skip++))
    fi
done < <(find "$WORKDIR/pptx" -name "*.xml" -print0 2>/dev/null || true)

# 额外处理：主题文件（可能有额外的 fontScheme 结构）
while IFS= read -r -d '' theme_file; do
    if grep -q 'a:fontScheme\|a:majorFont\|a:minorFont' "$theme_file" 2>/dev/null; then
        sed -i "s|\(<a:latin typeface=\"\)[^\"]*\(\"\)|\1${LATIN_FONT}\2|g" "$theme_file"
        sed -i "s|\(<a:ea typeface=\"\)[^\"]*\(\"\)|\1${CJK_FONT}\2|g" "$theme_file"
        $VERBOSE && echo "   ★ ${theme_file#$WORKDIR/pptx/}（主题字体）"
    fi
done < <(find "$WORKDIR/pptx/ppt/theme" -name "*.xml" -print0 2>/dev/null || true)

# ====== 重打包 ======
info "📦 重新打包 PPTX..."
cd "$WORKDIR/pptx"
rm -f "$OUTPUT"

# 注意：Office 要求 ZIP 的第一个文件是 [Content_Types].xml
zip -q -X -0 "$OUTPUT" "[Content_Types].xml" 2>/dev/null || true

# 用 -X 排除额外文件元数据，保持干净
zip -q -X -r "$OUTPUT" . -x "[Content_Types].xml" -x "*.DS_Store" -x "*Thumbs.db" 2>/dev/null
cd - > /dev/null

# ====== 结果 ======
echo ""
ok "✅ 完成！"
info "   处理文件: ${stats_mod} 个（跳过 ${stats_skip} 个无关文件）"
info "   中文 → ${CJK_FONT}"
info "   英文 → ${LATIN_FONT}"

# 检查文件大小
ORIG_SIZE=$(stat -c%s "$INPUT" 2>/dev/null || stat -f%z "$INPUT" 2>/dev/null)
NEW_SIZE=$(stat -c%s "$OUTPUT" 2>/dev/null || stat -f%z "$OUTPUT" 2>/dev/null)
if [[ -n "$ORIG_SIZE" && -n "$NEW_SIZE" ]]; then
    if command -v numfmt &>/dev/null; then
        info "   大小: $(numfmt --to=iec $ORIG_SIZE) → $(numfmt --to=iec $NEW_SIZE)"
    fi
fi

ok "   输出: $OUTPUT"
