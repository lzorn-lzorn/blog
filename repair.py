#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hexo 构建修复 / 诊断脚本（跨平台：Windows / macOS / Linux）

用途：站点 404、show.py 预览空白时，一条命令把本地构建修回来。

它按顺序做四件事：
  1. 依赖自检：逐项对比 node_modules 与 package.json / package-lock.json，
     列出「缺失 / 版本不一致 / 多装」的包（本项目的典型症状：
     hexo-renderer-marked 缺失、hexo 是 8.x 而 lock 锁的是 7.3.0）。
  2. 主题自检：确认 themes/<theme> 或 node_modules/hexo-theme-<theme> 能被 Hexo 找到。
  3. npm ci：按 lock 文件重装依赖（--no-install 可跳过）。
  4. hexo clean + generate，把完整输出同时打印并写入 repair-generate.log，
     最后自检 public/index.html —— 没有 index.html 就说明构建仍然是坏的，
     这时**不要**运行 go.py 部署（go.py 现在也会自己拦住这种空站点）。

用法：
    python repair.py                 # 诊断 + npm ci + 重新生成 + 自检
    python repair.py --no-install    # 跳过 npm ci（只想看诊断和生成日志）
    python repair.py --deploy        # 自检通过后接着执行 go.py 重新部署

运行前请先关掉 show.py 的预览窗口，否则 Windows 上 npm ci 可能因文件被占用而失败。
"""

from __future__ import annotations

import argparse
import json
import locale
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

IS_WINDOWS = os.name == "nt"
_CREATE_NO_WINDOW = 0x08000000 if IS_WINDOWS else 0

HEXO_CMD = ["npx", "--no-install", "hexo"]
LOG_NAME = "repair-generate.log"


# ---------------------------------------------------------------------------
# 输出与子进程
# ---------------------------------------------------------------------------
def setup_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass


def echo(text: str = "") -> None:
    try:
        print(text)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        print(text.encode(encoding, "replace").decode(encoding, "replace"))


def decode_output(data: bytes | None) -> str:
    """UTF-8 优先、系统代码页（中文 Windows 是 GBK）兜底。"""
    if not data:
        return ""
    try:
        preferred = locale.getpreferredencoding(False) or "utf-8"
    except Exception:
        preferred = "utf-8"
    for encoding in ("utf-8", preferred):
        try:
            return data.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return data.decode("utf-8", errors="replace")


def executable_path(name: str) -> str | None:
    return shutil.which(name)


def run(command, description: str, log=None) -> tuple[int, str]:
    """执行命令，实时回显输出（同时可选写入 log 文件），返回 (退出码, 输出)。"""
    argv = [os.fspath(item) for item in command]
    argv[0] = executable_path(argv[0]) or argv[0]

    if IS_WINDOWS:
        printable = subprocess.list2cmdline(argv)
    else:
        import shlex
        printable = shlex.join(argv)

    echo("\n" + "=" * 60)
    echo(description)
    echo("=" * 60)
    echo(f"$ {printable}")

    process = subprocess.Popen(
        argv,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        creationflags=_CREATE_NO_WINDOW,
    )

    chunks: list[str] = []
    if process.stdout is not None:
        for raw_line in process.stdout:
            text = decode_output(raw_line)
            chunks.append(text)
            try:
                sys.stdout.write(text)
                sys.stdout.flush()
            except UnicodeEncodeError:
                pass
            if log is not None:
                log.write(text)

    process.wait()
    echo(f"--- {description} 退出码: {process.returncode} ---")
    return process.returncode, "".join(chunks)


# ---------------------------------------------------------------------------
# 诊断
# ---------------------------------------------------------------------------
def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def read_theme_name(workdir: Path) -> str | None:
    config = workdir / "_config.yml"
    if not config.is_file():
        return None
    try:
        text = config.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    match = re.search(r"^\s*theme:\s*['\"]?([\w.-]+)", text, re.MULTILINE)
    return match.group(1) if match else None


def diagnose(workdir: Path) -> list[str]:
    """返回发现的问题列表（同时打印明细）。"""
    problems: list[str] = []

    pkg = load_json(workdir / "package.json") or {}
    declared: dict[str, str] = pkg.get("dependencies", {}) or {}
    lock = load_json(workdir / "package-lock.json") or {}
    locked: dict[str, dict] = lock.get("packages", {}) or {}

    echo("\n" + "=" * 60)
    echo("① 依赖自检: node_modules 对比 package-lock.json")
    echo("=" * 60)

    node_modules = workdir / "node_modules"
    for name in sorted(declared):
        spec = declared[name]
        expected = (locked.get(f"node_modules/{name}") or {}).get("version")
        installed_pkg = node_modules / name / "package.json"
        installed = None
        if installed_pkg.is_file():
            installed = (load_json(installed_pkg) or {}).get("version", "?")

        if installed is None:
            problems.append(f"缺少依赖 {name}（要求 {spec}，lock 记录 {expected}）")
            echo(f"  [缺失]  {name:<28} 要求 {spec:<10} lock {expected}   实际 无")
        elif expected and installed != expected:
            problems.append(f"{name} 版本不一致：实际 {installed}，lock {expected}")
            echo(f"  [版本]  {name:<28} 要求 {spec:<10} lock {expected}   实际 {installed}")
        else:
            echo(f"  [ OK ]  {name:<28} 实际 {installed}")

    if node_modules.is_dir():
        extra = sorted(
            p.name
            for p in node_modules.glob("hexo-*")
            if p.is_dir() and p.name not in declared
        )
        if extra:
            problems.append("安装了未声明的 hexo 插件: " + ", ".join(extra))
            echo(f"\n  [多余]  未声明但已安装: {', '.join(extra)}")
            echo("          （说明 node_modules 是被另一套 package.json 装出来的）")

    echo("\n" + "=" * 60)
    echo("② 主题自检")
    echo("=" * 60)
    theme = read_theme_name(workdir)
    echo(f"  _config.yml 里的 theme = {theme!r}")
    if theme:
        local = workdir / "themes" / theme
        from_npm = workdir / "node_modules" / f"hexo-theme-{theme}"
        echo(f"  themes/{theme}: {'存在' if local.exists() else '不存在'}")
        echo(f"  node_modules/hexo-theme-{theme}: {'存在' if from_npm.is_dir() else '不存在'}")
        echo("  （Hexo 两个位置都会找：themes/<name> 不存在时回退到 node_modules/hexo-theme-<name>）")
        if not local.exists() and not from_npm.is_dir():
            problems.append(f"主题 {theme} 在 themes/ 和 node_modules/ 里都找不到")

    echo("")
    if problems:
        echo(f"⚠️  共发现 {len(problems)} 个问题:")
        for item in problems:
            echo(f"   - {item}")
    else:
        echo("✅ 依赖与主题自检没有发现问题")
    return problems


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Hexo 构建修复 / 诊断脚本")
    parser.add_argument("--no-install", action="store_true", help="跳过 npm ci，只诊断和重新生成")
    parser.add_argument("--deploy", action="store_true", help="自检通过后接着执行 go.py 部署")
    return parser.parse_args()


def main() -> int:
    setup_console()
    args = parse_args()

    workdir = Path(__file__).resolve().parent
    os.chdir(workdir)

    echo("\n" + "🔧" * 30)
    echo("     Hexo 构建修复 / 诊断")
    echo("🔧" * 30)
    echo(f"\n 工作目录: {workdir}")

    for name in ("node", "npm", "npx"):
        if executable_path(name) is None:
            echo(f"\n❌ 未找到 {name}，请先安装 Node.js 并确认它在 PATH 中")
            return 1

    diagnose(workdir)

    if args.no_install:
        echo("\n（--no-install：跳过 npm ci）")
    else:
        echo(
            "\n接下来执行 npm ci：会删除并重装 node_modules，"
            "按 package-lock.json 还原成 hexo 7.3.0 + hexo-renderer-marked 6.3.0 那一套。"
        )
        code, _ = run(["npm", "ci"], "npm ci 重装依赖")
        if code != 0:
            echo("\n❌ npm ci 失败。常见原因：还有进程占用 node_modules（比如 show.py 的预览窗口没关）；")
            echo("   或 npm 与 lock 文件版本不兼容。把上面的输出发我，我继续跟。")
            return 1

    log_path = workdir / LOG_NAME
    with log_path.open("w", encoding="utf-8", errors="replace") as log:
        log.write(f"# 工作目录: {workdir}\n")
        run(HEXO_CMD + ["clean"], "hexo clean", log=log)
        run(HEXO_CMD + ["generate"], "hexo generate", log=log)

    public_dir = workdir / "public"
    index_file = public_dir / "index.html"
    html_files = sorted(public_dir.rglob("*.html")) if public_dir.is_dir() else []

    echo("\n" + "=" * 60)
    echo("③ 生成结果自检")
    echo("=" * 60)
    echo(f"  public/index.html : {'存在 ✅' if index_file.is_file() else '不存在 ❌'}")
    echo(f"  public 下的 HTML 文件数: {len(html_files)}")
    echo(f"  完整生成日志: {log_path}")

    if not index_file.is_file():
        echo("\n❌ 本地构建仍然不产出 HTML，先不要部署（go.py 也会拦住）。")
        echo("   请对照上面 generate 的输出找这几类线索：")
        echo("     - ERROR / WARN 行：No layout、Renderer for md not found 之类")
        echo("     - hexo 版本与主题不兼容（本仓库 lock 是 hexo 7.3.0）")
        echo(f"     - scripts/*.js 里的过滤器报错（protect-math.js / noindex.js / mermaid.js 等）")
        echo(f"   把 {LOG_NAME} 的内容发我，我据此继续定位。")
        return 1

    echo("\n✅ 本地构建已恢复正常。")
    echo("   本地预览: python show.py")
    if args.deploy:
        echo("\n继续部署 ...")
        code, _ = run([sys.executable, "go.py"], "重新部署 (go.py)")
        return code

    echo("   部署上线: python go.py   （它会先自检 public/index.html 再推送）")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        echo("\n\n⚠️  用户中断操作")
        sys.exit(130)
    except Exception as exc:
        echo(f"\n❌ 发生错误: {exc}")
        sys.exit(1)
