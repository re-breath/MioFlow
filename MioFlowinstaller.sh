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
# Step 3: Make gpuq executable
# Step 3: 设置 gpuq 为可执行
# -------------------------------------------------------------------------
chmod +x $HOME/.mio/gpuq

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
