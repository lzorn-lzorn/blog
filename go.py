#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hexo 博客自动部署脚本（跨平台：Windows / macOS / Linux）

流程：Hexo 清理 -> 生成 -> 部署 -> 提交源码到 Git -> 推送

跨平台要点
----------
1. 所有外部命令都以「参数列表 + shell=False」启动, 彻底绕开 shell 的引号解析。
   提交信息里的空格、中文、冒号、& | > 等字符不再会被 cmd.exe 或 sh 曲解。
   （旧版本在 Windows 上用 shlex.join 拼出 POSIX 单引号, 而 cmd.exe 不把单引号
     当引号, '2026-10-09 00:52:49' 被拆成两个参数, git 于是报
     error: pathspec '00:52:49'' did not match any file(s) known to git。）
2. Windows 上 npx 实际是 npx.cmd, 先用 shutil.which 解析出真实路径再启动。
3. 万一某些 Windows 环境无法直接启动 .cmd/.bat, 才退回 shell；退回时使用
   subprocess.list2cmdline（MSVCRT 双引号风格）并再套一层引号让 cmd.exe 的
   引号剥离规则得到正确结果, 绝不使用 POSIX 的 shlex.join。
4. 子进程输出先按 UTF-8、再按系统 ANSI 代码页解码, 
   中文 Windows 上 git/node 的本地化（GBK）提示不会变成乱码。
5. core.autocrlf 只在 Windows 上设置, 避免污染 macOS/Linux 的工作区。
"""

from __future__ import annotations

import argparse
import locale
import os
import platform
import shlex
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import NamedTuple, Sequence

IS_WINDOWS = os.name == "nt"

# Windows 上隐藏子进程控制台窗口, 避免运行时黑框闪烁
_CREATE_NO_WINDOW = 0x08000000 if IS_WINDOWS else 0

HEXO_CMD = ["npx", "--no-install", "hexo"]
BLOG_URL = "https://lzorn-lzorn.github.io"
REPO_URL = "https://github.com/lzorn-lzorn/blog"


# ---------------------------------------------------------------------------
# 输出（中文 / emoji 在旧控制台上也不会抛 UnicodeEncodeError）
# ---------------------------------------------------------------------------
def setup_console() -> None:
    """把标准输出与标准错误切到 UTF-8, 保证中文和 emoji 都能正常显示。"""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def _write(text: str) -> None:
    try:
        sys.stdout.write(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        sys.stdout.write(text.encode(encoding, "replace").decode(encoding, "replace"))
    sys.stdout.flush()


def echo(text: str = "") -> None:
    """打印一行文本, 编码不兼容时降级为可显示字符而不是直接报错。"""
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        print(text.encode(encoding, "replace").decode(encoding, "replace"))


def banner(title: str) -> None:
    echo("\n" + "=" * 60)
    echo(title)
    echo("=" * 60)


# ---------------------------------------------------------------------------
# 跨平台命令执行层
# ---------------------------------------------------------------------------
def _preferred_encoding() -> str:
    """系统默认编码：Windows 中文环境是 cp936(GBK), POSIX 上通常是 UTF-8。"""
    try:
        return locale.getpreferredencoding(False) or "utf-8"
    except Exception:  # pragma: no cover - 极端环境兜底
        return "utf-8"


def decode_output(data: bytes | None) -> str:
    """UTF-8 优先、系统代码页兜底地解码子进程输出。"""
    if not data:
        return ""
    for encoding in ("utf-8", _preferred_encoding()):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def executable_path(name: str) -> str | None:
    """跨平台查找可执行文件。

    shutil.which 在 Windows 上会按 PATHEXT 逐项尝试, 
    因此 'npx' 能解析成 'C:\\Program Files\\nodejs\\npx.cmd', 
    'git' 解析成 git.exe；POSIX 上解析成 /usr/bin/git 之类。
    """
    return shutil.which(name)


def build_argv(command: Sequence[str]) -> list[str]:
    """把「逻辑命令」转成真实参数列表：解析可执行文件并做类型校验。"""
    if isinstance(command, (str, bytes)):
        raise TypeError(
            "命令必须以参数列表给出, 例如 ['git', 'commit', '-m', message]；"
            "脚本不接受字符串命令, 以免重新引入 shell 引号问题"
        )
    argv = [os.fspath(item) for item in command]
    if not argv:
        raise ValueError("命令不能为空")
    return [executable_path(argv[0]) or argv[0], *argv[1:]]


def format_argv(argv: Sequence[str]) -> str:
    """仅用于打印：按当前平台的 shell 规则还原成可读命令行。"""
    if IS_WINDOWS:
        return subprocess.list2cmdline(list(argv))
    return shlex.join(list(argv))


def _popen(argv: Sequence[str], *, merge_stderr: bool) -> subprocess.Popen:
    """启动子进程。

    首选 shell=False + 参数列表：命令行不做任何转义, 各平台行为完全一致。
    仅当 Windows 上直接启动失败（个别环境的 .cmd/.bat 包装脚本无法直接
    CreateProcess）时, 才退回 shell=True, 并使用 cmd.exe 认识的双引号规则。
    """
    options = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT if merge_stderr else subprocess.PIPE,
        "creationflags": _CREATE_NO_WINDOW,
    }
    try:
        return subprocess.Popen(list(argv), **options)
    except OSError as exc:
        if not IS_WINDOWS:
            raise
        echo(f"⚠️  无法直接启动 {argv[0]}（{exc}）, 改用 cmd.exe 方式重试")
        # list2cmdline 产出 MSVCRT 风格双引号；外层再套一对引号, 
        # cmd /c 会剥掉首尾引号, 从而留下正确的内部命令行。
        cmdline = '"' + subprocess.list2cmdline(list(argv)) + '"'
        return subprocess.Popen(cmdline, shell=True, **options)


class CommandResult(NamedTuple):
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def capture(command: Sequence[str], *, merge_stderr: bool = False) -> CommandResult:
    """执行命令并捕获输出（不打印到终端）。"""
    argv = build_argv(command)
    process = _popen(argv, merge_stderr=merge_stderr)
    out, err = process.communicate()
    return CommandResult(
        process.returncode,
        decode_output(out),
        decode_output(out if merge_stderr else err),
    )


def run_command(command: Sequence[str], description: str) -> bool:
    """执行命令并实时回显输出, 返回是否成功。"""
    argv = build_argv(command)

    banner(description)
    echo(f"$ {format_argv(argv)}")

    process: subprocess.Popen | None = None
    try:
        process = _popen(argv, merge_stderr=True)
        if process.stdout is not None:
            for raw_line in process.stdout:
                _write(decode_output(raw_line))
        process.wait()
    except KeyboardInterrupt:
        if process is not None and process.poll() is None:
            process.kill()
            process.wait()
        raise
    except OSError as exc:
        echo(f"执行出错: {exc}")
        return False

    if process.returncode == 0:
        echo(f"{description} - 成功")
        return True
    echo(f"{description} - 失败 (退出码: {process.returncode})")
    return False


class StepError(RuntimeError):
    """某个部署步骤失败。"""


def run_or_fail(command: Sequence[str], description: str) -> None:
    if not run_command(command, description):
        raise StepError(f"{description} 失败")


# ---------------------------------------------------------------------------
# Git 相关
# ---------------------------------------------------------------------------
def configure_line_endings() -> None:
    """只在 Windows 上设置 core.autocrlf, 避免改写 macOS/Linux 工作区。"""
    if not IS_WINDOWS:
        echo("\n📌 非 Windows 平台, 保留现有的 core.autocrlf 设置")
        return
    if not run_command(
        ["git", "config", "core.autocrlf", "true"],
        "设置 Git 换行符策略 (core.autocrlf=true)",
    ):
        echo("⚠️  设置 core.autocrlf 失败, 继续执行（不影响提交流程）")


def changed_files() -> list[str]:
    """返回工作区/暂存区的改动列表；为空表示工作区干净。"""
    result = capture(["git", "-c", "core.quotepath=false", "status", "--porcelain"])
    if not result.ok:
        raise StepError(f"检查 Git 状态失败: {result.stderr.strip() or result.stdout.strip()}")

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        echo("\n📌 Git 工作区干净, 没有需要提交的改动")
        return lines

    echo("\n📋 检测到以下文件改动:")
    for line in lines:
        echo(f"   {line}")
    return lines


def has_unpushed_commits() -> bool:
    """本地是否存在已提交但尚未推送的 commit。"""
    upstream = capture(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"])
    if not upstream.ok:
        return False  # 没有上游分支, 视为无未推送提交

    ahead = capture(["git", "rev-list", "--count", "@{u}..HEAD"])
    if not ahead.ok:
        return False
    try:
        return int(ahead.stdout.strip()) > 0
    except ValueError:
        return False


def ensure_git_identity() -> None:
    """提交前确认 user.name / user.email 已配置, 否则给出可操作的提示。"""
    for key, example in (("user.name", "你的名字"), ("user.email", "you@example.com")):
        result = capture(["git", "config", key])
        if not result.ok or not result.stdout.strip():
            raise StepError(
                f'Git 未配置 {key}, 请先执行: git config --global {key} "{example}"'
            )


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hexo 博客自动部署脚本（跨平台）")
    parser.add_argument(
        "-m", "--message",
        type=str,
        default=None,
        help="Git 提交信息（默认使用当前时间字符串）",
    )
    return parser.parse_args()


def verify_generated_site(workdir: Path) -> None:
    """部署前自检: public/ 必须真的生成了 HTML, 否则中止。

    主题目录缺失 (themes/<theme> 是本地软链接/拷贝, 并不在 git 仓库里) 或
    node_modules 不完整 (例如 hexo-renderer-marked 缺失) 时, hexo generate
    只会把 source/ 里的静态文件原样拷进 public/, 一个 HTML 都不产出,
    但退出码仍然是 0。此时 hexo deploy 会把空的 public/ 强推覆盖线上,
    直接导致整站 404。所以这里宁可不部署。
    """
    public_dir = workdir / "public"
    index_file = public_dir / "index.html"
    html_files = list(public_dir.rglob("*.html")) if public_dir.is_dir() else []

    if index_file.is_file():
        echo(f"\n🔍 自检通过: public/index.html 已生成 (HTML 文件共 {len(html_files)} 个)")
        return

    themes_dir = workdir / "themes"
    themes = []
    if themes_dir.is_dir():
        themes = sorted(p.name for p in themes_dir.iterdir() if p.is_dir())

    raise StepError(
        "public/index.html 不存在, 已中止部署以防线上 404！\n"
        f"   public 目录: {public_dir}\n"
        f"   生成的 HTML 文件数: {len(html_files)}\n"
        f"   themes/ 下的主题目录: {', '.join(themes) if themes else '（空）'}\n"
        "   常见原因: themes/<主题名> 缺失（它是本地软链接或拷贝, 不在 git 仓库中,"
        "例如 themes\\kira 应指向 node_modules\\hexo-theme-kira）；"
        "或 node_modules 不完整（package-lock 里的 hexo-renderer-marked 等包没装上）。\n"
        "   建议: 先执行 npm ci, 再确认主题目录存在, 然后重新运行。"
    )


def deploy(message: str | None) -> None:
    workdir = Path(__file__).resolve().parent
    os.chdir(workdir)

    echo("\n" + "🌟" * 30)
    echo("     Hexo 博客自动部署脚本")
    echo("🌟" * 30)
    echo(f"\n 工作目录: {workdir}")
    echo(
        f" 运行环境: {platform.system()} {platform.release()} "
        f"| Python {platform.python_version()}"
    )

    missing = [name for name in ("git", "node", "npx") if executable_path(name) is None]
    if missing:
        raise StepError("未找到以下命令, 请先安装并确认它们在 PATH 中: " + ", ".join(missing))

    # 步骤 1 ~ 3: Hexo 清理 / 生成 / 自检 / 部署
    run_or_fail(HEXO_CMD + ["clean"], "清理 Hexo 缓存")
    run_or_fail(HEXO_CMD + ["generate"], "生成静态文件")
    verify_generated_site(workdir)
    run_or_fail(HEXO_CMD + ["deploy"], "部署到 GitHub Pages")

    echo("\n" + "=" * 60)
    echo("✅ Hexo 部署完成！")
    echo("=" * 60)

    configure_line_endings()

    # 步骤 4: 工作区是否有改动
    changes = changed_files()

    # 步骤 5: 是否有未推送的提交
    unpushed = has_unpushed_commits()

    if not changes and not unpushed:
        echo("\n 所有操作完成！")
        echo(f"博客地址: {BLOG_URL}")
        return

    if changes:
        commit_message = (message or "").strip() or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ensure_git_identity()
        run_or_fail(["git", "add", "-A"], "添加所有改动到暂存区")
        # 提交信息作为独立参数传递：空格、冒号、中文都不会再被 shell 拆开
        run_or_fail(["git", "commit", "-m", commit_message], f"提交改动: {commit_message}")
    else:
        echo("\n📌 工作区无改动, 但存在未推送的提交, 跳过 commit, 直接 push")

    run_or_fail(["git", "push"], "推送到远程仓库")

    echo("\n" + "=" * 60)
    echo("✨ 所有操作完成！")
    echo("=" * 60)
    echo(f"博客地址: {BLOG_URL}")
    echo(f"源代码: {REPO_URL}")
    echo("=" * 60 + "\n")


def main() -> int:
    setup_console()
    args = parse_args()

    try:
        deploy(args.message)
    except StepError as exc:
        # 部署流程是幂等的：clean + generate + deploy 每次都是全量重新生成并覆盖推送, 
        # git add/commit/push 也只处理尚未提交的改动, 因此失败后无需回滚。
        echo(f"\n❌ {exc}")
        echo("   修复问题后重新运行 python go.py 即可覆盖之前的结果。")
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        echo("\n\n⚠️  用户中断操作")
        sys.exit(130)
    except Exception as exc:  # 兜底：不向用户抛原始 traceback
        echo(f"\n❌ 发生错误: {exc}")
        sys.exit(1)
