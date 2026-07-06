#!/bin/bash
# ============================================================
# push_cf_md.sh — 碳纤维 MD 批量提交脚本（可中断续传版）
#
# 改进点：
#   1. Phase 1 预扫描：检查 nohup.out 中的 "Finished running GPUMD."
#      标记，已完成的自动跳过，不再重复计算
#   2. 未完成的一律全新开始（删除 mdrun 内所有文件重建），
#      不依赖 restart.xyz 续算，避免状态不一致
#   3. 队列模式：只处理未完成的 dataset，可安全 kill 后重启
#
# 用法：
#   cd ~/carbon_fiber/dataset/build_xxx
#   nohup bash push_cf_md.sh > push_cf_md.log 2>&1 &
# ============================================================

export PATH=/home/rebreath/app/GPUMD-master/src:$PATH
set -euo pipefail

# 日志统一输出
exec > >(tee -a submit.log)
exec 2>&1
date

# GPUMD 完成标志
COMPLETION_MARKER="Finished running GPUMD."

# ============================================================
# 工具函数：等待空闲 GPU 并提交任务
# ============================================================
free_time_run() {
    while true; do
        for gpu_id in $(nvidia-smi --query-gpu=index --format=csv,noheader,nounits); do
            mem_used=$(nvidia-smi --id=$gpu_id --query-gpu=memory.used --format=csv,noheader,nounits)
            if [ "$mem_used" -lt 200 ]; then
                export CUDA_VISIBLE_DEVICES=$gpu_id
                echo "Running task on GPU $gpu_id"
                eval "$1"
                break 2
            fi
        done
        echo "No free GPU found, waiting..."
        sleep 60
    done
    date '+%Y-%m-%d %H:%M:%S' >> run_train-file.log
    echo -e "执行 $1 \n" >> run_train-file.log
}
export -f free_time_run

# ============================================================
# 常量
# ============================================================
nepfile="C_2024_NEP4.txt"
initdir=$PWD

# ============================================================
# Phase 1: 扫描所有 dataset，构建未完成队列
# ============================================================
echo "=============================================="
echo " Phase 1: Scanning datasets for completion"
echo "=============================================="

COMPLETED=()
TODO=()

for dir in dataset_*; do
    [[ -d $dir ]] || continue

    nohup_file="$dir/mdrun/nohup.out"
    if [ -f "$nohup_file" ] && grep -q "$COMPLETION_MARKER" "$nohup_file"; then
        COMPLETED+=("$dir")
        echo "  [SKIP] $dir — already completed"
    else
        TODO+=("$dir")
        echo "  [TODO] $dir"
    fi
done

echo ""
echo "  Completed: ${#COMPLETED[@]}"
echo "  Remaining: ${#TODO[@]}"
echo ""

if [ ${#TODO[@]} -eq 0 ]; then
    echo "All datasets completed. Nothing to do."
    date
    exit 0
fi

# ============================================================
# Phase 2: 逐项处理未完成队列
# ============================================================
echo "=============================================="
echo " Phase 2: Processing ${#TODO[@]} datasets"
echo "=============================================="

for dir in "${TODO[@]}"; do
    echo "==== Processing $dir ===="

    # 清理旧文件，全新开始
    mkdir -p "$dir/mdrun"
    rm -rf "$dir/mdrun/"*
    cp run.in "$nepfile" "$dir/mdrun/"
    cp "$dir/mixdefcetconfig.xyz" "$dir/mdrun/model.xyz"

    # 写入晶格常数到 model.xyz 第二行
    lattic_a=$(awk '{print $1}' "$dir/lattice_constants.txt")
    lattic_b=$(awk '{print $2}' "$dir/lattice_constants.txt")
    lattic_c=$(awk '{print $3}' "$dir/lattice_constants.txt")
    substring="Lattice=\"$lattic_a 0.0 0.0 0.0 $lattic_b 0.0 0.0 0.0 $lattic_c\" Properties=species:S:1:pos:R:3"
    sed -i "2s/.*/$substring/" "$dir/mdrun/model.xyz"

    cd "$dir/mdrun"
    echo "  当前处于 $PWD"
    free_time_run 'nohup gpumd > nohup.out 2>&1 &'
    sleep 5
    cd "$initdir"
    echo "==== Finished $dir ===="
done

date
echo "All datasets have been processed."
