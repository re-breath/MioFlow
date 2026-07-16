"""
MioFlow CLI — 澪の命令行入口 ♡
=================================
用法：mio <命令> [参数...]

将任何 MioFlow 工具变成随处可用的 CLI 命令。
"""

import sys
import os
import subprocess
import fnmatch

MIO_HOME = os.path.expanduser("~/.mio")
MIO_VERSION = "0.1.0"


def _get_cmds():
    """扫描 MIO_HOME 下所有 Python 和可执行脚本"""
    cmds = {}
    if not os.path.isdir(MIO_HOME):
        return cmds
    for root, dirs, files in os.walk(MIO_HOME):
        # 跳过隐藏目录和 __pycache__
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        for f in files:
            if f.startswith('.'):
                continue
            # 去掉扩展名作为命令名
            name, ext = os.path.splitext(f)
            if ext in ('.py', '.sh'):
                fpath = os.path.join(root, f)
                # 用相对路径作为 key 防止重名
                rel = os.path.relpath(fpath, MIO_HOME)
                cmds[name] = fpath
                cmds[rel] = fpath
    return cmds


def _list_commands():
    """列出所有可用的 MioFlow 命令"""
    cmds = _get_cmds()
    if not cmds:
        print("( ˘͈ ᵕ ˘͈ ) 还没有安装 MioFlow 呢～ 先运行 MioFlowinstaller.sh 吧！")
        return

    # 按目录分组
    groups = {}
    for rel, fpath in sorted(cmds.items()):
        if '/' in rel:
            group, name = rel.split('/', 1)
        else:
            group, name = 'root', rel
        name = name.rsplit('.', 1)[0] if '.' in name else name
        groups.setdefault(group, []).append(name)

    print(f"MioFlow v{MIO_VERSION} — 澪の工具箱 ♡")
    print(f"{'='*40}")
    for group, names in sorted(groups.items()):
        print(f"\n  [{group}/]")
        for n in sorted(set(names)):
            print(f"    {n}")
    print()


def _find_command(cmd):
    """查找命令对应的脚本路径"""
    cmds = _get_cmds()
    # 精确匹配
    if cmd in cmds:
        return cmds[cmd]
    # 尝试加上 .py / .sh 后缀
    for ext in ('.py', '.sh'):
        if cmd + ext in cmds:
            return cmds[cmd + ext]
        # 也试试在子目录中
        for rel, fpath in cmds.items():
            if rel.endswith('/' + cmd) or rel.endswith('/' + cmd + ext):
                return fpath
    return None


def _run_script(fpath, args):
    """执行脚本"""
    _, ext = os.path.splitext(fpath)
    if ext == '.py':
        cmd = [sys.executable, fpath] + args
    elif ext == '.sh':
        cmd = ['bash', fpath] + args
    else:
        cmd = [fpath] + args

    try:
        os.execvp(cmd[0], cmd)
    except FileNotFoundError:
        print(f"Error: 找不到解释器执行 {fpath}")
        sys.exit(1)


def main():
    """CLI 入口"""
    if len(sys.argv) < 2 or sys.argv[1] in ('--help', '-h'):
        print("MioFlow — 澪の工具箱 ♡")
        print()
        print("用法:")
        print("  mio <命令> [参数...]")
        print("  mio --list, -l    列出所有可用命令")
        print("  mio --help, -h    显示此帮助")
        print()
        print("示例:")
        print("  mio nebula.py --help")
        print("  mio analyze_xyz_detail.py train.xyz")
        print("  mio tran_xyz2cssr input.xyz output.cssr")
        print()
        print("提示: 很多命令需要通过 bash source mio-env-function 来使用完整功能。")
        print("      这个 CLI 只是帮你快速定位和执行脚本。")
        sys.exit(0)

    if sys.argv[1] in ('--list', '-l'):
        _list_commands()
        sys.exit(0)

    cmd = sys.argv[1]
    args = sys.argv[2:]

    fpath = _find_command(cmd)
    if not fpath:
        print(f"澪找不到命令 '{cmd}' 呢 (｡ŏ﹏ŏ)")
        print(f"试试 mio --list 看看有什么可用命令吧～")
        sys.exit(1)

    _run_script(fpath, args)


if __name__ == "__main__":
    main()
