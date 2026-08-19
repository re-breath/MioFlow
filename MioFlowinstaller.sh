#!/usr/bin/env bash
# ======================================================================
# File:         MioFlowinstaller.sh
# Project:      MioFlow (原 NebulaFlow)
# Description:  MioFlow一键安装脚本 / One-click installer for MioFlow.
#               将文件复制到 ~/.mio/ 并写入 ~/.bashrc。
# Author:       rebreath
# ======================================================================

set -e

# -------------------------------------------------------------------------
# Step 1: Create library directory and sync files
# Step 1: 创建库目录并同步文件
# -------------------------------------------------------------------------
mkdir -p $HOME/.mio
rsync -av --update . $HOME/.mio/

# -------------------------------------------------------------------------
# Step 2: Add to ~/.bashrc if not already present
# Step 2: 将环境变量写入 ~/.bashrc（首次安装时）
# -------------------------------------------------------------------------
if ! grep -q "WRITEMIOFLOW2ENV" "$HOME/.bashrc"; then
    echo '
# MioFlow function library by rebreath
# ----------------------------------------------------------------
WRITEMIOFLOW2ENV=1
export PATH=$PATH:$HOME/.mio
export BASH_ENV="$HOME/.mio/mio-env-function"
source $HOME/.mio/mio-env-function
# ----------------------------------------------------------------
' >> "$HOME/.bashrc"
fi

# -------------------------------------------------------------------------
# Step 3: Install/update the Python CLI and make launchers executable
# Step 3: 安装/更新 Python CLI，并设置启动脚本为可执行
# -------------------------------------------------------------------------
chmod +x $HOME/.mio/gpuq
chmod +x $HOME/.mio/sh_lib/run_cp2k_linux.sh 2>/dev/null || true

if command -v python3 >/dev/null 2>&1 && python3 -m pip --version >/dev/null 2>&1; then
    pip_install_args=(
        --user
        --no-deps
        --no-build-isolation
        --disable-pip-version-check
        --upgrade
    )
    if python3 -m pip install --help 2>/dev/null | grep -q -- '--break-system-packages'; then
        # Safe together with --user: permits installation into ~/.local only.
        pip_install_args+=(--break-system-packages)
    fi
    if ! python3 -m pip install "${pip_install_args[@]}" "$HOME/.mio"; then
        echo "Warning: failed to install the 'mio' CLI; Shell functions are still available." >&2
    fi
else
    echo "Warning: python3/pip not found; skipped installing the 'mio' CLI." >&2
fi

# -------------------------------------------------------------------------
# Step 4: Done — 提示用户加载环境
# Step 4: Remind user to source ~/.bashrc
# -------------------------------------------------------------------------
echo ""
echo "MioFlow library installed successfully!"
echo "Please run: source ~/.bashrc"
echo "If you see 'MioFlow library loaded O.<', the installation is complete."
echo ""
echo "MioFlow库已经安装成功，下面请使用 source $HOME/.bashrc 命令使环境变量生效。"
echo "看到 'MioFlow library loaded O.<' 代表安装成功。"
