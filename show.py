#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hexo 本地快速预览脚本

功能：
  1. 从 4000 端口开始寻找一个空闲端口；
  2. 在该端口启动 hexo server；
  3. 用默认浏览器打开博客；
  4. 通过页面心跳检测页面是否已关闭, 关闭后自动结束 hexo 服务、释放端口。
"""

import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser

HEXO_CMD = ['npx', '--no-install', 'hexo']
START_PORT = 4000
HEARTBEAT_PATH = '__hb__'
HEARTBEAT_TIMEOUT = 5  # 超过 20 秒无心跳, 认为页面已关闭


def find_free_port(start, limit=200):
    """从 start 开始寻找一个未被占用的端口"""
    for port in range(start, start + limit):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('127.0.0.1', port)) != 0:
                return port
    raise RuntimeError(f"在 {start}~{start + limit - 1} 之间找不到空闲端口")


def wait_server_ready(port, timeout=30):
    """轮询等待 hexo server 就绪"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    port = find_free_port(START_PORT)
    print(f"🌐 端口 {port} 空闲, 正在启动博客...")

    # 设置环境变量, 触发心跳脚本注入（见 scripts/heartbeat.js）
    env = os.environ.copy()
    env['HEXO_PREVIEW'] = '1'

    # --log 让 hexo 打印请求日志, 用于检测心跳
    proc = subprocess.Popen(
        HEXO_CMD + ['server', '-p', str(port), '--log'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding='utf-8',
        errors='replace',
        bufsize=1,
        env=env,
    )

    if not wait_server_ready(port):
        print("❌ hexo server 启动失败")
        proc.terminate()
        sys.exit(1)

    url = f'http://localhost:{port}/'
    print(f"✅ 博客已启动：{url}")
    webbrowser.open(url)
    print(f"💡 用默认浏览器打开中... 关闭页面约 {HEARTBEAT_TIMEOUT}s 后自动释放端口（Ctrl+C 立即退出）")

    last_heartbeat = time.time()
    stop_flag = threading.Event()

    def read_output():
        nonlocal last_heartbeat
        for line in proc.stdout:
            if HEARTBEAT_PATH in line:
                last_heartbeat = time.time()  # 收到心跳, 不打印（避免刷屏）
            else:
                print(line, end='')
        stop_flag.set()  # hexo 进程输出结束（已退出）

    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()

    try:
        while not stop_flag.is_set():
            time.sleep(1)
            if time.time() - last_heartbeat > HEARTBEAT_TIMEOUT:
                print(f"\n🔚 检测到页面已关闭（超过 {HEARTBEAT_TIMEOUT}s 无心跳）, 结束服务...")
                break
    except KeyboardInterrupt:
        print("\n⚠️  用户中断")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("✅ hexo server 已停止, 端口已释放")


if __name__ == "__main__":
    main()
