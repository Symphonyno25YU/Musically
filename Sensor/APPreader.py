#!/usr/bin/env python3
import subprocess
import time

def get_frontmost_app():
    """读取当前前台(正在使用)的 app 名字,返回一个字符串。"""
    script = 'tell application "System Events" to get name of first application process whose frontmost is true'
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("出错了,可能是还没授权'辅助功能'权限。")
        print("系统给的错误信息:", result.stderr.strip())
        return None

    return result.stdout.strip()

# ---- 每 5 秒检测一次前台 app ----
print("开始监测前台 app,切换窗口试试,按 Control+C 停止:")
while True:
    app = get_frontmost_app()
    print("当前前台:", app)
    time.sleep(5)   # 5 秒检测一次

