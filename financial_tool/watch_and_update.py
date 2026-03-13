#!/usr/bin/env python3
"""
实时监控模式 - 自动检测 input/ 文件夹变化并更新 Excel
=====================================================
运行后会持续监控 input/ 文件夹，每当有新文件或文件变更时自动处理。

使用方法:
    python watch_and_update.py

按 Ctrl+C 停止监控。
"""

import time
import sys
from pathlib import Path
from process_data import INPUT_DIR, process_files, write_excel


def get_folder_state(folder):
    """获取文件夹当前状态（文件名+修改时间）。"""
    state = {}
    if folder.exists():
        for f in folder.iterdir():
            if f.is_file() and not f.name.startswith("."):
                state[f.name] = f.stat().st_mtime
    return state


def main():
    print("=" * 50)
    print("  金融数据 - 实时监控模式")
    print("=" * 50)
    print(f"\n  监控文件夹: {INPUT_DIR}")
    print("  每当有新文件放入，将自动处理并更新 Excel")
    print("  按 Ctrl+C 停止\n")

    CHECK_INTERVAL = 3  # 每 3 秒检查一次

    last_state = get_folder_state(INPUT_DIR)

    # 如果已有文件，先处理一次
    if last_state:
        print(f"  发现 {len(last_state)} 个已有文件，先处理一次...\n")
        records, count = process_files()
        write_excel(records)
        print()

    try:
        while True:
            time.sleep(CHECK_INTERVAL)
            current_state = get_folder_state(INPUT_DIR)

            if current_state != last_state:
                # 找出变化
                new_files = set(current_state.keys()) - set(last_state.keys())
                changed_files = {
                    f for f in current_state
                    if f in last_state and current_state[f] != last_state[f]
                }

                if new_files:
                    print(f"\n  检测到 {len(new_files)} 个新文件: {', '.join(new_files)}")
                if changed_files:
                    print(f"\n  检测到 {len(changed_files)} 个文件变更: {', '.join(changed_files)}")

                records, count = process_files()
                write_excel(records)
                print(f"\n  等待新文件... (Ctrl+C 退出)")

                last_state = current_state
    except KeyboardInterrupt:
        print("\n\n  已停止监控。")


if __name__ == "__main__":
    main()
