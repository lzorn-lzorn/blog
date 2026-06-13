#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hexo 博客自动部署脚本
支持 Windows, macOS, Linux
功能：清理 -> 生成 -> 部署 Hexo，并提交源代码到 Git
"""

import subprocess
import sys
import os
from datetime import datetime


HEXO_CMD = ['npx', '--no-install', 'hexo']


def run_command(command, description):
    """
    执行命令并实时输出结果
    
    Args:
        command: 要执行的命令（字符串或列表）
        description: 命令描述
    
    Returns:
        bool: 命令是否执行成功
    """
    print(f"\n{'='*60}")
    print(f"{description}")
    print(f"{'='*60}")
    
    try:
        # 如果是字符串，在 shell 中执行
        if isinstance(command, str):
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
        else:
            # 如果是列表，直接执行
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
        
        # 实时输出
        for line in process.stdout:
            print(line, end='')
        
        # 等待进程结束
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


def get_commit_message():
    """
    获取用户输入的提交信息，如果为空则使用默认信息
    
    Returns:
        str: 提交信息
    """
    print("\n" + "="*60)
    print("> 请输入 Git 提交信息 (直接回车使用默认信息):")
    print("="*60)
    
    try:
        message = input("提交信息: ").strip()
    except KeyboardInterrupt:
        print("\n\n⚠️  用户取消操作")
        sys.exit(0)
    
    if not message:
        # 使用默认提交信息（包含时间戳）
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"更新博客内容 - {now}"
    
    return message


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
    检查 Git 状态，确认是否有文件需要提交
    
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
        
        # 如果输出为空，说明没有改动
        if not result.stdout.strip():
            print("\n📌 Git 工作区干净，没有需要提交的改动")
            return False
        
        print("\n📋 检测到以下文件改动:")
        print(result.stdout)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 检查 Git 状态失败: {str(e)}")
        return False


def main():
    """主函数"""
    print("\n" + "🌟"*30)
    print("     Hexo 博客自动部署脚本")
    print("🌟"*30)
    
    # 确保在正确的目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    print(f"\n 工作目录: {script_dir}")

    if not check_command('git'):
        print("\n❌ 未找到 git，请先安装并确认它在 PATH 中")
        sys.exit(1)

    if not check_command('npx'):
        print("\n❌ 未找到 npx，请先安装 Node.js/npm")
        sys.exit(1)
    
    # 步骤 1: Hexo 清理 不清理(太慢)
    # if not run_command("hexo clean", "清理 Hexo 缓存"):
    #     print("\n⚠️  清理失败，是否继续？(y/n): ", end='')
    #     if input().lower() != 'y':
    #         sys.exit(1)
    
    # 步骤 2: Hexo 生成
    if not run_command(HEXO_CMD + ['generate'], "生成静态文件"):
        print("\n❌ 生成失败，部署终止")
        sys.exit(1)
    
    # 步骤 3: Hexo 部署
    if not run_command(HEXO_CMD + ['deploy'], "部署到 GitHub Pages"):
        print("\n❌ 部署失败，Git 提交终止")
        sys.exit(1)
    
    print("\n" + "="*60)
    print("✅ Hexo 部署完成！")
    print("="*60)
    
    # 步骤 4: 检查 Git 状态
    if not check_git_status():
        print("\n 所有操作完成！")
        print(f"博客地址: https://lzorn-lzorn.github.io")
        return
    
    # 步骤 5: Git 提交
    commit_message = get_commit_message()
    
    # Git add
    if not run_command("git add .", "添加所有改动到暂存区"):
        print("\n❌ Git add 失败")
        sys.exit(1)
    
    # Git commit
    commit_cmd = ['git', 'commit', '-m', commit_message]
    if not run_command(commit_cmd, f"提交改动: {commit_message}"):
        print("\n⚠️  提交失败，可能没有改动或存在冲突")
        # 不终止，继续尝试推送
    
    # Git push
    if not run_command("git push", "推送到远程仓库"):
        print("\n❌ 推送失败")
        sys.exit(1)
    
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
