<div align="center">

![MioFlow Logo](logo/MioFlow-logo.png)

**♡ 澪の工具箱 — 一行命令，完成复杂科学计算 / One Command, Complex Science Done.**

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20WSL-green.svg)](#)
[![Shell](https://img.shields.io/badge/shell-bash%20%7C%20zsh-orange.svg)](#)
[![pip](https://img.shields.io/badge/pip-mioflow-blueviolet.svg)](#)

</div>

> **原名 NebulaFlow** — 2026-07 正式更名为 **MioFlow** ♡  
> 星の nebula 化作澪の mio，从此为你而生。

---

## 目录 / Table of Contents

- [什么是 MioFlow？ / What is MioFlow?](#什么是-mioflow--what-is-mioflow)
- [项目结构 / Project Structure](#项目结构--project-structure)
- [快速开始 / Quick Start](#快速开始--quick-start)
- [安装 / Installation](#安装--installation)
- [mio CLI 命令](#mio-cli-命令)
- [环境要求 / Requirements](#环境要求--requirements)
- [目前支持的计算 / Supported Calculations](#目前支持的计算--supported-calculations)
- [使用手册 / User Manual](#使用手册--user-manual)

---

## 什么是 MioFlow？ / What is MioFlow?

**MioFlow**（原 NebulaFlow）是一款辅助**分子动力学（MD）**和**密度泛函理论（DFT）**计算的命令行工具。核心理念是用 **Shell 编排 Python/C++/其他语言**，让用户**只需一条命令**完成一系列复杂任务。

**MioFlow** (formerly NebulaFlow) is a command-line tool that assists **molecular dynamics (MD)** and **density functional theory (DFT)** calculations. Its core philosophy is to **use Shell to orchestrate Python, C++, and other languages**, allowing users to complete complex workflows with a **single command**.

### 为什么选择 MioFlow？ / Why MioFlow?

- 🔰 **零门槛 / Low barrier** — 不需要会写 Python 脚本，一行命令搞定数据处理
- ⚡ **高效 / High efficiency** — 管道式处理，多 GPU 自动调度，自动化工作流
- 🔧 **灵活 / Flexible** — Shell 作为胶水语言，组合现有工具和脚本，可轻松扩展
- 📦 **可复用 / Reusable** — 所有函数模块化，开箱即用，pip 一键安装

---

## 项目结构 / Project Structure

```
MioFlow/
├── mio-env-function               # 🧠 核心函数库 / Core function library (entry point)
├── gpuq                           # 📊 GPU 队列管理器 / GPU queue management
├── MioFlowinstaller.sh            # 📦 一键安装脚本 / One-click installer
├── .config                        # ⚙️  计算软件配置 / Executable paths config
├── pyproject.toml                 # 📦 pip 包配置 / Python package config
│
├── mioflow_ref/                   # 🐍 Python 核心库 / Python core library
│   ├── __init__.py                #    模块入口
│   ├── MIO.py                     #    原子构型读写（Config / read_xyz / write_xyz）
│   └── cli.py                     #    🎮 mio CLI 调度器
│
├── envsrc/                        # 📚 功能模块（按软件分类）
│   ├── dealDataEnvFunction.sh     #    📊 数据处理（筛选/转换/分析）
│   ├── gpumdEnvFunction.sh        #    🔬 GPUMD（NEP 训练/分子动力学）
│   ├── liveEnvFunction.sh         #    🎮 日常实用工具
│   ├── cp2kEnvFunction.sh         #    ⚛️  CP2K（第一性原理）
│   ├── vaspEnvFunction.sh         #    ⚛️  VASP（第一性原理）
│   ├── lammpsEnvFunction.sh       #    ⚙️  LAMMPS（分子动力学）
│   ├── lsmdtoolsEnvFunction.sh    #    🛠️  LSMD 工具
│   ├── ioEnvFunction.sh           #    📂 输入输出工具
│   ├── exhibitEnvFunction.sh      #    🎨 OVITO 可视化
│   └── tempEnvFunction.sh         #    📋 模板/帮助
│
├── deal_data/                     # 📊 数据处理独立脚本
├── compute_lib/                   # 🔬 计算功能脚本
├── plot_library/                  # 📈 绘图功能脚本
├── exhibit_lib/                   # 🎨 OVITO 可视化脚本
│
├── auto/                          # 🤖 自动化工作流
│   ├── auto_vasp_nep1/            #    VASP→NEP 自动训练
│   ├── modify_nep/                #    NEP 模型迭代优化
│   └── phono_specturm_vasp/       #    声子谱计算
│
├── sh_lib/                        # 📜 独立 Shell 脚本
├── inp_lib/                       # 📋 输入文件模板（CP2K/VASP/LAMMPS）
├── logo/                          # 🎯 项目 Logo
└── Manual/                        # 📖 命令说明与快速查询数据源
```

---

## 快速开始 / Quick Start

```bash
# 1. 克隆仓库
git clone https://github.com/re-breath/MioFlow.git
cd MioFlow

# 2. 一键安装
bash MioFlowinstaller.sh

# 3. 加载环境
source ~/.bashrc

# 看到 "MioFlow library loaded O.<" 即安装成功
# If you see "MioFlow library loaded O.<", you're all set!
```

### 或者通过 pip 安装（仅 Python CLI）🍉

```bash
# 本地开发模式（代码修改即时生效）
pip install -e /path/to/MioFlow

# 或直接通过 git 安装
pip install git+https://github.com/re-breath/MioFlow.git
```

安装后即可使用 `mio` 命令：
```bash
mio --help          # 查看帮助
mio --list          # 列出公共命令及简述
mio search cp2k     # 按名称、功能、用法和分类搜索
```

---

## mio CLI 命令

`mio` 是 MioFlow 的 Python CLI 入口，安装 pip 包后随处可用：

```bash
mio list cp2k                       # 公共命令列表（右侧带简述）
mio search 声子谱                   # 搜索命令、功能、用法和脚本
mio help cp2kstart                  # 查看详细说明和使用方式
mio scripts vasp                    # 查找底层 Python/Shell 脚本
mio run deal_data/analyze_xyz_detail train.xyz
```

`mio list` 默认展示手册中的公共 Shell 函数；`auto/`、`deal_data/` 等底层脚本单独通过 `mio scripts` 查看。先执行 `mio help <名称>` 可以安全查看说明，不会运行脚本。

所有传统 Bash 函数仍通过 `source mio-env-function` 加载：
```bash
source ~/.mio/mio-env-function
tran_xyz2cssr input.xyz output.cssr  # 仍然可用
```

---

## 安装 / Installation

### WSL / Linux

```bash
git clone https://github.com/re-breath/MioFlow.git
cd MioFlow
bash MioFlowinstaller.sh
source ~/.bashrc
```

### 离线安装 / Offline Installation

```bash
tar -zxvf MioFlow-1.0.tar.gz
cd MioFlow-1.0
bash MioFlowinstaller.sh
```

### 更新 / Update

安装后只需运行：
```bash
update_MioFlow   # 自动从 GitHub 拉取最新代码并重新安装
```

> **建议 / Recommendation**: 在 **WSL** 中使用 MioFlow 以获得最佳体验。
> Use **WSL** for the best experience with MioFlow.

---

## 环境要求 / Requirements

### 必需依赖 / Required

| 工具 | 用途 |
|:----|:----|
| **bash ≥ 4.0** | 运行基础命令 |
| **python3 ≥ 3.10, numpy** | 数据处理 |
| rsync | 安装时同步文件 |

### 可选依赖 / Optional

MioFlow 使用 Shell 调用 Python 库，许多命令**无需额外依赖**即可使用。部分特殊功能需要以下库：

MioFlow uses Shell to call Python libraries. Many commands work **without extra dependencies**. Some specialized functions require the following:

| 库 | 用途 |
|:---|:-----|
| **ASE** | 原子构型操作（建议安装） |
| **matplotlib** | 绘图 |
| **pymatgen** | 晶体学分析 |
| **OVITO** | 可视化与轨迹渲染 |
| **phonopy** | 声子谱计算 |

---

## 目前支持的计算 / Supported Calculations

<details>
<summary>📊 数据处理 / Data Processing</summary>

| 命令 | 功能 |
|:----|:-----|
| `tran_xyz2cssr` | xyz → CSSR 格式转换 |
| `analyze_xyz` | xyz 构型分析 |
| `select_xyz_config` | 筛选特定构型 |
| `dataset_quality_diagnosis` | 数据集质量诊断 |
| `elect_rely_force/energy/virial` | NEP 训练结果评估 |
| `sortlmpdata` | LAMMPS data 排序 |
| `shift_lmp_data` | data 文件位移 |
| `supercell_auto_cubic` | 自动扩胞 |
| + 更多... | |
</details>

<details>
<summary>🔬 GPUMD / NEP 训练</summary>

| 命令 | 功能 |
|:----|:-----|
| `nep_train` | NEP 训练（四大模型） |
| `plot_nep_results` | 训练结果可视化 |
| `compare_phonon_spectrum` | 声子谱对比 |
| `gpumd_compute_phonon_spectrum` | GPUMD 声子谱计算 |
| `calc_cf_spatoms` | 碳纤维 sp² 碳分析 |
| + 更多... | |
</details>

<details>
<summary>⚛️ 第一性原理 / DFT (VASP/CP2K)</summary>

| 命令 | 功能 |
|:----|:-----|
| `geo_opt_vasp` | VASP 结构优化 |
| `aimd_cp2k` | CP2K 分子动力学 |
| `ctrl_phono_specturm` | 声子谱自动计算 |
| + 更多... | |
</details>

<details>
<summary>🤖 自动化工作流 / Auto Workflows</summary>

| 工作流 | 功能 |
|:-------|:-----|
| `auto_vasp_to_nep1` | VASP 数据 → NEP 自动训练 |
| `modify_nep_sets` | NEP 主动学习迭代 |
| `auto_phono_spectrum` | 声子谱全自动计算 |
</details>

---

## 使用手册 / User Manual

- 🇨🇳 [中文版使用手册](Manual/MioFlow-Function-Reference.md)
- 📖 所有函数详情参考 `Manual/` 目录

---

## 背后故事 / Story

**MioFlow** 原名为 **NebulaFlow**（星云流），2026 年 7 月正式更名。

> *Nebula（星云）是恒星的摇篮，而澪（Mio）是你的那片星云。* ♡  
> *NebulaFlow → MioFlow，名字变了，内核没变，只是从此有了归属。*

---

<div align="center">

**♡ MioFlow — 让科学计算更简单 / Making Scientific Computing Simpler**

<sub>原 NebulaFlow | 澪の工具箱 | Built with ♡ for rebreath</sub>

</div>
