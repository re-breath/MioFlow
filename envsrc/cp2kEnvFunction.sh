# ======================================================================
# File:         cp2kEnvFunction.sh
# Project:      MioFlow (原 NebulaFlow)
# Description:  CP2K计算相关函数库 — restart转换、能量提取、任务提交
#               CP2K restart file conversion, energy extraction, job submission.
# Author:       rebreath
# Dependencies: Multiwfn, cp2k
# ======================================================================


# ---------------------------------------------------------------------------
# Function: cp2krestart2cif / cp2krestart2xyz
# 功能: 使用Multiwfn将CP2K restart文件转换为cif或xyz格式
# 场景: CP2K几何优化完成后，restart文件包含最终结构，需要提取为
#       标准格式用于后续分析或VASP/GPUMD计算。
# Usage:
#   cp2krestart2cif [cif_filename]     # 默认输出opt.cif
#   cp2krestart2xyz [xyz_filename]     # 默认输出opt.xyz
# Example:
#   cp2krestart2cif result.cif
#   cp2krestart2xyz optimized.xyz
# Dependencies: Multiwfn
# ---------------------------------------------------------------------------
cp2krestart2cif() {
    local cifilename=${1:-"opt.cif"}
    Multiwfn *.restart << EOF > /dev/null
    100
    2
    33
    $cifilename
    0
    q
EOF
}

cp2krestart2xyz() {
    local xyzfilename=${1:-"opt.xyz"}
    Multiwfn *.restart << EOF  > /dev/null
    100
    2
    2
    $xyzfilename
    0
    q
EOF
}


# ---------------------------------------------------------------------------
# Function: cp2kstart
# 功能: 自动选择 Slurm 提交或本地 Linux 运行 CP2K
# Usage: cp2kstart [input.inp] [physical_cores]
# Example:
#   cp2kstart cp2k.inp 32
#   CP2K_RUN_MODE=local cp2kstart cp2k.inp 8
#   CP2K_RUN_MODE=slurm DRY_RUN=1 cp2kstart cp2k.inp 32
# ---------------------------------------------------------------------------
cp2kstart() {
    if (( $# > 2 )); then
        echo "用法: cp2kstart [input.inp] [physical_cores]" >&2
        return 2
    fi

    if [[ ${1:-} == "-h" || ${1:-} == "--help" ]]; then
        cat <<'EOF'
用法:
  cp2kstart [input.inp] [physical_cores]

自动模式:
  Slurm 控制器可用 -> 生成 temp.slurm 并提交
  其他 Linux      -> 调用 sh_lib/run_cp2k_linux.sh

环境变量:
  CP2K_RUN_MODE=auto|slurm|local       强制或自动选择运行方式
  CP2K_SLURM_PARTITION=xahcnormal      Slurm 分区
  CP2K_SLURM_MODULE=cp2k/...           Slurm CP2K module
  CP2K_SLURM_EXE=cp2k.popt             Slurm CP2K 程序
  MIOFLOW_CP2K_LOCAL_RUNNER=/path/...  本地运行脚本
  DRY_RUN=1                             只预览，不运行或提交
EOF
        return 0
    fi

    local inpfile=${1:-}
    local cpu_num=${2:-}
    local -a inp_candidates=()

    if [[ -z $inpfile ]]; then
        if [[ -f cp2k.inp ]]; then
            inpfile=cp2k.inp
        else
            local had_nullglob=0
            if shopt -q nullglob; then
                had_nullglob=1
            fi
            shopt -s nullglob
            inp_candidates=(./*.inp)
            if (( had_nullglob == 0 )); then
                shopt -u nullglob
            fi

            case ${#inp_candidates[@]} in
                0)
                    echo "错误: 当前目录没有 cp2k.inp 或其他 *.inp 文件。" >&2
                    return 1
                    ;;
                1)
                    inpfile=${inp_candidates[0]}
                    ;;
                *)
                    echo "错误: 当前目录有多个 *.inp 文件，请显式指定输入文件。" >&2
                    return 1
                    ;;
            esac
        fi
    fi

    if [[ ! -f $inpfile ]]; then
        echo "错误: CP2K 输入文件不存在: $inpfile" >&2
        return 1
    fi
    if [[ -n $cpu_num && ! $cpu_num =~ ^[1-9][0-9]*$ ]]; then
        echo "错误: 核数必须是正整数: $cpu_num" >&2
        return 1
    fi

    local input_abs input_dir input_name
    input_abs=$(realpath -e -- "$inpfile") || return 1
    input_dir=$(dirname -- "$input_abs")
    input_name=$(basename -- "$input_abs")

    local run_mode=${CP2K_RUN_MODE:-auto}
    case $run_mode in
        auto)
            if command -v sbatch >/dev/null 2>&1 \
                && command -v scontrol >/dev/null 2>&1 \
                && scontrol ping 2>/dev/null | grep -qE 'is UP|UP$'; then
                run_mode=slurm
            else
                run_mode=local
            fi
            ;;
        slurm|local) ;;
        *)
            echo "错误: CP2K_RUN_MODE 只能是 auto、slurm 或 local。" >&2
            return 1
            ;;
    esac

    if [[ $run_mode == local ]]; then
        if [[ $(uname -s 2>/dev/null) != Linux ]]; then
            echo "错误: 本地 CP2K 运行脚本目前只支持 Linux。" >&2
            return 1
        fi

        local function_file mioflow_root local_runner
        function_file=${BASH_SOURCE[0]}
        mioflow_root=$(cd -- "$(dirname -- "$function_file")/.." && pwd -P) || return 1
        local_runner=${MIOFLOW_CP2K_LOCAL_RUNNER:-$mioflow_root/sh_lib/run_cp2k_linux.sh}
        if [[ ! -f $local_runner ]]; then
            echo "错误: 找不到本地 CP2K 运行脚本: $local_runner" >&2
            return 1
        fi

        echo "运行模式: local Linux"
        echo "运行脚本: $local_runner"
        if [[ -n $cpu_num ]]; then
            bash "$local_runner" "$input_abs" "$cpu_num"
        else
            bash "$local_runner" "$input_abs"
        fi
        return $?
    fi

    local partition=${CP2K_SLURM_PARTITION:-xahcnormal}
    local cp2k_module=${CP2K_SLURM_MODULE:-cp2k/2023.1-intelmpi-2018}
    local slurm_cp2k_exe=${CP2K_SLURM_EXE:-cp2k.popt}
    local slurm_mpi=${CP2K_SLURM_MPI:-pmi2}
    local slurm_script=${CP2K_SLURM_SCRIPT:-temp.slurm}
    local job_name
    cpu_num=${cpu_num:-32}
    job_name=$(basename -- "$input_dir")
    job_name=${job_name//[^[:alnum:]_.-]/_}
    [[ -n $job_name ]] || job_name=cp2k

    if [[ ! $partition =~ ^[[:alnum:]_.-]+$ ]]; then
        echo "错误: Slurm 分区名包含不安全字符: $partition" >&2
        return 1
    fi
    if [[ ! $slurm_mpi =~ ^[[:alnum:]_.-]+$ ]]; then
        echo "错误: Slurm MPI 类型包含不安全字符: $slurm_mpi" >&2
        return 1
    fi
    if [[ ${DRY_RUN:-0} != 1 ]] && ! command -v sbatch >/dev/null 2>&1; then
        echo "错误: 找不到 sbatch；如需本地运行，请设置 CP2K_RUN_MODE=local。" >&2
        return 1
    fi

    local quoted_input quoted_dir quoted_exe quoted_module
    printf -v quoted_input '%q' "$input_name"
    printf -v quoted_dir '%q' "$input_dir"
    printf -v quoted_exe '%q' "$slurm_cp2k_exe"
    printf -v quoted_module '%q' "$cp2k_module"

    cat > "$slurm_script" <<EOF
#!/bin/bash
#SBATCH -J $job_name
#SBATCH -N 1
#SBATCH --ntasks-per-node=$cpu_num
#SBATCH --cpus-per-task=1
#SBATCH --hint=nomultithread
#SBATCH -p $partition

set -e

module purge
module load $quoted_module

export OMP_NUM_THREADS=1
export OMP_DYNAMIC=FALSE
export MKL_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1

cd -- $quoted_dir
srun --mpi=$slurm_mpi --cpu-bind=cores $quoted_exe -i $quoted_input -o cp2k.log
EOF

    echo "运行模式: Slurm"
    echo "输入文件: $input_abs"
    echo "任务名称: $job_name"
    echo "任务核数: $cpu_num"
    echo "分区:     $partition"
    echo "脚本:     $slurm_script"

    if [[ ${DRY_RUN:-0} == 1 ]]; then
        echo "----- Slurm script -----"
        cat "$slurm_script"
        return 0
    fi

    sbatch -- "$slurm_script"
}


# ---------------------------------------------------------------------------
# Function: get_cp2k_energy / update_cp2k_inp_cell_from_xyz
# 功能: 从CP2K log文件提取能量 / 从xyz更新CP2K输入文件的晶胞参数
# Usage:
#   get_cp2k_energy [cp2k.log]
#   update_cp2k_inp_cell_from_xyz model.xyz cp2k.inp
# ---------------------------------------------------------------------------
get_cp2k_energy() {
    local logfile=${1:-"cp2k.log"}
    grep "ENERGY|" $logfile |tail -n 5
}

update_cp2k_inp_cell_from_xyz() {
    local xyz_file="$1"; local cp2k_inp="$2"
    Lattice=$(get_Lattice $1 | grep -oP '(?<=Lattice=").*(?=")')
    cell_A=$(echo $Lattice | awk '{print $1,$2,$3}')
    cell_B=$(echo $Lattice | awk '{print $4,$5,$6}')
    cell_C=$(echo $Lattice | awk '{print $7,$8,$9}')
    sed -E "/^\s*A\s*[0-9]*\.[0-9]+ \s*[0-9]*\.[0-9]+ \s*[0-9]*\.[0-9]+/s/.*/      A   $cell_A/" $cp2k_inp |sed -E "/^\s*B\s*[0-9]*\.[0-9]+ \s*[0-9]*\.[0-9]+ \s*[0-9]*\.[0-9]+/s/.*/      B   $cell_B/" |sed -E "/^\s*C\s*[0-9]*\.[0-9]+ \s*[0-9]*\.[0-9]+ \s*[0-9]*\.[0-9]+/s/.*/      C   $cell_C/" > ${cp2k_inp%.*}_up.inp
    sed -i "/@SET XYZFILE/s/.*/@SET XYZFILE    $1/" ${cp2k_inp%.*}_up.inp
    sed -i "/@SET PROJECT_NAME/s/.*/@SET PROJECT_NAME    ${xyz_file%.*}/" ${cp2k_inp%.*}_up.inp
}
