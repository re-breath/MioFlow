# NebulaFlow 函数参考手册

> **版本**: 2026-06-28 | **作者**: rebreath | **总函数数**: ~270+
>
> 本手册按**科学计算任务领域**分类，方便快速查找。每个函数标注源文件和行号，可直接跳转查看源码。

---

## 目录

- [快速索引：按任务查找](#快速索引按任务查找)
- [1. VASP 第一性原理计算](#1-vasp-第一性原理计算)
- [2. GPUMD 分子动力学 & NEP 势函数](#2-gpumd-分子动力学--nep-势函数)
- [3. NEP 训练集构建与管理](#3-nep-训练集构建与管理)
- [4. HNEMD 热导率计算](#4-hnemd-热导率计算)
- [5. 声子谱 & 弹性模量](#5-声子谱--弹性模量)
- [6. 格式转换](#6-格式转换-xyzposcardatacifpdb)
- [7. LAMMPS 分子动力学](#7-lammps-分子动力学)
- [8. CP2K 计算](#8-cp2k-计算)
- [9. 多尺度MD软件开发 (LSMD)](#9-多尺度md-软件开发-lsmd)
- [10. 结晶度分析 (OVITO)](#10-结晶度分析-ovito)
- [11. 数据处理与分析](#11-数据处理与分析)
- [12. 可视化与绘图](#12-可视化与绘图)
- [13. GPU 任务调度 & 超算集群](#13-gpu-任务调度--超算集群)
- [14. 结构操作](#14-结构操作-扩胞缺陷吸附)
- [15. 碳纤维分析](#15-碳纤维分析)
- [16. 媒体处理 & 日常工具](#16-媒体处理--日常工具)
- [17. 核心工具函数](#17-核心工具函数)
- [附录A: 按源文件索引](#附录a-按源文件索引)
- [附录B: 按函数名 A-Z 索引](#附录b-按函数名-a-z-索引)

---

## 快速索引：按任务查找

| 我想做什么... | 去哪里找 |
|---|---|
| 提交 VASP 计算 | [§1](#1-vasp-第一性原理计算) `vasprun`, `vasprun_dcu` |
| 生成 POTCAR/KPOINTS | [§1](#1-vasp-第一性原理计算) `add_potcar`, `add_kpoints` |
| 运行 GPUMD 模拟 | [§2](#2-gpumd-分子动力学--nep-势函数) `start_gpumd` |
| 训练 NEP 势函数 | [§3](#3-nep-训练集构建与管理) 筛选 + 转换流程 |
| 计算热导率 (HNEMD) | [§4](#4-hnemd-热导率计算) `start_mul_hnemd` → `deal_hnemd_data` |
| 计算声子谱 | [§5](#5-声子谱--弹性模量) `compute_phonon_spectrum` |
| 计算弹性模量 | [§5](#5-声子谱--弹性模量) `compute_elastic_moduli` |
| XYZ ↔ POSCAR 转换 | [§6](#6-格式转换-xyzposcardatacifpdb) `tran_xyz2pos`, `tran_pos2xyz` |
| LAMMPS data 处理 | [§7](#7-lammps-分子动力学) `merge_lmp`, `tran_data2xyz` |
| 运行 CP2K | [§8](#8-cp2k-计算) `cp2kstart` |
| 分析结晶度 | [§10](#10-结晶度分析-ovito) `analyze_crystallinity_fraction` |
| 扩胞/建超胞 | [§14](#14-结构操作-扩胞缺陷吸附) `expand_cell`, `supercell_auto_cubic` |
| 构建吸附模型 | [§14](#14-结构操作-扩胞缺陷吸附) `build_adsorption_model` |
| 分析碳纤维 | [§15](#15-碳纤维分析) `analyze_cf` |
| 找空闲GPU跑任务 | [§13](#13-gpu-任务调度--超算集群) `free_gpu_run`, `free_time_run` |
| 批量文件处理 | [§17](#17-核心工具函数) `recc`→`revv`, `pfrun` |
| 音频/视频/PDF处理 | [§16](#16-媒体处理--日常工具) 各种 convert/compress 函数 |

---

# 1. VASP 第一性原理计算

**源文件**: [envsrc/vaspEnvFunction.sh](../envsrc/vaspEnvFunction.sh) (347行) + [envsrc/tempEnvFunction.sh](../envsrc/tempEnvFunction.sh) (部分)

## 1.1 任务提交

### vasprun()
- **文件**: `envsrc/vaspEnvFunction.sh:27`
- **功能**: 生成 SLURM 脚本并提交 VASP CPU 计算（xahcnormal 分区）
- **用法**: `vasprun [core_num]`
- **说明**: 默认 64 核；自动检测 INCAR/POSCAR/POTCAR；加载 Intel MPI + MKL/AVX2 优化

### vasprun_dcu()
- **文件**: `envsrc/vaspEnvFunction.sh:77`
- **功能**: 生成 SLURM 脚本并提交 VASP DCU 加速计算（xahdnormal 分区）
- **用法**: `vasprun_dcu [dcu_num]`
- **说明**: 每个 DCU 配 8 CPU 核；设置 HIP_VISIBLE_DEVICES + numactl 绑定

### check_vasp_complete()
- **文件**: `envsrc/gpumdEnvFunction.sh:890`
- **功能**: 检查 VASP 计算是否完成，未完成则自动提交
- **用法**: `check_vasp_complete [vasp_exe] [core_num]`
- **说明**: 通过 OUTCAR 完成标志检测；默认 1 核

### run_all_vasp_job()
- **文件**: `envsrc/gpumdEnvFunction.sh:915`
- **功能**: 遍历所有 `train-*` 目录并确保每个 VASP 任务完成
- **用法**: `run_all_vasp_job`
- **说明**: 自动添加 KSPACING、完整性检查、计时统计

### wait_complete_vasp_run()
- **文件**: `envsrc/tempEnvFunction.sh:403`
- **功能**: 等待 VASP 任务完成后执行指定命令
- **用法**: `wait_complete_vasp_run "后续命令"`
- **说明**: 最多重试 1000 次（间隔 100s）；超时报错

## 1.2 输入文件准备

### add_potcar()
- **文件**: `envsrc/vaspEnvFunction.sh:140`
- **功能**: 使用 vaspkit 自动生成 POTCAR（根据 POSCAR 元素）
- **用法**: `add_potcar`
- **说明**: 依赖 vaspkit（功能 103）；自动匹配推荐赝势

### add_kpoints()
- **文件**: `envsrc/vaspEnvFunction.sh:158`
- **功能**: 使用 vaspkit 生成 Gamma-centered MP 网格 KPOINTS
- **用法**: `add_kpoints [kpoint_spacing]`
- **说明**: 默认 0.03（2π/Å）；依赖 vaspkit（功能 102）

### add_kspacing_to_incar()
- **文件**: `envsrc/vaspEnvFunction.sh:175` / `envsrc/gpumdEnvFunction.sh:866`
- **功能**: 为 INCAR 添加 KSPACING 参数（替代 KPOINTS 文件）
- **用法**: `add_kspacing_to_incar <kspacing>`
- **说明**: 默认 0.2；适合大体系（>几百原子）；自动备份原 KPOINTS

### clean_vasp_out()
- **文件**: `envsrc/vaspEnvFunction.sh:197`
- **功能**: 删除所有 VASP 输出文件（WAVECAR/CHGCAR/OUTCAR等），仅保留输入
- **用法**: `clean_vasp_out`
- **说明**: 释放磁盘空间；不可逆操作

### load_single_point_energy_dir()
- **文件**: `envsrc/gpumdEnvFunction.sh:960`
- **功能**: 查找所有 POSCAR 并创建单点能计算目录结构
- **用法**: `load_single_point_energy_dir`
- **说明**: 构建 `single_energy/train-XXX` 目录；自动复制 INCAR/POTCAR/KPOINTS

## 1.3 结构优化流程

### vaspstart_geo_optstage1()
- **文件**: `envsrc/tempEnvFunction.sh:218`
- **功能**: VASP 结构优化第一阶段（低精度粗优化）
- **用法**: `vaspstart_geo_optstage1`
- **说明**: ENCUT=300, NSW=30, EDIFF=1E-2, IVDW=11；使用 4 DCU

### vaspstart_geo_optstage2()
- **文件**: `envsrc/tempEnvFunction.sh:252`
- **功能**: VASP 结构优化第二阶段（中精度）
- **用法**: `vaspstart_geo_optstage2`
- **说明**: ENCUT=400, NSW=100, EDIFF=1E-4

### vaspstart_geo_optstage3()
- **文件**: `envsrc/tempEnvFunction.sh:285`
- **功能**: VASP 结构优化第三阶段（高精度+力收敛）
- **用法**: `vaspstart_geo_optstage3`
- **说明**: ENCUT=500, EDIFFG=-0.02, KSPACING=0.2

### vaspstart_single_energy()
- **文件**: `envsrc/tempEnvFunction.sh:356`
- **功能**: 在当前目录构建 VASP 单点能计算
- **用法**: `vaspstart_single_energy`
- **说明**: IBRION=0, EDIFF=1E-5, NELM=120

### vaspstart_single_energy_after_relaxation()
- **文件**: `envsrc/tempEnvFunction.sh:320`
- **功能**: 驰豫完成后创建 calc_SE 目录提交单点能
- **用法**: `vaspstart_single_energy_after_relaxation`
- **说明**: 复制 CONTCAR→POSCAR，静态计算

### wait_geo_run_SE()
- **文件**: `envsrc/tempEnvFunction.sh:388`
- **功能**: 等待结构优化完成后自动提交单点能
- **用法**: `wait_geo_run_SE`
- **说明**: 每 100s 检测 OUTCAR 完成标志

## 1.4 后处理

### outcar_get_virial()
- **文件**: `envsrc/vaspEnvFunction.sh:289`
- **功能**: 从 OUTCAR 提取应力/位力 9 分量
- **用法**: `outcar_get_virial [outcar_file]`
- **说明**: grep "FORCE on cell =-STRESS" 提取 Total 行；用于构建 NEP 位力标签

### fix_poscar_zFrc()
- **文件**: `envsrc/vaspEnvFunction.sh:218`
- **功能**: 按分数坐标固定 POSCAR 中 z 轴底部原子
- **用法**: `fix_poscar_zFrc [posfile] [frac]`
- **说明**: 默认固定底部 70%（frac=0.7）；依赖 ase+vaspkit(402)；输出 POSCAR_FIX.vasp

### fix_poscar_zCar()
- **文件**: `envsrc/vaspEnvFunction.sh:257`
- **功能**: 按绝对坐标固定 POSCAR 中 z 范围原子
- **用法**: `fix_poscar_zCar [posfile] [z_max] [z_min]`
- **说明**: 默认 z_max=18, z_min=0；依赖 vaspkit(402)

### deal_outcar_to_train()
- **文件**: `envsrc/gpumdEnvFunction.sh:990`
- **功能**: 将所有 OUTCAR 转换为 NEP 训练集 train.xyz
- **用法**: `deal_outcar_to_train [target_dir]`
- **说明**: 提取晶格/能量/位力/受力；遍历所有 OUTCAR

### generate_band_plot()
- **文件**: `envsrc/vaspEnvFunction.sh:306`
- **功能**: 从 band.yaml 绘制声子色散图
- **用法**: `generate_band_plot <band.yaml>`
- **说明**: 依赖 pyyaml/numpy/matplotlib；输出 phonon_band_structure.png

---

# 2. GPUMD 分子动力学 & NEP 势函数

**源文件**: [envsrc/gpumdEnvFunction.sh](../envsrc/gpumdEnvFunction.sh) (1159行)

## 2.1 任务启动

### start_gpumd()
- **文件**: `envsrc/gpumdEnvFunction.sh:483`
- **功能**: 根据 `.config` 自动选择 GPUMD 启动方式（GPU/DCU）
- **用法**: `start_gpumd [dcu_num]`
- **说明**: 配置中 `gpumd_exe` 决定模式；兼容普通 GPU 和 DCU 加速器

### verify_gpumd_result()
- **文件**: `envsrc/gpumdEnvFunction.sh:458`
- **功能**: 创建 `verify_` 目录重新验算当前 GPUMD 算例
- **用法**: `verify_gpumd_result [nepfile]`
- **说明**: 自动检测 `nep*.txt`；复制输入文件到验证目录

### repeat_buildgpumd()
- **文件**: `envsrc/tempEnvFunction.sh:467`
- **功能**: 创建 n 个 GPUMD 运行副本目录
- **用法**: `repeat_buildgpumd n`
- **说明**: 生成 run1~runN，每个含 model.xyz + nep.txt + run.in

### repeat_rungpumd()
- **文件**: `envsrc/tempEnvFunction.sh:477`
- **功能**: 并行启动 n 个 GPUMD 运行
- **用法**: `repeat_rungpumd n`
- **说明**: 使用 free_time_run 间隔 5s 依次启动

## 2.2 超算集群启动器

### gpumdstart_rebreath()
- **文件**: `envsrc/gpumdEnvFunction.sh:1109`
- **功能**: 曙光超算 rebreath 分区 SLURM 提交
- **用法**: `gpumdstart_rebreath [-n dcu_num]`
- **说明**: 分区 xahdnormal；240h 时限

### gpumdstart_zwj()
- **文件**: `envsrc/gpumdEnvFunction.sh:1135`
- **功能**: 曙光超算 zwj 分区 SLURM 提交
- **用法**: `gpumdstart_zwj [-n dcu_num]`
- **说明**: 分区 wzhdtest；GPUMD 3.9.5 + DTK 24.04

### gpumdstart_dcu()
- **文件**: `envsrc/tempEnvFunction.sh:114`
- **功能**: 通用曙光超算 GPUMD DCU 任务提交
- **用法**: `gpumdstart_dcu [-n dcu_num]`
- **说明**: 1 DCU + 1 CPU 默认；任务名取当前目录名

### submit_gpumd()
- **文件**: `envsrc/tempEnvFunction.sh:803`
- **功能**: 提交 GPUMD Slurm 任务（1 GPU + 4 CPU）
- **用法**: `submit_gpumd [run.in]`
- **说明**: 默认输入 run.in；非 run.in 时创建软链接

## 2.3 应力-应变分析

### plot_stress_strain_curve()
- **文件**: `envsrc/gpumdEnvFunction.sh:1074`
- **功能**: 自动检测变形轴并绘制应力-应变曲线
- **用法**: `plot_stress_strain_curve`
- **说明**: 委托 stress_strain_curve.sh；识别 deform_{xyz}+ 目录

### plot_mul_stress_strain_curve()
- **文件**: `envsrc/gpumdEnvFunction.sh:1088`
- **功能**: 多方向应力-应变曲线对比
- **用法**: `plot_mul_stress_strain_curve`
- **说明**: 需 deform_x/ deform_y/ deform_z/ 目录

---

# 3. NEP 训练集构建与管理

**源文件**: `envsrc/gpumdEnvFunction.sh` (筛选) + `envsrc/dealDataEnvFunction.sh` (文件操作)

## 3.1 训练集质量筛选

### screening_reasonable_forces()
- **文件**: `envsrc/gpumdEnvFunction.sh:27`
- **功能**: 筛选受力在 [min, max] 范围内的构型
- **用法**: `screening_reasonable_forces <xyzfile> <min> <max>`
- **说明**: 委托 elect_rely_force.py；剔除 DFT 受力异常构型

### screening_reasonable_energy()
- **文件**: `envsrc/gpumdEnvFunction.sh:44`
- **功能**: 筛选总能量在合理范围的构型
- **用法**: `screening_reasonable_energy <xyzfile> <min> <max>`
- **说明**: 委托 elect_rely_energy.py；剔除 DFT 未收敛构型

### screening_reasonable_virial()
- **文件**: `envsrc/gpumdEnvFunction.sh:61`
- **功能**: 筛选位力在合理范围的构型
- **用法**: `screening_reasonable_virial <xyzfile> <min> <max>`
- **说明**: 委托 elect_rely_virial.py；剔除非物理应力构型

## 3.2 训练集诊断

### check_dataset_quality()
- **文件**: `envsrc/gpumdEnvFunction.sh:511`
- **功能**: NEP 训练集多维度质量诊断（PCA/离群检测/描述符分析）
- **用法**: `check_dataset_quality [--descriptor descriptor.out] [--outdir report_dir]`
- **说明**: 委托 dataset_quality_diagnosis.py；依赖 sklearn/numpy/ase

### compare_nepdata()
- **文件**: `envsrc/gpumdEnvFunction.sh:526`
- **功能**: 比较 train.xyz 和 test.xyz 基本信息
- **用法**: `compare_nepdata [train.xyz] [test.xyz]`
- **说明**: 输出构型数量对比

## 3.3 VASP→NEP 桥接

### deal_outcar_to_train()
- **文件**: `envsrc/gpumdEnvFunction.sh:990`
- **功能**: 批量 OUTCAR → train.xyz
- **用法**: `deal_outcar_to_train [target_dir]`
- **说明**: 参见 §1.4

### load_single_point_energy_dir()
- **文件**: `envsrc/gpumdEnvFunction.sh:960`
- **功能**: 批量创建单点能计算目录
- **用法**: `load_single_point_energy_dir`
- **说明**: 参见 §1.2

### run_all_vasp_job()
- **文件**: `envsrc/gpumdEnvFunction.sh:915`
- **功能**: 批量运行所有 VASP 单点能
- **用法**: `run_all_vasp_job`
- **说明**: 参见 §1.1

---

# 4. HNEMD 热导率计算

**源文件**: [envsrc/gpumdEnvFunction.sh](../envsrc/gpumdEnvFunction.sh)

## 4.1 批量运行

### start_mul_hnemd()
- **文件**: `envsrc/gpumdEnvFunction.sh:173`
- **功能**: 批量创建多次 HNEMD 计算目录并排队执行
- **用法**: `start_mul_hnemd <nepfile> <times> <core_num>`
- **说明**: 创建 hnemd_0~hnemd_N；使用 free_time_run 在空闲 GPU 排队；默认 6 次

### start_mul_hnemd_shuguang()
- **文件**: `envsrc/gpumdEnvFunction.sh:199`
- **功能**: 曙光超算版批量 HNEMD（质数种子防冲突）
- **用法**: `start_mul_hnemd_shuguang <nepfile> <times> <core_num>`
- **说明**: 调用 generate_large_primes 生成独立种子；使用 gpumd_dcu_394 提交

## 4.2 数据后处理

### deal_hnemd_data()
- **文件**: `envsrc/gpumdEnvFunction.sh:344`
- **功能**: 一键处理：整理数据 → 平均 kappa → 绘制热导率
- **用法**: `deal_hnemd_data`
- **说明**: 委托 deal_hnemd_data.sh 后调用 plot_mul_hnemd

### plot_hnemd()
- **文件**: `envsrc/gpumdEnvFunction.sh:227`
- **功能**: 自动识别热导方向（_x/_y/_z）并绘图
- **用法**: `plot_hnemd`
- **说明**: 递归查找 kappa.out；正则提取方向后缀

### plot_hnemd_para()
- **文件**: `envsrc/gpumdEnvFunction.sh:257`
- **功能**: 并行绘制所有 HNEMD 热导率图（动态检测 CPU 空闲核数）
- **用法**: `plot_hnemd_para [root_dir]`
- **说明**: 通过 /proc/loadavg 估算空闲核；xargs -P 并行

### plot_mul_hnemd()
- **文件**: `envsrc/gpumdEnvFunction.sh:311`
- **功能**: 绘制多次 HNEMD 平均热导率图
- **用法**: `plot_mul_hnemd`
- **说明**: 查找 average_hnemd/kappa 目录；自动统计 kappa_N.out 数量

### get_hnemd_data()
- **文件**: `envsrc/gpumdEnvFunction.sh:375`
- **功能**: 依次进入 x/y/z 三个方向 HNEMD 目录绘图
- **用法**: `get_hnemd_data`
- **说明**: 需 hnemd_x/, hnemd_y/, hnemd_z/ 子目录

### check_hnemd_thermo()
- **文件**: `envsrc/gpumdEnvFunction.sh:359`
- **功能**: 检查 HNEMD thermo.out 输出，计算平均值和最终晶格参数
- **用法**: `check_hnemd_thermo`
- **说明**: 调用 average_file_s 处理 thermo_*；tail -n 1 输出晶格

### deal_strain_fluctuation_to_elastic()
- **文件**: `envsrc/gpumdEnvFunction.sh:400`
- **功能**: 从应变波动法 thermo.out 提取弹性模量
- **用法**: `deal_strain_fluctuation_to_elastic <T_K>`
- **说明**: 委托 deal_strain_fluctuation.sh；输出 elastics.txt

---

# 5. 声子谱 & 弹性模量

**源文件**: `envsrc/gpumdEnvFunction.sh` + `compute_lib/` + `envsrc/dealDataEnvFunction.sh`

### compute_phonon_spectrum()
- **文件**: `envsrc/gpumdEnvFunction.sh:845`
- **功能**: 使用 GPUMD + phonopy 计算声子谱
- **用法**: `compute_phonon_spectrum`
- **说明**: 需 model.xyz + nep.txt；委托 gpumd_compute_phonon_spectrum.py；依赖 phonopy

### compute_elastic_moduli()
- **文件**: `envsrc/gpumdEnvFunction.sh:824`
- **功能**: 使用 calorine 库计算弹性模量 Cij 张量
- **用法**: `compute_elastic_moduli [nepfile]`
- **说明**: 默认 nep.txt；通过 sed 注入参数到 Python 模板；输出 elastic_calorine.txt

### get_phonon_spectrum_mpdata()
- **文件**: `envsrc/dealDataEnvFunction.sh:1492`
- **功能**: 从 Materials Project API 获取声子谱数据并绘图
- **用法**: `get_phonon_spectrum_mpdata <mpid> [method]`
- **说明**: 如 mp-2741；method 默认 dfpt；分两步：提取+绘图

### generate_band_plot()
- **文件**: `envsrc/vaspEnvFunction.sh:306`
- **功能**: 从 phonopy band.yaml 绘制声子色散
- **用法**: `generate_band_plot <band.yaml>`
- **说明**: 参见 §1.4

---

# 6. 格式转换 (XYZ/POSCAR/Data/CIF/PDB)

**源文件**: [envsrc/ioEnvFunction.sh](../envsrc/ioEnvFunction.sh) (159行) + `envsrc/dealDataEnvFunction.sh` (部分)

> 所有转换函数依赖 `python3` + `ase`

## 6.1 XYZ ↔ POSCAR

### tran_xyz2pos()
- **文件**: `envsrc/ioEnvFunction.sh:20`
- **功能**: XYZ → VASP POSCAR
- **用法**: `tran_xyz2pos <file.xyz>`
- **说明**: 输出 POSCAR_convered

### tran_pos2xyz()
- **文件**: `envsrc/ioEnvFunction.sh:38`
- **功能**: POSCAR → 扩展 XYZ（保留晶格）
- **用法**: `tran_pos2xyz <POSCAR> [output.xyz]`
- **说明**: 默认输出 model_conversed.xyz

## 6.2 XYZ ↔ LAMMPS Data

### tran_xyz2data()
- **文件**: `envsrc/ioEnvFunction.sh:77`
- **功能**: XYZ → LAMMPS data
- **用法**: `tran_xyz2data <model.xyz> <output.data> <elem1> [elem2 ...]`
- **说明**: 必须提供元素列表以分配原子类型；自动规范化第二行关键字

### tran_data2xyz()
- **文件**: `envsrc/ioEnvFunction.sh:56`
- **功能**: LAMMPS data → 扩展 XYZ
- **用法**: `tran_data2xyz <file.data> [output.xyz] [atom_style]`
- **说明**: atom_style 默认 atomic

## 6.3 其他格式

### tran_xyz2pdb()
- **文件**: `envsrc/ioEnvFunction.sh:106`
- **功能**: XYZ → PDB 格式
- **用法**: `tran_xyz2pdb <file.xyz>`
- **说明**: 输出 convered.pdb

### tran_cif2xyz()
- **文件**: `envsrc/ioEnvFunction.sh:124`
- **功能**: CIF → 扩展 XYZ（保留晶格）
- **用法**: `tran_cif2xyz <file.cif>`
- **说明**: 自动命名（.cif→.xyz）

### tran_xyz2cif() / tran_pos2cif()
- **文件**: `envsrc/ioEnvFunction.sh:149`
- **功能**: XYZ/POSCAR → CIF 格式
- **用法**: `tran_xyz2cif <input> [output.cif]`
- **说明**: 默认输出 file.cif；ASE 通用读写

### clean_poscar()
- **文件**: `envsrc/tempEnvFunction.sh:440`
- **功能**: 清理 POSCAR 重复元素格式（ASE 生成后用）
- **用法**: `clean_poscar [POSCAR]`
- **说明**: POSCAR→xyz→POSCAR 往返转换；合并重复元素条目

### tran_xyz2cssr()
- **文件**: `envsrc/dealDataEnvFunction.sh:1426`
- **功能**: XYZ → CSSR 格式（晶体学可视化）
- **用法**: `tran_xyz2cssr <input.xyz> <output.cssr>`

---

# 7. LAMMPS 分子动力学

**源文件**: [envsrc/lammpsEnvFunction.sh](../envsrc/lammpsEnvFunction.sh) (104行)

### merge_lmp()
- **文件**: `envsrc/lammpsEnvFunction.sh:21`
- **功能**: 合并 LAMMPS data + settings 为完整 data 文件
- **用法**: `merge_lmp <datafile> <settings>`
- **说明**: 为 LigParGen 设计；OPLS 力场参数；输出 mergedata.lmp + merge.log

### lammpsrun()
- **文件**: `envsrc/lammpsEnvFunction.sh:74`
- **功能**: 曙光超算提交 LAMMPS CPU 任务
- **用法**: `lammpsrun <ncore> <in_file>`
- **说明**: xahcnormal 分区；单节点

### submit_lmp_matpl()
- **文件**: `envsrc/tempEnvFunction.sh:756`
- **功能**: 提交 LAMMPS Slurm 任务（matpl 环境）
- **用法**: `submit_lmp_matpl [lmp.in] [corenum]`
- **说明**: 默认 4 核；加载 python/ase-lammps-kokkos-nep
- **别名**: `runlmp`

### shift_lmp_data()
- **文件**: `envsrc/lammpsEnvFunction.sh:51`
- **功能**: 使用 OVITO 平移 LAMMPS data 原子并包裹回盒子
- **用法**: `shift_lmp_data <in.data> <out.data> [dx] [dy] [dz]`
- **说明**: 默认平移 10Å；修复 PBC 切割分子

### sortlmpdata()
- **文件**: `envsrc/lammpsEnvFunction.sh:100`
- **功能**: 对 LAMMPS data 原子 ID 重新排序
- **用法**: `sortlmpdata <input.data>`
- **说明**: 输出 `<basename>_sort.data`

---

# 8. CP2K 计算

**源文件**: [envsrc/cp2kEnvFunction.sh](../envsrc/cp2kEnvFunction.sh) (99行) + `envsrc/tempEnvFunction.sh` (部分)

### cp2kstart()
- **文件**: `envsrc/cp2kEnvFunction.sh:58` / `envsrc/tempEnvFunction.sh:159`
- **功能**: 曙光超算提交 CP2K 任务
- **用法**: `cp2kstart [cp2k.inp] [cpu_num]`
- **说明**: 默认 32 核；加载 cp2k/2023.1-intelmpi-2018；srun --mpi=pmi2

### cp2krestart2cif()
- **文件**: `envsrc/cp2kEnvFunction.sh:24`
- **功能**: CP2K restart → CIF 格式
- **用法**: `cp2krestart2cif [cif_filename]`
- **说明**: 依赖 Multiwfn；默认输出 opt.cif

### cp2krestart2xyz()
- **文件**: `envsrc/cp2kEnvFunction.sh:36`
- **功能**: CP2K restart → XYZ 格式
- **用法**: `cp2krestart2xyz [xyz_filename]`
- **说明**: 依赖 Multiwfn；默认输出 opt.xyz

### get_cp2k_energy()
- **文件**: `envsrc/cp2kEnvFunction.sh:85`
- **功能**: 从 CP2K 日志提取总能量
- **用法**: `get_cp2k_energy [cp2k.log]`
- **说明**: grep "ENERGY|" 输出最后 5 行

### update_cp2k_inp_cell_from_xyz()
- **文件**: `envsrc/cp2kEnvFunction.sh:90` / `envsrc/dealDataEnvFunction.sh:1441` / `envsrc/tempEnvFunction.sh:142`
- **功能**: 用 xyz 晶格更新 CP2K 输入的 CELL 部分
- **用法**: `update_cp2k_inp_cell_from_xyz <model.xyz> <cp2k.inp>`
- **说明**: sed 替换 A/B/C 向量；输出 `*_up.inp`；同时更新 @SET XYZFILE

### build_stages()
- **文件**: `envsrc/tempEnvFunction.sh:189`
- **功能**: 构建多 stage CP2K 计算文件夹
- **用法**: `build_stages`
- **说明**: 创建 stage1~4 目录；自动更新晶胞并提交

### check_stage_energy()
- **文件**: `envsrc/tempEnvFunction.sh:204`
- **功能**: 检查各 stage 的 CP2K 计算能量
- **用法**: `check_stage_energy`
- **说明**: 对 stage1~4 分别查找 ENERGY| 行

### use_pbc_run()
- **文件**: `envsrc/tempEnvFunction.sh:446`
- **功能**: 将非周期性改为 PBC 后提交 CP2K
- **用法**: `use_pbc_run`
- **说明**: 创建 use_pbc 目录；PERIODIC NONE→XYZ

### use_sccs_run()
- **文件**: `envsrc/tempEnvFunction.sh:456`
- **功能**: 添加 SCCS 隐式溶剂模型后提交 CP2K
- **用法**: `use_sccs_run`
- **说明**: 介电常数 78.36（水）；创建 use_sccs 目录

---

# 9. 多尺度MD软件开发 (LSMD)

**源文件**: [envsrc/lsmdtoolsEnvFunction.sh](../envsrc/lsmdtoolsEnvFunction.sh) (114行)

> 用于自研 LSMD 软件与 LAMMPS 的力场分量对比验证

### testlsmdmod()
- **文件**: `envsrc/lsmdtoolsEnvFunction.sh:61`
- **功能**: 使用 LSMD 逐分量测试力场（全部/键/角/二面角/配对）
- **用法**: `testlsmdmod <model.data>`
- **说明**: 生成 md.inp 运行 5 次；输出 virialbond/angle/dihedral/pair.txt + 轨迹

### testlmpmod()
- **文件**: `envsrc/lsmdtoolsEnvFunction.sh:23`
- **功能**: 在 lmptest 目录中用 LAMMPS 验证力场模型
- **用法**: `testlmpmod <model.data>`
- **说明**: 激活 deepmd conda 环境；4 MPI 进程；模板 testall.inp

### testlmpdir()
- **文件**: `envsrc/lsmdtoolsEnvFunction.sh:37`
- **功能**: 在当前目录用 LAMMPS 验证力场（可设温度）
- **用法**: `testlmpdir <model.data> [T_K]`
- **说明**: 默认 300K；单进程运行

### testlsmdmod() — 辅助
- **文件**: `envsrc/lsmdtoolsEnvFunction.sh:49` (注释中 testlsmdir)
- **说明**: 当前目录版 LSMD 验证

### clearcompare()
- **文件**: `envsrc/lsmdtoolsEnvFunction.sh:95`
- **功能**: 清理 LAMMPS/LSMD 对比测试目录
- **用法**: `clearcompare`

### cdcomparedir()
- **文件**: `envsrc/lsmdtoolsEnvFunction.sh:96`
- **功能**: 切换到对比测试根目录
- **用法**: `cdcomparedir`

### metal2real()
- **文件**: `envsrc/lsmdtoolsEnvFunction.sh:107`
- **功能**: LAMMPS metal 单位 → real 单位转换
- **用法**: `metal2real <val1> [val2 ...]`
- **说明**: 转换因子 23.060547830619 eV→kcal/mol

---

# 10. 结晶度分析 (OVITO)

**源文件**: [envsrc/dealDataEnvFunction.sh](../envsrc/dealDataEnvFunction.sh) (§7)

> 所有结晶度分析函数依赖 `ovito` + `numpy` + `matplotlib`

### analyze_crystallinity_fraction()
- **文件**: `envsrc/dealDataEnvFunction.sh:925`
- **功能**: 计算特定晶型原子比例随帧数变化（PTM）
- **用法**: `analyze_crystallinity_fraction <crystal_type> <xyz_file> [rmsd_cutoff]`
- **说明**: RMSD 截断默认 0.1；输出 `<晶型>_atom_fraction.png` + .txt

### analyze_mulcrystallinity_fraction()
- **文件**: `envsrc/dealDataEnvFunction.sh:1000`
- **功能**: 同时分析多种晶型比例演化
- **用法**: `analyze_mulcrystallinity_fraction <xyz_file> <type1> <type2> ... [rmsd_cutoff]`
- **说明**: 如 FCC+HCP+BCC；最后一个数字参数作 RMSD 截断

### analyze_allcrystallinity_fraction()
- **文件**: `envsrc/dealDataEnvFunction.sh:1138`
- **功能**: 一次性分析所有 PTM 支持的晶型比例
- **用法**: `analyze_allcrystallinity_fraction <xyz_file> [rmsd_cutoff]`
- **说明**: 自动过滤始终为 0 的晶型；输出 active_structures_summary.txt

### analyze_crystallinity_frame_counts()
- **文件**: `envsrc/dealDataEnvFunction.sh:1078`
- **功能**: 分析单帧所有晶型原子计数
- **用法**: `analyze_crystallinity_frame_counts <xyz_file> [frame|last] [rmsd_cutoff]`
- **说明**: 默认最后一帧；输出 9 种 PTM 晶型计数和比例

### get_grain_count()
- **文件**: `envsrc/dealDataEnvFunction.sh:877`
- **功能**: PTM + 晶粒分割分析晶粒数量演化
- **用法**: `get_grain_count <crystal_type> <xyz_file> [min_grain_size]`
- **说明**: 默认最小晶粒 100 原子；输出 grain_count_*.png + crystal_atoms_*.png

### analysis_grains_size()
- **文件**: `envsrc/dealDataEnvFunction.sh:1206`
- **功能**: 分析单帧中特定晶型各晶粒的原子数
- **用法**: `analysis_grains_size <crystal_type> <xyz_file>`
- **说明**: 输出 grain_CrystalType_count.txt

### AlN_analyze_phase()
- **文件**: `envsrc/tempEnvFunction.sh:498`
- **功能**: 并行分析 AlN 所有 dump.xyz 结晶相（SC + HEX_DIAMOND）
- **用法**: `AlN_analyze_phase`
- **说明**: 查找所有 dump.xyz；并行调用 analyze_crystallinity_fraction

### check_dump_sc_lastcol()
- **文件**: `envsrc/tempEnvFunction.sh:522`
- **功能**: 检查所有 SC 相分析结果是否为零
- **用法**: `check_dump_sc_lastcol`

### check_dump_hex_lastcol()
- **文件**: `envsrc/tempEnvFunction.sh:539`
- **功能**: 检查所有 HEX_DIAMOND 相分析结果是否为 1
- **用法**: `check_dump_hex_lastcol`

---

# 11. 数据处理与分析

**源文件**: [envsrc/dealDataEnvFunction.sh](../envsrc/dealDataEnvFunction.sh) (1499行)

## 11.1 列统计分析

### find_column_max()
- **文件**: `envsrc/dealDataEnvFunction.sh:25`
- **功能**: 查找数据文件指定列的数值最大值
- **用法**: `find_column_max <file> <column>`

### find_column_abs_max()
- **文件**: `envsrc/dealDataEnvFunction.sh:54`
- **功能**: 查找指定列绝对值最大值并输出完整行
- **用法**: `find_column_abs_max <file> <column>`

### analysis_column()
- **文件**: `envsrc/dealDataEnvFunction.sh:102`
- **功能**: 完整统计分析：max/min/abs_max/abs_min/mean/std
- **用法**: `analysis_column <file> <column> [skiprows]`
- **说明**: 依赖 python3+numpy

### get_col_average()
- **文件**: `envsrc/dealDataEnvFunction.sh:131`
- **功能**: 计算指定列在行区间内的平均值
- **用法**: `get_col_average <file> <col> [start] [end]`
- **说明**: 依赖 python3+numpy

## 11.2 文件逐行平均

### average_file()
- **文件**: `envsrc/dealDataEnvFunction.sh:178`
- **功能**: 使用 C++ 对多个数据文件逐行平均
- **用法**: `average_file <file1> <file2> [file3...]`
- **说明**: 依赖 g++ + cpp_lib/averagefiles.cpp

### average_file_s()
- **文件**: `envsrc/dealDataEnvFunction.sh:198`
- **功能**: 纯 Shell+awk 逐行平均（无编译依赖）
- **用法**: `average_file_s <file1> <file2> [file3...]`

### average_file_c()
- **文件**: `envsrc/dealDataEnvFunction.sh:228`
- **功能**: C++ 平均 + 自动重命名输出
- **用法**: `average_file_c <file1> <file2> [file3...]`

## 11.3 XYZ 文件解析

### get_energy()
- **文件**: `envsrc/gpumdEnvFunction.sh:561`
- **功能**: 从 GPUMD 风格 xyz 提取所有构型能量
- **用法**: `get_energy [xyz_file]`
- **说明**: 解析注释行 `Energy=` 字段

### get_Lattice()
- **文件**: `envsrc/gpumdEnvFunction.sh:577`
- **功能**: 从 xyz 提取所有构型晶格参数
- **用法**: `get_Lattice [xyz_file]`
- **说明**: 提取 `Lattice="..."` 字段

### get_virial()
- **文件**: `envsrc/gpumdEnvFunction.sh:592`
- **功能**: 从 xyz 提取所有构型位力
- **用法**: `get_virial [xyz_file]`
- **说明**: 提取 `Virial="..."` 字段

### get_configs_num()
- **文件**: `envsrc/gpumdEnvFunction.sh:607`
- **功能**: 统计 xyz 文件构型数量
- **用法**: `get_configs_num [xyz_file]`
- **说明**: 统计 lattice 出现次数

### get_V()
- **文件**: `envsrc/gpumdEnvFunction.sh:623`
- **功能**: 计算每帧晶胞体积（支持 xyz 和 thermo.out）
- **用法**: `get_V [file]`
- **说明**: xyz: Lattice 3×3 矩阵 → 体积；thermo.out: 12 列或 18 列

### get_area_of_xy_and_volume()
- **文件**: `envsrc/gpumdEnvFunction.sh:681`
- **功能**: 计算每帧 xy 面积和斜胞体积
- **用法**: `get_area_of_xy_and_volume <xyz_file>`
- **说明**: 输出 Volume_area_xy.txt（两列）

## 11.4 XYZ 构型选择

### select_xyz_config()
- **文件**: `envsrc/dealDataEnvFunction.sh:335`
- **功能**: 提取指定索引的单构型
- **用法**: `select_xyz_config [xyz_file] [config_index]`
- **说明**: 默认 train.xyz；索引 -1=最后一个；依赖 ase

### select_xyz_configs()
- **文件**: `envsrc/dealDataEnvFunction.sh:361`
- **功能**: 提取指定范围的多个构型
- **用法**: `select_xyz_configs [xyz_file] [start] [end]`
- **说明**: 区间 [start:end+1]

### select_every_nth_config()
- **文件**: `envsrc/dealDataEnvFunction.sh:385`
- **功能**: 每隔 N 帧提取 1 帧（稀释轨迹）
- **用法**: `select_every_nth_config <xyz_file> <n>`
- **说明**: 默认 dump.xyz 步长 10；惰性读取节省内存

### analyze_xyz()
- **文件**: `envsrc/dealDataEnvFunction.sh:413`
- **功能**: 详细分析 xyz 文件结构信息
- **用法**: `analyze_xyz <xyz_file>`
- **说明**: 委托 analyze_xyz_detail.py

### analysis_model()
- **文件**: `envsrc/dealDataEnvFunction.sh:427`
- **功能**: 分析原子模型（总数+各元素计数）
- **用法**: `analysis_model <xyz_file>`
- **说明**: 依赖 ase + collections.Counter

### view_atom()
- **文件**: `envsrc/dealDataEnvFunction.sh:456`
- **功能**: ASE GUI 可视化原子结构
- **用法**: `view_atom <structure_file>`
- **说明**: 支持 POSCAR/xyz 等多种格式

## 11.5 配位数

### calc_coordination_number()
- **文件**: `envsrc/dealDataEnvFunction.sh:1249`
- **功能**: ASE 最小镜像约定计算每个原子配位数
- **用法**: `calc_coordination_number <xyz_file> [r_cut]`
- **说明**: 默认截断 2.5Å；输出 coordination_numbers.txt

## 11.6 Thermo 分析

### analyze_thermo_out()
- **文件**: `envsrc/tempEnvFunction.sh:560`
- **功能**: 分析 GPUMD thermo.out 生成三面板图
- **用法**: `analyze_thermo_out [thermo.out] [every] [first_step]`
- **说明**: 输出 thermo_analysis_data.txt + thermo_analysis_3panel.png；计算相对体积、压强、偏应力

### deal_box()
- **文件**: `envsrc/tempEnvFunction.sh:97`
- **功能**: 绘制 box.raw 体积变化曲线
- **用法**: `deal_box [box.raw]`
- **说明**: Lx×Ly×Lz 计算体积；输出 box.png

### find_dcu_speed()
- **文件**: `envsrc/tempEnvFunction.sh:180`
- **功能**: 批量提取 DCU 任务 GPU 信息和运行速度
- **用法**: `find_dcu_speed`
- **说明**: 查找 std.out*；提取 GPU information + Speed of this run

### visualize_thermo()
- **文件**: `envsrc/dealDataEnvFunction.sh:1478`
- **功能**: ASE 可视化热力学输出
- **用法**: `visualize_thermo <thermo_file>`

## 11.7 文件整理

### copy_each_to_own_dir()
- **文件**: `envsrc/dealDataEnvFunction.sh:1367`
- **功能**: 将指定后缀文件各自放入同名文件夹
- **用法**: `copy_each_to_own_dir [extension]`
- **说明**: 默认 xyz

### cp_file_to_subdirs()
- **文件**: `envsrc/dealDataEnvFunction.sh:1384`
- **功能**: 将文件复制到所有一级子目录
- **用法**: `cp_file_to_subdirs <file>`
- **说明**: 批量分发 INCAR/POTCAR 等

### xyz_group_by_type()
- **文件**: `envsrc/dealDataEnvFunction.sh:1395`
- **功能**: 将 xyz 原子按元素类型分组
- **用法**: `xyz_group_by_type <xyz_file>`

### grouping_to_xyz()
- **文件**: `envsrc/dealDataEnvFunction.sh:1412`
- **功能**: 按方向原子比例分组
- **用法**: `grouping_to_xyz <xyz_file> <x/y/z> <ratio1> <ratio2> <ratio3>`

## 11.8 其他工具

### generate_large_primes()
- **文件**: `envsrc/dealDataEnvFunction.sh:1460`
- **功能**: 生成指定数量的质数（用于 HNEMD 种子）
- **用法**: `generate_large_primes <count> [start]`
- **说明**: 默认起始 10001；纯 Shell 试除法

### del_caf2xyz_F()
- **文件**: `envsrc/tempEnvFunction.sh:4`
- **功能**: 删除 xyz 中 CaF2 结构的 F 原子
- **用法**: `del_caf2xyz_F [dump.xyz] [output]`
- **说明**: C++ 内联编译执行

### zone_group_to_xyz()
- **文件**: `envsrc/dealDataEnvFunction.sh:615`
- **功能**: 按空间区域分组原子（组1=区域内，组0=区域外）
- **用法**: `zone_group_to_xyz <xyz_file> <x/y/z> <min> <max>`

### crystal_face_distance_grouping()
- **文件**: `envsrc/dealDataEnvFunction.sh:643`
- **功能**: 按晶面距离分组原子
- **用法**: `crystal_face_distance_grouping <xyz_file> <[h,k,l]> <min> <max>`

---

# 12. 可视化与绘图

**源文件**: `envsrc/gpumdEnvFunction.sh` + `plot_library/` + `envsrc/dealDataEnvFunction.sh`

## 12.1 NEP 结果可视化

### plot_nep()
- **文件**: `envsrc/gpumdEnvFunction.sh:81`
- **功能**: 默认配置绘制 NEP 训练结果
- **用法**: `plot_nep`
- **说明**: 需在含 loss.out 的目录运行；委托 hplt_nep_results.py

### plot_ultimate_nep()
- **文件**: `envsrc/gpumdEnvFunction.sh:96`
- **功能**: 出版级 NEP 训练结果图
- **用法**: `plot_ultimate_nep`
- **说明**: 优化配色；适合论文/报告

### plot_E_F_Vir_distribution()
- **文件**: `envsrc/gpumdEnvFunction.sh:114`
- **功能**: 训练集 E/F/Virial 三面板分布直方图
- **用法**: `plot_E_F_Vir_distribution [train.xyz]`
- **说明**: 依赖 nebula 库；600dpi 输出

## 12.2 轨迹可视化

### plot_E_frame()
- **文件**: `envsrc/gpumdEnvFunction.sh:720`
- **功能**: 能量随 MD 步数变化曲线
- **用法**: `plot_E_frame [file] [dump_interval]`
- **说明**: 支持 xyz/thermo.out；输出 E-frame.png

### plot_volume_per_atom_xyz()
- **文件**: `envsrc/dealDataEnvFunction.sh:286`
- **功能**: 每原子体积随帧数变化图
- **用法**: `plot_volume_per_atom_xyz <xyz_file> [output.dat] [output.png]`
- **说明**: 依赖 ase；自动验证晶格

## 12.3 快速绘图

### replot()
- **文件**: `envsrc/dealDataEnvFunction.sh:253`
- **功能**: 两列数据快速 X-Y 散点图
- **用法**: `replot <data_file>`
- **说明**: 输出 plot.png

---

# 13. GPU 任务调度 & 超算集群

**源文件**: [rebreath-env-function](../rebreath-env-function) (§6-7) + `envsrc/tempEnvFunction.sh`

## 13.1 GPU 自动调度

### free_gpu_run()
- **文件**: `rebreath-env-function:334`
- **功能**: 轮询 GPU，在第一个空闲 GPU 上运行命令（文件锁安全）
- **用法**: `free_gpu_run <pid_var> <command>`
- **说明**: 环境变量: GPU_FREE_MEM_THRESHOLD_MB(500), GPU_FREE_UTIL_THRESHOLD(10), GPU_WAIT_INTERVAL(20)；flock 防冲突

### free_time_run()
- **文件**: `rebreath-env-function:400`
- **功能**: 轮询 GPU 直到有 <200MB 使用的卡，执行命令
- **用法**: `free_time_run 'nohup gpumd 2>&1 &'`
- **说明**: 简化版，无锁；日志 run_train-file.log

### wait_and_run()
- **文件**: `rebreath-env-function:301`
- **功能**: 等待 PID 结束后在空闲 GPU 执行后续命令
- **用法**: `wait_and_run <PID> "command" [interval]`
- **说明**: 默认间隔 60s

### pfrun()
- **文件**: `rebreath-env-function:443`
- **功能**: 并行查找文件并在每个所在目录执行命令
- **用法**: `pfrun <file_pattern> <command> [--jobs N] [--dry-run] [--quiet]`
- **说明**: 委托 parallel_find_run.sh

## 13.2 进程管理

### find_nohup_task()
- **文件**: `rebreath-env-function:277`
- **功能**: 查找 nohup 后台进程
- **用法**: `find_nohup_task "gpumd"`

### pwdxcd()
- **文件**: `rebreath-env-function:284`
- **功能**: cd 到指定 PID 的工作目录
- **用法**: `pwdxcd <PID>`

---

# 14. 结构操作 (扩胞/缺陷/吸附)

**源文件**: `envsrc/dealDataEnvFunction.sh` + `envsrc/tempEnvFunction.sh` + `envsrc/gpumdEnvFunction.sh`

## 14.1 超胞构建

### expand_cell()
- **文件**: `envsrc/dealDataEnvFunction.sh:497`
- **功能**: ASE 扩胞
- **用法**: `expand_cell <xyz_file> <nx> <ny> <nz>`
- **说明**: 默认 model.xyz；输出 expanded.xyz

### supercell_auto_cubic()
- **文件**: `envsrc/dealDataEnvFunction.sh:522`
- **功能**: 智能扩胞（自动判断系数，趋近正方体）
- **用法**: `supercell_auto_cubic <xyz_file> <target_number>`

### suggest_expand_coefficient()
- **文件**: `envsrc/dealDataEnvFunction.sh:542`
- **功能**: 建议正交晶胞扩胞系数使总原子数接近目标
- **用法**: `suggest_expand_coefficient <xyz_file> [target_count]`
- **说明**: 默认 10000 原子；依赖 ase+numpy

### suggest_expand_coefficient_nebula()
- **文件**: `envsrc/dealDataEnvFunction.sh:578`
- **功能**: 同上但使用 nebula 库（非 ASE）
- **用法**: `suggest_expand_coefficient_nebula <xyz_file> [target_count]`

### cell_expansion()
- **文件**: `envsrc/gpumdEnvFunction.sh:424`
- **功能**: 使用 GPUMD 对 xyz 结构扩胞（replicate）
- **用法**: `cell_expansion <nx> <ny> <nz>`
- **说明**: 需 model.xyz + nep.txt；输出 expanded.xyz

## 14.2 缺陷与表面

### generate_vacancy_defect_xyz()
- **文件**: `envsrc/dealDataEnvFunction.sh:694`
- **功能**: 随机生成空位缺陷
- **用法**: `generate_vacancy_defect_xyz <input.xyz> <output.xyz> <fraction> [species] [seed]`
- **说明**: 支持指定元素或所有元素

### cutting_crystal_surface()
- **文件**: `envsrc/dealDataEnvFunction.sh:671`
- **功能**: ASE 切割晶面生成 slab
- **用法**: `cutting_crystal_surface <xyz_file> <h> <k> <l>`
- **说明**: 默认 1 层

## 14.3 吸附/脱附

### get_molecule()
- **文件**: `envsrc/dealDataEnvFunction.sh:748`
- **功能**: ASE 生成分子 xyz 结构
- **用法**: `get_molecule <molecule_formula>`
- **说明**: 如 H2O, HCOOH, O3；输出 adsorbate.xyz

### build_adsorption_model()
- **文件**: `envsrc/dealDataEnvFunction.sh:768`
- **功能**: 构建基底+吸附分子模型（自动找位点）
- **用法**: `build_adsorption_model <substrate.xyz> <adsorbate_formula>`
- **说明**: 依赖 pymatgen；输出多个 adsorbed_structure_N.xyz

### build_disorption_model()
- **文件**: `envsrc/dealDataEnvFunction.sh:802`
- **功能**: 构建脱附模型（分子远离基底）
- **用法**: `build_disorption_model <substrate.xyz> <molecule> [min_distance]`
- **说明**: 默认 10Å 距离；输出 POSCAR_desorption.vasp

### fix_adsorption_model()
- **文件**: `envsrc/tempEnvFunction.sh:430`
- **功能**: 创建固定文件夹并固定吸附模型底层
- **用法**: `fix_adsorption_model <model> <fix_height>`
- **说明**: 调用 fix_poscar_zCar

## 14.4 其他

### atom_dist()
- **文件**: `envsrc/dealDataEnvFunction.sh:477`
- **功能**: 计算两个原子欧几里得距离（不考虑 PBC）
- **用法**: `atom_dist <x1> <y1> <z1> <x2> <y2> <z2>`

---

# 15. 碳纤维分析

**源文件**: [envsrc/dealDataEnvFunction.sh](../envsrc/dealDataEnvFunction.sh) (§9)

### analyze_cf()
- **文件**: `envsrc/dealDataEnvFunction.sh:1289`
- **功能**: 碳纤维综合分析（碳环统计/XRD/RDF）
- **用法**: `analyze_cf <xyz_file>`
- **说明**: 依赖 cf_analyze + xrd 外部工具；输出碳环分布、RDF、XRD 图谱

### calc_cf_spatoms()
- **文件**: `envsrc/dealDataEnvFunction.sh:1333`
- **功能**: 碳纤维杂化原子和结晶率（已弃用）
- **用法**: `calc_cf_spatoms <xyz_file>`

### calc_xrd_usedebyer()
- **文件**: `envsrc/dealDataEnvFunction.sh:1348`
- **功能**: debyer 软件计算粉末 XRD 谱图
- **用法**: `calc_xrd_usedebyer [xyz_file]`
- **说明**: 波长 1.5406Å；终角 80°；步长 0.02

---

# 16. 媒体处理 & 日常工具

**源文件**: [envsrc/liveEnvFunction.sh](../envsrc/liveEnvFunction.sh) (723行)

## 16.1 图片/视频

### compress_all_gif()
- **文件**: `envsrc/liveEnvFunction.sh:4`
- **功能**: 批量压缩大于阈值的 GIF 文件
- **用法**: `compress_all_gif [阈值MB]`
- **说明**: 默认 3MB；依赖 ffmpeg

### convert_video_to_gif()
- **文件**: `envsrc/liveEnvFunction.sh:32`
- **功能**: 视频 → GIF 动图
- **用法**: `convert_video_to_gif input.mp4 [output.gif]`
- **说明**: fps=10, scale=320:-1；palettegen/paletteuse 优化

### png2pdf()
- **文件**: `envsrc/liveEnvFunction.sh:134`
- **功能**: PNG 合并转 PDF
- **用法**: `png2pdf in.png [out.pdf]` 或 `png2pdf *.png out.pdf`
- **说明**: 依赖 Pillow；自动处理透明背景

### pdf2eps()
- **文件**: `envsrc/liveEnvFunction.sh:172`
- **功能**: 目录中所有 PDF → EPS
- **用法**: `pdf2eps [输入目录] [输出目录]`
- **说明**: 依赖 poppler(pdftops)

### pdfs_to_eps_pages()
- **文件**: `envsrc/liveEnvFunction.sh:194`
- **功能**: PDF 每页拆分为独立 EPS
- **用法**: `pdfs_to_eps_pages [输入目录] [输出目录]`
- **说明**: 依赖 pdfinfo + pdftops

## 16.2 音频/TTS

### txt2mp3()
- **文件**: `envsrc/liveEnvFunction.sh:223`
- **功能**: TXT 文本并行转 MP3 有声文件
- **用法**: `txt2mp3 [-j 并行数] [-v 语音] 文件1.txt [文件2.txt ...]`
- **说明**: edge-tts (Azure TTS)；默认 zh-CN-XiaoxiaoNeural

### novel_txt_to_mp3()
- **文件**: `envsrc/liveEnvFunction.sh:433`
- **功能**: 小说按章节切分逐章转 MP3
- **用法**: `novel_txt_to_mp3 <小说.txt> [输出目录] [并行数]`
- **说明**: 正则识别第X章/Chapter；支持 UTF-8/GB18030

### to_mp3()
- **文件**: `envsrc/liveEnvFunction.sh:319`
- **功能**: 任意音频/视频 → MP3
- **用法**: `to_mp3 <输入文件> [输出.mp3]`
- **说明**: ffmpeg；libmp3lame 128kbps 44100Hz

### to_flac_light()
- **文件**: `envsrc/liveEnvFunction.sh:359`
- **功能**: 音频转轻量 FLAC（voice/voice32/keep 三种模式）
- **用法**: `to_flac_light <输入文件> [输出.flac] [模式]`
- **说明**: voice: 单声道 22050Hz

## 16.3 其他工具

### catmd()
- **文件**: `envsrc/liveEnvFunction.sh:111`
- **功能**: 终端渲染 Markdown
- **用法**: `catmd [README.md]`
- **说明**: 依赖 python3 rich 库

### compare_folders()
- **文件**: `envsrc/liveEnvFunction.sh:57`
- **功能**: 对比两文件夹同名文件差异
- **用法**: `compare_folders <folder1> <folder2>`

### get_map_distance()
- **文件**: `envsrc/liveEnvFunction.sh:616`
- **功能**: 高德地图查询两地驾车距离/时间
- **用法**: `mapdist <出发地> <目的地>` 或 `mapdist <目的地>`
- **别名**: `mapdist`

### cp2desktop() / mv2desktop()
- **文件**: `envsrc/tempEnvFunction.sh:488` / `:492`
- **功能**: 复制/移动文件到 Windows 桌面
- **用法**: `cp2desktop <file>` / `mv2desktop <file>`

---

# 17. 核心工具函数

**源文件**: [rebreath-env-function](../rebreath-env-function) (549行)

## 17.1 库管理

### loadrenv()
- **文件**: `rebreath-env-function:38`
- **功能**: 重新加载 NebulaFlow 环境（编辑后刷新）
- **用法**: `loadrenv`

### update_NebulaFlow()
- **文件**: `rebreath-env-function:47`
- **功能**: 从 GitHub 拉取最新代码并重装
- **用法**: `update_NebulaFlow`

### relib()
- **文件**: `rebreath-env-function:66`
- **功能**: 按关键词搜索并复制/查看库文件
- **用法**: `relib [-v] [-m] <keyword1> [keyword2 ...]`
- **说明**: -v 仅查看；-m 多层关键词搜索

## 17.2 文件记忆系统 (recc 系列)

### recc()
- **文件**: `rebreath-env-function:151`
- **功能**: 记录文件路径到临时记忆
- **用法**: `recc file1.txt file2.xyz`

### recat()
- **文件**: `rebreath-env-function:172`
- **功能**: 查看记忆的文件列表
- **用法**: `recat`

### revv()
- **文件**: `rebreath-env-function:183`
- **功能**: 将记忆的文件复制到目标目录
- **用法**: `revv [target_dir]`

### reclean()
- **文件**: `rebreath-env-function:164`
- **功能**: 清空文件记忆
- **用法**: `reclean`

## 17.3 路径与数学

### wslcd()
- **文件**: `rebreath-env-function:195`
- **功能**: 智能 cd（支持 Windows 路径自动转换）
- **用法**: `wslcd D:\NebulaFlow`

### winpath()
- **文件**: `rebreath-env-function:211`
- **功能**: Windows 路径 → WSL 路径（仅输出）
- **用法**: `winpath D:\NebulaFlow`

### pow()
- **文件**: `rebreath-env-function:229`
- **功能**: 整数幂运算
- **用法**: `pow 2 10` → 1024

### calc_time()
- **文件**: `rebreath-env-function:236`
- **功能**: 测量命令执行时间（毫秒）
- **用法**: `calc_time "gpumd"`

### addpath()
- **文件**: `rebreath-env-function:247`
- **功能**: 添加目录到 PATH
- **用法**: `addpath /path/to/dir`

### wc_file_lines()
- **文件**: `rebreath-env-function:254`
- **功能**: 按扩展名统计代码行数
- **用法**: `wc_file_lines cpp h py`

## 17.4 目录管理

### dirman()
- **文件**: `rebreath-env-function:455`
- **功能**: 读取并显示目录的 .dirlog 文件
- **用法**: `dirman /path/to/dir`

### wdlog()
- **文件**: `rebreath-env-function:467`
- **功能**: 编辑目录的 .dirlog 文件
- **用法**: `wdlog [path]`

### search_large_files()
- **文件**: `rebreath-env-function:320`
- **功能**: 查找大于 20GB 的文件
- **用法**: `search_large_files /home/user`

## 17.5 网络

### proxy_download()
- **文件**: `rebreath-env-function:120`
- **功能**: 通过 SSH 代理下载文件
- **用法**: `proxy_download "wget http://example.com/file.tar.gz"`

### use_agent()
- **文件**: `rebreath-env-function:112`
- **功能**: 设置 HTTP 代理
- **用法**: `use_agent`

## 17.6 教学/玩具

### compute_high_of_tree()
- **文件**: `rebreath-env-function:481`
- **功能**: Shell+C++ 教学示例（动态编译执行）
- **用法**: `compute_high_of_tree`

### gpt9()
- **文件**: `rebreath-env-function:513`
- **功能**: 简易聊天机器人玩具
- **用法**: `gpt9`

### mycat()
- **文件**: `rebreath-env-function:530`
- **功能**: 猫模拟器玩具
- **用法**: `mycat`

---

# 附录A: 按源文件索引

| 源文件 | 路径 | 函数数 | 主要领域 |
|--------|------|--------|----------|
| `rebreath-env-function` | 根目录 | ~20 | 核心工具/GPU调度/文件管理 |
| `vaspEnvFunction.sh` | envsrc/ | ~10 | VASP 计算 |
| `gpumdEnvFunction.sh` | envsrc/ | ~38 | GPUMD/NEP/HNEMD/弹性/声子 |
| `dealDataEnvFunction.sh` | envsrc/ | ~46 | 数据处理/结晶度/结构操作/碳纤维 |
| `tempEnvFunction.sh` | envsrc/ | ~31 | 模板流程/VASP多阶段/AlN分析 |
| `liveEnvFunction.sh` | envsrc/ | ~12 | 媒体处理/音频/PDF |
| `ioEnvFunction.sh` | envsrc/ | ~7 | 格式转换 |
| `lammpsEnvFunction.sh` | envsrc/ | ~4 | LAMMPS 任务 |
| `cp2kEnvFunction.sh` | envsrc/ | ~5 | CP2K 计算 |
| `lsmdtoolsEnvFunction.sh` | envsrc/ | ~6 | LSMD 验证 |

> **注**: 部分函数在多个文件中重复定义（如 `update_cp2k_inp_cell_from_xyz` 在3个文件中均有定义）。

---

# 附录B: 按函数名 A-Z 索引

| 函数名 | 章节 | 功能关键词 |
|--------|------|-----------|
| `add_kpoints` | §1.2 | VASP KPOINTS 生成 |
| `add_kspacing_to_incar` | §1.2 | INCAR KSPACING |
| `add_potcar` | §1.2 | VASP POTCAR 生成 |
| `addpath` | §17.3 | PATH 管理 |
| `AlN_analyze_phase` | §10 | AlN 结晶相分析 |
| `analysis_column` | §11.1 | 列统计分析 |
| `analysis_grains_size` | §10 | 晶粒原子数 |
| `analysis_model` | §11.4 | 原子模型分析 |
| `analyze_allcrystallinity_fraction` | §10 | 全晶型分析 |
| `analyze_cf` | §15 | 碳纤维综合分析 |
| `analyze_crystallinity_fraction` | §10 | 单晶型比例 |
| `analyze_crystallinity_frame_counts` | §10 | 单帧晶型统计 |
| `analyze_mulcrystallinity_fraction` | §10 | 多晶型分析 |
| `analyze_thermo_out` | §11.6 | thermo.out 分析 |
| `analyze_xyz` | §11.4 | xyz 结构分析 |
| `atom_dist` | §14.4 | 原子间距 |
| `average_file` | §11.2 | C++ 文件平均 |
| `average_file_c` | §11.2 | C++ 平均+重命名 |
| `average_file_s` | §11.2 | Shell 文件平均 |
| `build_adsorption_model` | §14.3 | 吸附模型 |
| `build_disorption_model` | §14.3 | 脱附模型 |
| `build_stages` | §8 | CP2K 多阶段 |
| `calc_cf_spatoms` | §15 | 碳纤维杂化(弃用) |
| `calc_coordination_number` | §11.5 | 配位数 |
| `calc_time` | §17.3 | 执行计时 |
| `calc_xrd_usedebyer` | §15 | XRD 计算 |
| `catmd` | §16.3 | Markdown 渲染 |
| `cdcomparedir` | §9 | LSMD 对比目录 |
| `cell_expansion` | §14.1 | GPUMD 扩胞 |
| `check_dataset_quality` | §3.2 | NEP 训练集诊断 |
| `check_dump_hex_lastcol` | §10 | HEX 相检查 |
| `check_dump_sc_lastcol` | §10 | SC 相检查 |
| `check_hnemd_thermo` | §4.2 | HNEMD thermo 检查 |
| `check_stage_energy` | §8 | CP2K stage 能量 |
| `check_vasp_complete` | §1.1 | VASP 完成检查 |
| `clean_poscar` | §6.3 | POSCAR 清理 |
| `clean_vasp_out` | §1.2 | VASP 输出清理 |
| `clearcompare` | §9 | LSMD 清理 |
| `compare_folders` | §16.3 | 文件夹对比 |
| `compare_nepdata` | §3.2 | NEP 数据对比 |
| `compress_all_gif` | §16.1 | GIF 压缩 |
| `compute_elastic_moduli` | §5 | 弹性模量 |
| `compute_high_of_tree` | §17.6 | 教学示例 |
| `compute_phonon_spectrum` | §5 | 声子谱 |
| `convert_video_to_gif` | §16.1 | 视频转GIF |
| `copy_each_to_own_dir` | §11.7 | 文件归档 |
| `cp2desktop` | §16.3 | 复制到桌面 |
| `cp2krestart2cif` | §8 | restart→CIF |
| `cp2krestart2xyz` | §8 | restart→XYZ |
| `cp2kstart` | §8 | CP2K 提交 |
| `cp_file_to_subdirs` | §11.7 | 文件分发 |
| `crystal_face_distance_grouping` | §11.8 | 晶面分组 |
| `cutting_crystal_surface` | §14.2 | 晶面切割 |
| `deal_AlN_diff_axis_deform` | §10 | AlN 多轴分析 |
| `deal_box` | §11.6 | box.raw 绘图 |
| `deal_hnemd_data` | §4.2 | HNEMD 一键处理 |
| `deal_outcar_to_train` | §1.4/§3.3 | OUTCAR→train.xyz |
| `deal_strain_fluctuation_to_elastic` | §4.2 | 应变波动→弹性 |
| `del_caf2xyz_F` | §11.8 | 删除 CaF2 F 原子 |
| `dirman` | §17.4 | .dirlog 阅读 |
| `expand_cell` | §14.1 | ASE 扩胞 |
| `find_column_abs_max` | §11.1 | 列绝对最大值 |
| `find_column_max` | §11.1 | 列最大值 |
| `find_dcu_speed` | §11.6 | DCU 速度提取 |
| `find_nohup_task` | §13.2 | 进程查找 |
| `fix_adsorption_model` | §14.3 | 吸附模型固定 |
| `fix_poscar_zCar` | §1.4 | POSCAR 绝对坐标固定 |
| `fix_poscar_zFrc` | §1.4 | POSCAR 分数坐标固定 |
| `free_gpu_run` | §13.1 | GPU 空闲调度(锁) |
| `free_time_run` | §13.1 | GPU 空闲调度(简) |
| `generate_band_plot` | §1.4/§5 | 声子色散图 |
| `generate_large_primes` | §11.8 | 质数生成 |
| `generate_vacancy_defect_xyz` | §14.2 | 空位缺陷 |
| `get_area_of_xy_and_volume` | §11.3 | xy面积+体积 |
| `get_col_average` | §11.1 | 列区间平均 |
| `get_configs_num` | §11.3 | xyz 构型数 |
| `get_cp2k_energy` | §8 | CP2K 能量提取 |
| `get_energy` | §11.3 | xyz 能量提取 |
| `get_grain_count` | §10 | 晶粒计数 |
| `get_hnemd_data` | §4.2 | HNEMD 三向绘图 |
| `get_Lattice` | §11.3 | xyz 晶格提取 |
| `get_map_distance` | §16.3 | 高德地图 |
| `get_molecule` | §14.3 | 分子结构生成 |
| `get_phonon_spectrum_mpdata` | §5 | MP 声子谱 |
| `get_V` | §11.3 | 晶胞体积 |
| `get_virial` | §11.3 | xyz 位力提取 |
| `gpt9` | §17.6 | 聊天机器人 |
| `grouping_to_xyz` | §11.7 | 比例分组 |
| `gpumdstart_dcu` | §2.2 | 曙光 DCU 提交 |
| `gpumdstart_rebreath` | §2.2 | 曙光 rebreath 分区 |
| `gpumdstart_zwj` | §2.2 | 曙光 zwj 分区 |
| `lammpsrun` | §7 | LAMMPS 提交 |
| `loadrenv` | §17.1 | 环境重载 |
| `load_single_point_energy_dir` | §1.2/§3.3 | 单点能目录 |
| `merge_lmp` | §7 | LAMMPS data 合并 |
| `metal2real` | §9 | 单位转换 |
| `mv2desktop` | §16.3 | 移动到桌面 |
| `mycat` | §17.6 | 猫模拟器 |
| `novel_txt_to_mp3` | §16.2 | 小说TTS |
| `outcar_get_virial` | §1.4 | OUTCAR 位力 |
| `pdf2eps` | §16.1 | PDF→EPS |
| `pdfs_to_eps_pages` | §16.1 | PDF 拆分 EPS |
| `pfrun` | §13.1 | 并行查找运行 |
| `plot_E_frame` | §12.2 | 能量-帧数图 |
| `plot_E_F_Vir_distribution` | §12.1 | E/F/Vir 分布 |
| `plot_hnemd` | §4.2 | HNEMD 单方向图 |
| `plot_hnemd_para` | §4.2 | HNEMD 并行绘图 |
| `plot_mul_hnemd` | §4.2 | HNEMD 平均图 |
| `plot_mul_stress_strain_curve` | §2.3 | 多向应力应变 |
| `plot_nep` | §12.1 | NEP 结果图 |
| `plot_stress_strain_curve` | §2.3 | 应力应变曲线 |
| `plot_ultimate_nep` | §12.1 | NEP 出版图 |
| `plot_volume_per_atom_xyz` | §12.2 | 体积/原子图 |
| `png2pdf` | §16.1 | PNG→PDF |
| `pow` | §17.3 | 幂运算 |
| `proxy_download` | §17.5 | 代理下载 |
| `pwdxcd` | §13.2 | PID 工作目录 |
| `recc` | §17.2 | 文件记忆 |
| `recat` | §17.2 | 记忆查看 |
| `reclean` | §17.2 | 记忆清空 |
| `relib` | §17.1 | 库文件搜索 |
| `repeat_buildgpumd` | §2.1 | GPUMD 副本 |
| `repeat_rungpumd` | §2.1 | GPUMD 并行启动 |
| `replot` | §12.3 | 快速绘图 |
| `revv` | §17.2 | 记忆输出 |
| `run_all_vasp_job` | §1.1/§3.3 | 批量 VASP |
| `screening_reasonable_energy` | §3.1 | 能量筛选 |
| `screening_reasonable_forces` | §3.1 | 力筛选 |
| `screening_reasonable_virial` | §3.1 | 位力筛选 |
| `search_large_files` | §17.4 | 大文件查找 |
| `select_every_nth_config` | §11.4 | 等距抽帧 |
| `select_xyz_config` | §11.4 | 单构型提取 |
| `select_xyz_configs` | §11.4 | 范围构型提取 |
| `shift_lmp_data` | §7 | LAMMPS 平移 |
| `sortlmpdata` | §7 | LAMMPS 排序 |
| `start_gpumd` | §2.1 | GPUMD 启动 |
| `start_mul_hnemd` | §4.1 | 批量 HNEMD |
| `start_mul_hnemd_shuguang` | §4.1 | 曙光批量 HNEMD |
| `submit_gpumd` | §2.2 | GPUMD Slurm |
| `submit_lmp_matpl` | §7 | LAMMPS Slurm |
| `suggest_expand_coefficient` | §14.1 | 扩胞建议(ASE) |
| `suggest_expand_coefficient_nebula` | §14.1 | 扩胞建议(nebula) |
| `supercell_auto_cubic` | §14.1 | 智能扩胞 |
| `testlmpdir` | §9 | LAMMPS 目录测试 |
| `testlmpmod` | §9 | LAMMPS 模块测试 |
| `testlsmdmod` | §9 | LSMD 分量测试 |
| `to_flac_light` | §16.2 | FLAC 转换 |
| `to_mp3` | §16.2 | MP3 转换 |
| `tran_cif2xyz` | §6.3 | CIF→XYZ |
| `tran_data2xyz` | §6.2 | Data→XYZ |
| `tran_pos2xyz` | §6.1 | POSCAR→XYZ |
| `tran_xyz2cif` | §6.3 | XYZ→CIF |
| `tran_xyz2cssr` | §6.3 | XYZ→CSSR |
| `tran_xyz2data` | §6.2 | XYZ→Data |
| `tran_xyz2pdb` | §6.3 | XYZ→PDB |
| `tran_xyz2pos` | §6.1 | XYZ→POSCAR |
| `txt2mp3` | §16.2 | TXT→MP3 |
| `update_cp2k_inp_cell_from_xyz` | §8 | CP2K 晶胞更新 |
| `update_NebulaFlow` | §17.1 | 库更新 |
| `use_agent` | §17.5 | HTTP 代理 |
| `use_pbc_run` | §8 | PBC CP2K |
| `use_sccs_run` | §8 | SCCS CP2K |
| `vasprun` | §1.1 | VASP CPU 提交 |
| `vasprun_dcu` | §1.1 | VASP DCU 提交 |
| `vaspstart_geo_optstage1` | §1.3 | 优化阶段1 |
| `vaspstart_geo_optstage2` | §1.3 | 优化阶段2 |
| `vaspstart_geo_optstage3` | §1.3 | 优化阶段3 |
| `vaspstart_single_energy` | §1.3 | 单点能 |
| `vaspstart_single_energy_after_relaxation` | §1.3 | 驰豫后单点能 |
| `verify_deform` | §2.3 | 拉伸验算 |
| `verify_gpumd_result` | §2.1 | GPUMD 验算 |
| `view_atom` | §11.4 | 结构可视化 |
| `visualize_thermo` | §11.6 | Thermo 可视化 |
| `wait_and_run` | §13.1 | 等待执行 |
| `wait_complete_vasp_run` | §1.1 | 等待 VASP |
| `wait_geo_run_SE` | §1.3 | 等待优化+单点能 |
| `wc_file_lines` | §17.3 | 代码行统计 |
| `wdlog` | §17.4 | .dirlog 编辑 |
| `winpath` | §17.3 | 路径转换 |
| `wslcd` | §17.3 | WSL cd |
| `xyz_group_by_type` | §11.7 | 元素分组 |
| `zone_group_to_xyz` | §11.8 | 空间分组 |

---

> **手册结束** | 最后更新: 2026-06-28 | NebulaFlow by rebreath
