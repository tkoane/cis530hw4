#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
金融数据自动提取工具
===================
将图片(截图)和文字文件中的金融数据提取到Excel表格中。

使用方法:
    python process_data.py              # 处理 input 文件夹中的所有文件
    python process_data.py --watch      # 持续监控，有新文件自动处理
"""

import os
import sys
import re
import json
import time
import hashlib
import argparse
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

try:
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

# ── 路径配置 ──────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
CONFIG_FILE = BASE_DIR / "config.json"
PROCESSED_LOG = BASE_DIR / ".processed_files.json"

# ── 默认配置 ──────────────────────────────────────────────
DEFAULT_CONFIG = {
    "company_name": "目标公司",
    "excel_filename": "financial_data.xlsx",
    "ocr_language": "chi_sim+eng",
    "keywords": [
        "营收", "收入", "利润", "净利润", "毛利", "毛利率",
        "净利率", "ROE", "ROA", "PE", "PB", "EPS",
        "市值", "股价", "涨幅", "跌幅", "成交量", "成交额",
        "revenue", "profit", "margin", "growth", "earnings",
        "总资产", "净资产", "负债", "现金流", "分红", "股息",
        "同比", "环比", "增长", "下降",
    ],
    "date_formats": [
        r"\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?",
        r"\d{4}[-/]\d{1,2}",
        r"\d{1,2}[-/]\d{1,2}[-/]\d{4}",
    ],
}


def load_config():
    """加载配置文件，如果不存在则使用默认配置"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            user_config = json.load(f)
        config = {**DEFAULT_CONFIG, **user_config}
    else:
        config = DEFAULT_CONFIG.copy()
    return config


def load_processed_log():
    """加载已处理文件记录"""
    if PROCESSED_LOG.exists():
        with open(PROCESSED_LOG, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_processed_log(log):
    """保存已处理文件记录"""
    with open(PROCESSED_LOG, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def file_hash(filepath):
    """计算文件的 MD5 用于去重"""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ── 文本提取 ──────────────────────────────────────────────

def extract_text_from_image(image_path, config):
    """从图片中提取文字 (OCR)"""
    if not HAS_PIL:
        print(f"  [警告] 未安装 Pillow，无法处理图片: {image_path}")
        return None
    if not HAS_TESSERACT:
        print(f"  [警告] 未安装 pytesseract，无法处理图片: {image_path}")
        print("  请运行: pip install pytesseract")
        print("  并安装 Tesseract-OCR: https://github.com/tesseract-ocr/tesseract")
        return None

    try:
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img, lang=config.get("ocr_language", "chi_sim+eng"))
        return text.strip()
    except Exception as e:
        print(f"  [错误] OCR处理失败 {image_path}: {e}")
        return None


def extract_text_from_file(filepath):
    """从文本文件中读取内容"""
    encodings = ["utf-8", "gbk", "gb2312", "utf-16", "latin-1"]
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read().strip()
        except (UnicodeDecodeError, UnicodeError):
            continue
    print(f"  [警告] 无法读取文件编码: {filepath}")
    return None


# ── 数据解析 ──────────────────────────────────────────────

def extract_date(text, config):
    """从文本中提取日期"""
    for pattern in config.get("date_formats", []):
        match = re.search(pattern, text)
        if match:
            return match.group()
    return datetime.now().strftime("%Y-%m-%d")


def extract_numbers(text):
    """提取文本中的数字（含百分比、金额等）"""
    patterns = [
        (r"([\d,]+\.?\d*)\s*[万亿]?[元美]?[元金]?[美]?[元]?", "number"),
        (r"([-+]?\d+\.?\d*)\s*%", "percentage"),
    ]
    numbers = []
    for pattern, kind in patterns:
        for match in re.finditer(pattern, text):
            numbers.append({"value": match.group(), "type": kind, "pos": match.start()})
    return numbers


def parse_financial_data(text, config):
    """
    从文本中解析金融数据。
    返回一个列表，每个元素是一条数据记录 (dict)。
    """
    if not text:
        return []

    records = []
    date = extract_date(text, config)
    keywords = config.get("keywords", [])

    lines = text.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 查找每行中匹配的关键词和数值
        matched_keywords = [kw for kw in keywords if kw in line]
        if not matched_keywords:
            continue

        # 提取该行的数字
        numbers = re.findall(r"[-+]?\d[\d,]*\.?\d*\s*%?(?:\s*[万亿])?", line)

        for kw in matched_keywords:
            record = {
                "日期": date,
                "指标": kw,
                "数值": ", ".join(n.strip() for n in numbers) if numbers else "见原文",
                "原文": line[:200],  # 截断过长的行
            }
            records.append(record)

    # 如果没有匹配到关键词，也保存原始文本作为记录
    if not records and len(text.strip()) > 0:
        records.append({
            "日期": date,
            "指标": "原始记录",
            "数值": "",
            "原文": text[:500],
        })

    return records


# ── Excel 输出 ────────────────────────────────────────────

def create_or_update_excel(records, config):
    """创建或更新 Excel 文件"""
    if not HAS_OPENPYXL:
        print("[错误] 未安装 openpyxl，无法生成Excel文件")
        print("请运行: pip install openpyxl")
        return None

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    excel_path = OUTPUT_DIR / config.get("excel_filename", "financial_data.xlsx")

    # 定义表头
    headers = ["日期", "指标", "数值", "原文", "来源文件", "处理时间"]

    if excel_path.exists():
        wb = openpyxl.load_workbook(excel_path)
        ws = wb.active
    else:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = config.get("company_name", "金融数据")

        # 写表头 + 样式
        header_font = Font(name="微软雅黑", bold=True, color="FFFFFF", size=11)
        header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
        header_align = Alignment(horizontal="center", vertical="center")

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_align

        # 设置列宽
        col_widths = [14, 14, 20, 60, 30, 20]
        for i, width in enumerate(col_widths, 1):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = width

    # 追加数据
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_font = Font(name="微软雅黑", size=10)
    thin_border = Border(
        left=Side(style="thin", color="D9D9D9"),
        right=Side(style="thin", color="D9D9D9"),
        top=Side(style="thin", color="D9D9D9"),
        bottom=Side(style="thin", color="D9D9D9"),
    )

    for record in records:
        row = [
            record.get("日期", ""),
            record.get("指标", ""),
            record.get("数值", ""),
            record.get("原文", ""),
            record.get("来源文件", ""),
            now,
        ]
        ws.append(row)
        # 给新行设置样式
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=ws.max_row, column=col)
            cell.font = data_font
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center", wrap_text=(col == 4))

    wb.save(excel_path)
    return excel_path


# ── 主流程 ────────────────────────────────────────────────

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}
TEXT_EXTENSIONS = {".txt", ".csv", ".text", ".msg", ".log"}


def process_single_file(filepath, config):
    """处理单个文件，返回提取的记录列表"""
    filepath = Path(filepath)
    ext = filepath.suffix.lower()

    print(f"  处理文件: {filepath.name}")

    if ext in IMAGE_EXTENSIONS:
        text = extract_text_from_image(filepath, config)
    elif ext in TEXT_EXTENSIONS:
        text = extract_text_from_file(filepath)
    else:
        print(f"  [跳过] 不支持的文件类型: {ext}")
        return []

    if not text:
        print(f"  [跳过] 未提取到内容: {filepath.name}")
        return []

    records = parse_financial_data(text, config)
    for r in records:
        r["来源文件"] = filepath.name

    print(f"  -> 提取到 {len(records)} 条记录")
    return records


def process_all_files(config):
    """处理 input 文件夹中的所有新文件"""
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    processed_log = load_processed_log()

    all_files = sorted(INPUT_DIR.iterdir())
    supported = [f for f in all_files if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS | TEXT_EXTENSIONS]

    if not supported:
        print(f"\n[提示] input 文件夹为空，请将图片或文字文件放入: {INPUT_DIR.resolve()}")
        return

    new_records = []
    new_count = 0
    skip_count = 0

    for filepath in supported:
        fhash = file_hash(filepath)
        if str(filepath.name) in processed_log and processed_log[str(filepath.name)] == fhash:
            skip_count += 1
            continue

        records = process_single_file(filepath, config)
        new_records.extend(records)
        processed_log[str(filepath.name)] = fhash
        new_count += 1

    if skip_count > 0:
        print(f"\n  [跳过] {skip_count} 个已处理的文件")

    if new_records:
        excel_path = create_or_update_excel(new_records, config)
        if excel_path:
            print(f"\n{'='*50}")
            print(f"  Excel 已更新！")
            print(f"  文件路径: {excel_path.resolve()}")
            print(f"  本次新增: {len(new_records)} 条记录（来自 {new_count} 个文件）")
            print(f"{'='*50}")
        save_processed_log(processed_log)
    else:
        print("\n  [提示] 没有新的数据需要处理")


def watch_mode(config, interval=5):
    """监控模式：每隔几秒检查新文件"""
    print(f"\n  监控模式已启动，每 {interval} 秒检查一次新文件...")
    print(f"  监控文件夹: {INPUT_DIR.resolve()}")
    print(f"  按 Ctrl+C 停止\n")

    try:
        while True:
            process_all_files(config)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\n\n  监控已停止。")


def main():
    parser = argparse.ArgumentParser(description="金融数据自动提取工具")
    parser.add_argument("--watch", action="store_true", help="启动监控模式，持续检查新文件")
    parser.add_argument("--interval", type=int, default=5, help="监控模式检查间隔（秒），默认5秒")
    parser.add_argument("--reset", action="store_true", help="清除已处理记录，重新处理所有文件")
    args = parser.parse_args()

    print("\n" + "=" * 50)
    print("  金融数据自动提取工具")
    print("=" * 50)

    # 检查依赖
    missing = []
    if not HAS_OPENPYXL:
        missing.append("openpyxl")
    if not HAS_PIL:
        missing.append("Pillow")
    if not HAS_TESSERACT:
        missing.append("pytesseract")

    if missing:
        print(f"\n  [提示] 缺少以下依赖: {', '.join(missing)}")
        print(f"  请运行: pip install {' '.join(missing)}")
        if "openpyxl" in missing:
            print("  (openpyxl 是必须的，用于生成Excel)")
            sys.exit(1)
        if "Pillow" in missing or "pytesseract" in missing:
            print("  (图片处理需要 Pillow 和 pytesseract，纯文字文件不需要)")

    config = load_config()
    print(f"\n  公司名称: {config['company_name']}")
    print(f"  输入文件夹: {INPUT_DIR.resolve()}")
    print(f"  输出文件夹: {OUTPUT_DIR.resolve()}")

    if args.reset and PROCESSED_LOG.exists():
        os.remove(PROCESSED_LOG)
        print("\n  已清除处理记录，将重新处理所有文件")

    if args.watch:
        watch_mode(config, args.interval)
    else:
        process_all_files(config)


if __name__ == "__main__":
    main()
