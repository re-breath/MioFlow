"""MioFlow command catalogue and script launcher."""

from __future__ import annotations

import ast
import os
import re
import shutil
import sys
import textwrap
import unicodedata
import warnings
from dataclasses import dataclass
from functools import lru_cache
from importlib import metadata
from pathlib import Path
from typing import Iterable


MIO_HOME = Path(os.environ.get("MIO_HOME", "~/.mio")).expanduser().resolve()
MANUAL_RELATIVE_PATH = Path("Manual/MioFlow-Function-Reference.md")
SCRIPT_ROOTS = (
    "auto",
    "compute_lib",
    "deal_data",
    "exhibit_lib",
    "plot_library",
    "sh_lib",
)
ROOT_SCRIPT_SKIP = {"MioFlowinstaller.sh"}
SCRIPT_EXCLUDED_PARTS = {"__pycache__", "discard", ".git", ".wink"}


@dataclass(frozen=True)
class ManualCommand:
    name: str
    description: str
    usage: str
    section: str
    subsection: str
    source: str
    notes: str
    line: int


@dataclass(frozen=True)
class ScriptCommand:
    name: str
    canonical: str
    path: Path
    description: str
    kind: str


def _version() -> str:
    try:
        return metadata.version("mioflow")
    except metadata.PackageNotFoundError:
        return "0.1.0"


def _manual_path() -> Path:
    candidates = (
        MIO_HOME / MANUAL_RELATIVE_PATH,
        Path(__file__).resolve().parents[1] / MANUAL_RELATIVE_PATH,
    )
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


def _clean_markdown(value: str) -> str:
    value = re.sub(r"\[([^]]+)]\([^)]+\)", r"\1", value)
    value = value.replace("`", "").replace("**", "")
    return re.sub(r"\s+", " ", value).strip()


def _parse_manual(path: Path | None = None) -> list[ManualCommand]:
    manual = path or _manual_path()
    if not manual.is_file():
        return []

    lines = manual.read_text(encoding="utf-8", errors="replace").splitlines()
    entries: list[ManualCommand] = []
    section = "其他"
    subsection = ""
    names: list[str] = []
    fields: dict[str, str] = {}
    heading_line = 0

    def flush() -> None:
        nonlocal names, fields, heading_line
        for name in names:
            entries.append(
                ManualCommand(
                    name=name,
                    description=_clean_markdown(fields.get("功能", "")),
                    usage=_clean_markdown(fields.get("用法", "")),
                    section=section,
                    subsection=subsection,
                    source=_clean_markdown(
                        fields.get("文件", fields.get("源文件", ""))
                    ),
                    notes=_clean_markdown(fields.get("说明", "")),
                    line=heading_line,
                )
            )
        names = []
        fields = {}
        heading_line = 0

    for line_number, raw in enumerate(lines, start=1):
        if raw.startswith("### "):
            flush()
            names = re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\(\)", raw)
            heading_line = line_number
            continue
        if raw.startswith("## "):
            flush()
            subsection = _clean_markdown(raw[3:])
            continue
        if raw.startswith("# "):
            flush()
            section = _clean_markdown(raw[2:])
            subsection = ""
            continue
        if names:
            match = re.match(r"^\s*-\s*\*\*([^*]+)\*\*:\s*(.*)$", raw)
            if match:
                fields[match.group(1).strip()] = match.group(2).strip()
    flush()
    return entries


def _manual_commands() -> list[ManualCommand]:
    """Return one best-documented entry per function name."""
    selected: dict[str, ManualCommand] = {}
    for entry in _parse_manual():
        old = selected.get(entry.name)
        score = bool(entry.description) + bool(entry.usage) + bool(entry.source)
        old_score = (
            bool(old.description) + bool(old.usage) + bool(old.source) if old else -1
        )
        if old is None or score > old_score:
            selected[entry.name] = entry
    return sorted(selected.values(), key=lambda item: (_section_key(item.section), item.name))


def _section_key(section: str) -> tuple[int, str]:
    match = re.match(r"(\d+)", section)
    return (int(match.group(1)) if match else 10_000, section)


def _first_doc_line(doc: str | None) -> str:
    if not doc:
        return ""
    for line in doc.splitlines():
        line = line.strip().strip("=—-")
        if (
            line
            and not re.fullmatch(r"[A-Za-z0-9_.-]+\.(?:py|sh)", line)
            and not line.lower().startswith(("usage", "用法"))
        ):
            return line
    return ""


def _python_description(text: str) -> str:
    try:
        # Old scientific scripts sometimes contain non-raw regex strings.
        # Their SyntaxWarning must not leak into a read-only catalogue query.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(text)
    except SyntaxError:
        return ""

    description = _first_doc_line(ast.get_docstring(tree, clean=True))
    if description:
        return description

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function_name = ""
        if isinstance(node.func, ast.Attribute):
            function_name = node.func.attr
        elif isinstance(node.func, ast.Name):
            function_name = node.func.id
        if function_name != "ArgumentParser":
            continue
        for keyword in node.keywords:
            if keyword.arg == "description" and isinstance(keyword.value, ast.Constant):
                if isinstance(keyword.value.value, str):
                    return _first_doc_line(keyword.value.value)
    return ""


def _comment_description(text: str) -> str:
    """Extract an old-style natural-language header comment."""
    skipped = re.compile(
        r"^(?:!|/?usr/bin|[-=#>*]+$|[-=#>*]{3,}|.*coding[:=]|from\s+rebreath$|"
        r"(?:usage|用法|使用方式|依赖|author|date|version)\s*[:：]?)",
        re.IGNORECASE,
    )
    for raw in text.splitlines()[:140]:
        stripped = raw.strip()
        if not stripped.startswith("#") or stripped.startswith("#!"):
            continue
        candidate = stripped.lstrip("#").strip()
        if len(candidate) < 6 or skipped.match(candidate):
            continue
        if re.search(r"[\u4e00-\u9fff]", candidate) or len(candidate.split()) >= 4:
            return _clean_markdown(candidate)
    return ""


def _shell_description(text: str) -> str:
    preferred_patterns = (
        r"^#\s*(?:Description|功能|用途)\s*[:：]\s*(.+)$",
        r"^#\s*(本脚本.+)$",
    )
    for pattern in preferred_patterns:
        for line in text.splitlines()[:120]:
            match = re.match(pattern, line.strip(), re.IGNORECASE)
            if match:
                return _clean_markdown(match.group(1))
    return ""


@lru_cache(maxsize=1)
def _manual_script_descriptions() -> dict[str, str]:
    descriptions: dict[str, str] = {}
    for entry in _parse_manual():
        if entry.description:
            descriptions.setdefault(entry.name.casefold(), entry.description)
        references = " ".join((entry.source, entry.notes, entry.usage))
        for filename in re.findall(r"([A-Za-z0-9_.-]+\.(?:py|sh))", references):
            descriptions.setdefault(Path(filename).stem.casefold(), entry.description)
    return descriptions


def _description_from_filename(stem: str, suffix: str) -> str:
    normalized = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", stem)
    normalized = normalized.replace("_", " ").replace("-", " ")
    words = normalized.casefold()
    domains = []
    domain_tokens = (
        ("phonon", "声子谱"),
        ("elastic", "弹性模量"),
        ("nep", "NEP"),
        ("xrd", "XRD"),
        ("rdf", "RDF"),
        ("hnemd", "HNEMD"),
        ("outcar", "OUTCAR"),
        ("poscar", "POSCAR"),
        ("xyz", "XYZ"),
        ("lmp", "LAMMPS"),
        ("bib", "BibTeX 文献"),
        ("ppt", "PPT"),
    )
    for token, label in domain_tokens:
        if token in words and label not in domains:
            domains.append(label)
    subject = "、".join(domains) or normalized

    actions = (
        (("compare",), "比较"),
        (("plot", "hplt"), "绘制"),
        (("analy", "diagnosis"), "分析"),
        (("convert", "trans", "to"), "转换"),
        (("dedup",), "去重"),
        (("sort",), "排序"),
        (("modify", "fix"), "修改"),
        (("perturb",), "生成微扰构型"),
        (("train",), "处理训练数据"),
        (("run", "start", "submit", "sbatch"), "运行或提交"),
        (("compute", "calorine"), "计算"),
        (("exhibit", "visual", "render"), "可视化"),
    )
    action = next(
        (label for tokens, label in actions if any(token in words for token in tokens)),
        "处理",
    )
    return f"{action}{subject}的 {suffix[1:].upper()} 工具脚本"


def _script_description(path: Path) -> str:
    known = {
        "run_cp2k_linux": "在本地 Linux 上按真实物理核并行运行 CP2K",
        "free_run_mulwork": "按可用计算资源调度多个任务",
    }
    text = path.read_text(encoding="utf-8", errors="replace")
    manual_description = _manual_script_descriptions().get(path.stem.casefold(), "")
    if path.suffix == ".py":
        structured_description = _python_description(text)
    else:
        structured_description = _shell_description(text)
    return (
        manual_description
        or structured_description
        or _comment_description(text)
        or known.get(path.stem)
        or _description_from_filename(path.stem, path.suffix)
    )


def _discover_scripts() -> list[ScriptCommand]:
    if not MIO_HOME.is_dir():
        return []

    paths: set[Path] = set()
    for root_name in SCRIPT_ROOTS:
        root = MIO_HOME / root_name
        if root.is_dir():
            paths.update(root.rglob("*.py"))
            paths.update(root.rglob("*.sh"))
    for suffix in ("*.py", "*.sh"):
        paths.update(
            path
            for path in MIO_HOME.glob(suffix)
            if path.name not in ROOT_SCRIPT_SKIP
        )

    scripts: list[ScriptCommand] = []
    for path in sorted(paths):
        relative = path.relative_to(MIO_HOME)
        if any(part.startswith(".") or part in SCRIPT_EXCLUDED_PARTS for part in relative.parts):
            continue
        canonical = relative.with_suffix("").as_posix()
        scripts.append(
            ScriptCommand(
                name=path.stem,
                canonical=canonical,
                path=path,
                description=_script_description(path),
                kind="Python" if path.suffix == ".py" else "Shell",
            )
        )
    return scripts


def _matches(query: str, values: Iterable[str]) -> bool:
    needle = query.casefold()
    return any(needle in value.casefold() for value in values if value)


def _display_width(value: str) -> int:
    return sum(2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1 for char in value)


def _fit(value: str, width: int) -> str:
    if _display_width(value) <= width:
        return value
    result = ""
    used = 0
    for char in value:
        char_width = 2 if unicodedata.east_asian_width(char) in {"W", "F"} else 1
        if used + char_width > max(1, width - 1):
            break
        result += char
        used += char_width
    return result + "…"


def _pad(value: str, width: int) -> str:
    return value + " " * max(0, width - _display_width(value))


def _print_rows(rows: list[tuple[str, str]], indent: str = "    ") -> None:
    if not rows:
        return
    terminal_width = shutil.get_terminal_size((110, 24)).columns
    name_width = min(42, max(_display_width(name) for name, _ in rows))
    description_width = max(24, terminal_width - len(indent) - name_width - 3)
    for name, description in rows:
        shown_name = _fit(name, name_width)
        shown_description = _fit(description or "暂无简述", description_width)
        print(f"{indent}{_pad(shown_name, name_width)}  {shown_description}")


def _list_manual(query: str = "") -> int:
    commands = [
        item
        for item in _manual_commands()
        if not query
        or _matches(
            query,
            (
                item.name,
                item.description,
                item.usage,
                item.section,
                item.subsection,
                item.notes,
            ),
        )
    ]
    if not commands:
        print(f"没有找到与“{query}”匹配的公共命令。")
        return 1

    print(f"MioFlow v{_version()} — 公共命令（来自函数手册，共 {len(commands)} 项）")
    current_section = None
    for item in commands:
        if item.section != current_section:
            current_section = item.section
            print(f"\n  [{current_section}]")
        _print_rows([(item.name, item.description)])
    print("\n提示: mio list <关键词> | mio help <命令> | mio scripts [关键词]")
    return 0


def _list_scripts(query: str = "") -> int:
    scripts = [
        item
        for item in _discover_scripts()
        if not query
        or _matches(query, (item.name, item.canonical, item.description, item.kind))
    ]
    if not scripts:
        print(f"没有找到与“{query}”匹配的脚本。")
        return 1

    print(f"MioFlow v{_version()} — 独立脚本（共 {len(scripts)} 项）")
    groups: dict[str, list[ScriptCommand]] = {}
    for item in scripts:
        group = item.canonical.split("/", 1)[0] if "/" in item.canonical else "root"
        groups.setdefault(group, []).append(item)
    for group, items in sorted(groups.items()):
        print(f"\n  [{group}/]")
        _print_rows([(item.canonical, item.description) for item in items])
    print("\n提示: 先用 mio help <脚本> 查看说明；用 mio run <脚本> [参数] 执行。")
    return 0


def _search(query: str, manual_only: bool = False) -> int:
    manual_results = [
        item
        for item in _manual_commands()
        if _matches(
            query,
            (
                item.name,
                item.description,
                item.usage,
                item.section,
                item.subsection,
                item.source,
                item.notes,
            ),
        )
    ]
    script_results = [] if manual_only else [
        item
        for item in _discover_scripts()
        if _matches(query, (item.name, item.canonical, item.description, item.kind))
    ]
    if not manual_results and not script_results:
        print(f"没有找到与“{query}”匹配的命令或脚本。")
        return 1

    print(f"搜索“{query}”的结果：")
    if manual_results:
        print("\n  [公共命令]")
        _print_rows(
            [(f"[函数] {item.name}", item.description) for item in manual_results]
        )
    if script_results:
        print("\n  [独立脚本]")
        _print_rows(
            [(f"[脚本] {item.canonical}", item.description) for item in script_results]
        )
    print("\n使用 mio help <名称> 查看详细用法。")
    return 0


def _resolve_scripts(command: str) -> list[ScriptCommand]:
    normalized = command.replace("\\", "/")
    normalized = re.sub(r"\.(?:py|sh)$", "", normalized)
    scripts = _discover_scripts()
    exact = [item for item in scripts if item.canonical == normalized]
    if exact:
        return exact
    return [item for item in scripts if item.name == Path(normalized).name]


def _manual_exact(command: str) -> list[ManualCommand]:
    return [item for item in _parse_manual() if item.name == command]


def _print_manual_detail(entries: list[ManualCommand]) -> None:
    primary = max(
        entries,
        key=lambda item: bool(item.description) + bool(item.usage) + bool(item.source),
    )
    print(primary.name)
    print("=" * _display_width(primary.name))
    print("类型: Shell 函数（由 mio-env-function 加载）")
    print(f"功能: {primary.description or '暂无简述'}")
    print(f"用法: {primary.usage or primary.name}")
    print(f"分类: {primary.section}" + (f" / {primary.subsection}" if primary.subsection else ""))
    if primary.source:
        print(f"来源: {primary.source}")
    if primary.notes:
        print(f"说明: {primary.notes}")
    print(f"手册: {_manual_path()}:{primary.line}")
    print("\n运行方式:")
    print("  source ~/.mio/mio-env-function   # 新终端通常已自动加载")
    print(f"  {primary.usage or primary.name}")
    if len(entries) > 1:
        locations = ", ".join(str(item.line) for item in entries)
        print(f"\n该命令在手册中出现多次，相关行: {locations}")


def _print_script_detail(script: ScriptCommand) -> None:
    print(script.canonical)
    print("=" * _display_width(script.canonical))
    print(f"类型: 独立 {script.kind} 脚本")
    print(f"功能: {script.description}")
    print(f"路径: {script.path}")
    print("\n安全查看后再运行:")
    print(f"  mio run {script.canonical} [参数...]  ")
    print("\n注意: 独立脚本可能依赖当前目录中的输入文件、外部软件或计算资源。")


def _show_help(command: str) -> int:
    command = re.sub(r"\(\)$", "", command)
    manual_entries = _manual_exact(command)
    script_entries = _resolve_scripts(command)

    if manual_entries:
        _print_manual_detail(manual_entries)
    if manual_entries and script_entries:
        print("\n--- 同名脚本 ---\n")
    if len(script_entries) == 1:
        _print_script_detail(script_entries[0])
    elif len(script_entries) > 1:
        print(f"脚本名“{command}”不唯一，请使用完整路径：")
        _print_rows([(item.canonical, item.description) for item in script_entries])
        return 2
    if manual_entries or script_entries:
        return 0

    print(f"没有精确找到“{command}”；以下是相关结果：\n")
    return _search(command)


def _run_script(command: str, args: list[str]) -> int:
    matches = _resolve_scripts(command)
    if not matches:
        print(f"找不到独立脚本“{command}”。请用 mio search {command} 查找。", file=sys.stderr)
        return 1
    if len(matches) > 1:
        print(f"脚本名“{command}”不唯一，请使用以下完整路径之一：", file=sys.stderr)
        for item in matches:
            print(f"  {item.canonical}", file=sys.stderr)
        return 2

    script = matches[0]
    executable = sys.executable if script.kind == "Python" else "bash"
    argv = [executable, str(script.path), *args]
    try:
        os.execvp(argv[0], argv)
    except FileNotFoundError:
        print(f"找不到解释器“{argv[0]}”，无法执行 {script.path}", file=sys.stderr)
        return 1


def _print_main_help() -> None:
    print(
        textwrap.dedent(
            """\
            MioFlow — 澪の工具箱 ♡

            用法:
              mio list [关键词]              列出手册中的公共命令及简述
              mio scripts [关键词]           列出独立 Python/Shell 脚本
              mio search <关键词>            搜索名称、功能、用法、分类和脚本
              mio help <命令或脚本>          查看详细说明与使用方法
              mio manual [关键词]            查询函数参考手册
              mio run <脚本> [参数...]       明确执行一个独立脚本

            兼容选项:
              mio --list, -l [关键词]        等同于 mio list
              mio --help, -h [命令]          显示总帮助或命令帮助
              mio <脚本> [参数...]           兼容旧版的脚本执行方式

            示例:
              mio list cp2k
              mio search 声子谱
              mio help cp2kstart
              mio scripts vasp
              mio help auto/auto_vasp_nep1/Ctrl_auto_vasp_to_nep1
            """
        )
    )


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        _print_main_help()
        return 0

    command = args.pop(0)
    if command in {"--help", "-h"}:
        if args:
            return _show_help(args[0])
        _print_main_help()
        return 0
    if command in {"list", "--list", "-l"}:
        show_all = "--all" in args
        query = next((arg for arg in args if arg != "--all"), "")
        status = _list_manual(query)
        if show_all:
            print("\n" + "-" * 72 + "\n")
            script_status = _list_scripts(query)
            return 0 if status == 0 or script_status == 0 else 1
        return status
    if command in {"scripts", "script"}:
        return _list_scripts(args[0] if args else "")
    if command in {"search", "find", "--search", "--find", "-s"}:
        if not args:
            print("用法: mio search <关键词>", file=sys.stderr)
            return 2
        return _search(" ".join(args))
    if command in {"help", "show"}:
        if not args:
            print("用法: mio help <命令或脚本>", file=sys.stderr)
            return 2
        return _show_help(args[0])
    if command == "manual":
        if args:
            return _search(" ".join(args), manual_only=True)
        print(_manual_path())
        print("使用 mio manual <关键词> 查询手册。")
        return 0
    if command == "run":
        if not args:
            print("用法: mio run <脚本> [参数...]", file=sys.stderr)
            return 2
        return _run_script(args[0], args[1:])

    if args == ["--help"] or args == ["-h"]:
        return _show_help(command)

    scripts = _resolve_scripts(command)
    if scripts:
        return _run_script(command, args)

    if _manual_exact(re.sub(r"\(\)$", "", command)):
        print(f"“{command}”是 Shell 函数，不是独立脚本。")
        print(f"请在已加载 MioFlow 的终端中直接运行；先执行 mio help {command} 查看用法。")
        return 2

    print(f"找不到“{command}”。试试: mio search {command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
