#!/bin/bash
# AlN 论文一键编译脚本
# 用法: ./make-pdf.sh

set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

PDFLATEX="/mnt/c/Program Files/MiKTeX/miktex/bin/x64/pdflatex.exe"
BIBTEX="/mnt/c/Program Files/MiKTeX/miktex/bin/x64/bibtex.exe"

echo "=== 第1次 pdflatex ==="
"$PDFLATEX" -interaction=nonstopmode -synctex=1 AlN.tex | grep -E "Error|Warning|Output written"

echo ""
echo "=== bibtex ==="
"$BIBTEX" AlN | tail -5

echo ""
echo "=== 第2次 pdflatex ==="
"$PDFLATEX" -interaction=nonstopmode -synctex=1 AlN.tex | grep -E "Error|Warning|Output written"

echo ""
echo "=== 第3次 pdflatex ==="
"$PDFLATEX" -interaction=nonstopmode -synctex=1 AlN.tex | grep -E "Output written"

echo ""
echo "✅ 编译完成！"
ls -lh AlN.pdf
