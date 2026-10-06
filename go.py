#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hexo 博客自动部署脚本
支持 Windows, macOS, Linux
功能：清理 -> 生成 -> 部署 Hexo, 并提交源代码到 Git
"""

import argparse
import shlex
import subprocess
import sys
import os
from datetime import datetime


HEXO_CMD = ['npx', '--no-install', 'hexo']

def run_command(command, description):
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    
    try:
        if isinstance(command, str):
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding='utf-8',      
                errors='replace',      
                bufsize=1
            )
        else:
            process = subprocess.Popen(
                shlex.join(command),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding='utf-8',      
                errors='replace',      
                bufsize=1
            )
        
        for line in process.stdout:
            print(line, end='')
        
        process.wait()
        
        if process.returncode == 0:
            print(f"{description} - 成功")
            return True
        else:
            print(f"{description} - 失败 (退出码: {process.returncode})")
            return False
            
    except Exception as e:
        print(f"执行出错: {str(e)}")
        return False
    
    
def parse_args():
    """
    解析命令行参数
    
    Returns:
        argparse.Namespace: 解析后的参数
    """
    parser = argparse.ArgumentParser(description="Hexo 博客自动部署脚本")
    parser.add_argument(
        '-m', '--message',
        type=str,
        default=None,
        help='Git 提交信息（默认使用当前时间字符串）'
    )
    return parser.parse_args()


def check_command(command):
    """
    检查命令是否可用

    Args:
        command: 命令名

    Returns:
        bool: 命令是否存在
    """
    try:
        subprocess.run(
            [command, '--version'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_git_status():
    """
    检查 Git 状态, 确认是否有文件需要提交
    
    Returns:
        bool: 是否有文件需要提交
    """
    try:
        result = subprocess.run(
            ['git', 'status', '--porcelain'],
            capture_output=True,
            text=True,
            check=True
        )
        
        # 如果输出为空, 说明没有改动
        if not result.stdout.strip():
            print("\n📌 Git 工作区干净, 没有需要提交的改动")
            return False
        
        print("\n📋 检测到以下文件改动:")
        print(result.stdout)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 检查 Git 状态失败: {str(e)}")
        return False


def fail_exit(description):
    """
    部署步骤失败时退出。

    部署流程是幂等的：clean + generate + deploy 每次都是全量重新生成并覆盖推送，
    git add/commit/push 也只会提交尚未提交的改动。因此失败后无需回滚，
    修复问题后重新运行 `python3 go.py` 即可覆盖之前的结果。
    """
    print(f"\n❌ {description}")
    sys.exit(1)


def main():
    """主函数"""
    args = parse_args()
    
    print("\n" + "🌟"*30)
    print("     Hexo 博客自动部署脚本")
    print("🌟"*30)
    
    # 确保在正确的目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"\n 工作目录: {script_dir}")

    if not check_command('git'):
        print("\n❌ 未找到 git, 请先安装并确认它在 PATH 中")
        sys.exit(1)

    if not check_command('node'):
        print("\n❌ 未找到 node, 请先安装 Node.js")
        sys.exit(1)

    # 步骤 1: Hexo 清理
    if not run_command(HEXO_CMD + ['clean'], "清理 Hexo 缓存"):
        fail_exit("清理 Hexo 缓存失败")

    # 步骤 2: Hexo 生成
    if not run_command(HEXO_CMD + ['generate'], "生成静态文件"):
        fail_exit("生成静态文件失败")

    # 步骤 3: Hexo 部署
    if not run_command(HEXO_CMD + ['deploy'], "部署到 GitHub Pages"):
        fail_exit("部署到 GitHub Pages 失败")

    print("\n" + "="*60)
    print("✅ Hexo 部署完成！")
    print("="*60)

    run_command("git config core.autocrlf true", "设置 Git 换行符策略")

    # 步骤 4: 检查 Git 状态
    if not check_git_status():
        print("\n 所有操作完成！")
        print(f"博客地址: https://lzorn-lzorn.github.io")
        return

    # 步骤 5: Git 提交
    commit_message = args.message or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Git add
    if not run_command("git add .", "添加所有改动到暂存区"):
        fail_exit("Git add 失败")

    # Git commit
    commit_cmd = ['git', 'commit', '-m', commit_message]
    if not run_command(commit_cmd, f"提交改动: {commit_message}"):
        fail_exit("Git commit 失败")

    # Git push
    if not run_command("git push", "推送到远程仓库"):
        fail_exit("推送到远程仓库失败")

    # 完成
    print("\n" + "<" + "="*60 + ">")
    print("✨ 所有操作完成！")
    print("="*60)
    print(f"博客地址: https://lzorn-lzorn.github.io")
    print(f"源代码: https://github.com/lzorn-lzorn/blog")
    print("<" + "="*60 + ">" + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断操作")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误: {str(e)}")
        sys.exit(1)
