#!/usr/bin/env python3
"""
金融高频数据自动化整理工具
=============================
将 input/ 文件夹中的图片和文字文件自动提取、整理并输出到 Excel。

使用方法:
    1. 将图片(.png/.jpg/.jpeg) 或 文本文件(.txt) 放入 input/ 文件夹
    2. 运行: python process_data.py
    3. 在 output/ 文件夹中查看生成的 Excel 文件
"""

import os
import re
import sys
import json
import glob
import hashlib
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
PROCESSED_LOG = BASE_DIR / ".processed_files.json"
CONFIG_FILE = BASE_DIR / "config.json"

# ── 默认提取模式（正则表达式）────────────────────────────
# 你可以在 config.json 中自定义这些模式
DEFAULT_PATTERNS = {
    "日期": [
        r"(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日号]?)",
        r"(\d{1,2}[-/月]\d{1,2}[日号]?)",
    ],
    "股票代码": [
        r"([036]\d{5})",
        r"(SH\d{6}|SZ\d{6})",
        r"([A-Z]{1,5})",  # 美股代码
    ],
    "股票名称": [
        r"[\u4e00-\u9fa5]{2,6}(?:股份|集团|科技|银行|证券|保险|基金)",
    ],
    "价格": [
        r"(?:价格|现价|收盘价|开盘价|成交价)[：:]\s*(\d+\.?\d*)",
        r"(\d+\.\d{2})\s*(?:元|¥)",
    ],
    "涨跌幅": [
        r"(?:涨跌幅|涨幅|跌幅)[：:]\s*([+-]?\d+\.?\d*%?)",
        r"([+-]\d+\.?\d*%)",
    ],
    "成交量": [
        r"(?:成交量|量)[：:]\s*(\d+[\d,.]*\s*(?:万?手?|股)?)",
        r"(\d+[\d,.]*)\s*(?:万?手)",
    ],
    "成交额": [
        r"(?:成交额|额)[：:]\s*(\d+[\d,.]*\s*(?:万|亿)?元?)",
    ],
    "备注": [
        r"(?:备注|说明|评论|点评)[：:]\s*(.+)",
    ],
}


def load_config():
    """加载配置文件，如果不存在则使用默认配置。"""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"patterns": DEFAULT_PATTERNS, "company_name": ""}


def load_processed_log():
    """加载已处理文件记录。"""
    if PROCESSED_LOG.exists():
        with open(PROCESSED_LOG, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_processed_log(log):
    """保存已处理文件记录。"""
    with open(PROCESSED_LOG, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def file_hash(filepath):
    """计算文件的 MD5 哈希值，用于判断文件是否变更。"""
    h = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def extract_text_from_image(image_path):
    """从图片中提取文字（OCR）。"""
    if not HAS_PIL:
        print(f"  [警告] 未安装 Pillow，无法处理图片: {image_path}")
        print("  请运行: pip install Pillow")
        return ""
    if not HAS_TESSERACT:
        print(f"  [警告] 未安装 pytesseract，无法处理图片: {image_path}")
        print("  请运行: pip install pytesseract")
        print("  并安装 Tesseract-OCR: https://github.com/tesseract-ocr/tesseract")
        return ""

    try:
        img = Image.open(image_path)
        # 尝试中英文双语 OCR
        text = pytesseract.image_to_string(img, lang="chi_sim+eng")
        return text
    except Exception as e:
        print(f"  [错误] OCR 处理失败 ({image_path}): {e}")
        return ""


def read_text_file(filepath):
    """读取文本文件内容。"""
    encodings = ["utf-8", "gbk", "gb2312", "utf-16", "latin-1"]
    for enc in encodings:
        try:
            with open(filepath, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    print(f"  [警告] 无法读取文件: {filepath}")
    return ""


def extract_fields(text, patterns):
    """用正则表达式从文本中提取字段。"""
    result = {}
    for field_name, pattern_list in patterns.items():
        for pattern in pattern_list:
            matches = re.findall(pattern, text)
            if matches:
                # 取第一个匹配结果
                result[field_name] = matches[0].strip() if isinstance(matches[0], str) else matches[0]
                break
    return result


def extract_all_text_lines(text):
    """将原始文本也保留，以便人工核对。"""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines[:20])  # 最多保留 20 行


def process_files():
    """扫描 input 文件夹，处理新文件或已变更文件。"""
    config = load_config()
    patterns = config.get("patterns", DEFAULT_PATTERNS)
    processed_log = load_processed_log()

    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    # 支持的文件类型
    image_exts = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".webp"}
    text_exts = {".txt", ".csv", ".log", ".md"}

    all_files = sorted(INPUT_DIR.iterdir())
    new_records = []
    updated_count = 0

    for filepath in all_files:
        if filepath.is_dir() or filepath.name.startswith("."):
            continue

        ext = filepath.suffix.lower()
        if ext not in image_exts and ext not in text_exts:
            continue

        # 检查是否已处理过（且未变更）
        fhash = file_hash(filepath)
        file_key = str(filepath.name)
        if file_key in processed_log and processed_log[file_key]["hash"] == fhash:
            # 文件未变更，加载已有记录
            new_records.append(processed_log[file_key]["record"])
            continue

        # 新文件或已变更文件
        print(f"  处理: {filepath.name}")
        updated_count += 1

        if ext in image_exts:
            raw_text = extract_text_from_image(filepath)
        else:
            raw_text = read_text_file(filepath)

        if not raw_text.strip():
            print(f"    -> 未能提取到文本内容")
            record = {
                "文件名": filepath.name,
                "处理时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "原始内容": "(无内容)",
            }
        else:
            fields = extract_fields(raw_text, patterns)
            record = {
                "文件名": filepath.name,
                "处理时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            # 按配置中的字段顺序添加
            for field_name in patterns:
                record[field_name] = fields.get(field_name, "")
            record["原始内容"] = extract_all_text_lines(raw_text)

        new_records.append(record)
        processed_log[file_key] = {"hash": fhash, "record": record}

    save_processed_log(processed_log)
    return new_records, updated_count


def write_excel(records):
    """将记录写入 Excel 文件。"""
    if not HAS_OPENPYXL:
        print("\n[错误] 未安装 openpyxl，无法生成 Excel 文件")
        print("请运行: pip install openpyxl")
        # 回退到 CSV
        write_csv_fallback(records)
        return

    if not records:
        print("\n没有数据记录，跳过 Excel 生成。")
        return

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "金融数据汇总"

    # 获取所有列名
    columns = list(records[0].keys())

    # 样式
    header_font = Font(name="微软雅黑", bold=True, size=11, color="FFFFFF")
    header_fill = PatternFill(start_color="2F5496", end_color="2F5496", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    cell_align = Alignment(vertical="top", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )

    # 写表头
    for col_idx, col_name in enumerate(columns, 1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align
        cell.border = thin_border

    # 写数据
    for row_idx, record in enumerate(records, 2):
        for col_idx, col_name in enumerate(columns, 1):
            value = record.get(col_name, "")
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = cell_align
            cell.border = thin_border

    # 自动调整列宽
    for col_idx, col_name in enumerate(columns, 1):
        max_len = len(col_name) * 2  # 中文字符宽度
        for row_idx in range(2, len(records) + 2):
            val = str(ws.cell(row=row_idx, column=col_idx).value or "")
            # 取第一行的长度估算
            first_line = val.split("\n")[0] if val else ""
            max_len = max(max_len, len(first_line.encode("utf-8", errors="ignore")))
        ws.column_dimensions[openpyxl.utils.get_column_letter(col_idx)].width = min(max_len + 2, 50)

    # 冻结首行
    ws.freeze_panes = "A2"

    # 保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"金融数据_{timestamp}.xlsx"
    output_path = OUTPUT_DIR / filename
    wb.save(output_path)

    # 同时保存一个固定名称的"最新版"
    latest_path = OUTPUT_DIR / "最新数据.xlsx"
    wb.save(latest_path)

    print(f"\n  Excel 已生成:")
    print(f"    {output_path}")
    print(f"    {latest_path} (最新版)")


def write_csv_fallback(records):
    """当 openpyxl 不可用时，回退到 CSV 格式。"""
    import csv
    if not records:
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"金融数据_{timestamp}.csv"
    output_path = OUTPUT_DIR / filename
    columns = list(records[0].keys())
    with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(records)
    print(f"\n  CSV 已生成 (openpyxl 未安装，使用 CSV 替代):")
    print(f"    {output_path}")


def main():
    print("=" * 50)
    print("  金融高频数据自动化整理工具")
    print("=" * 50)

    # 检查 input 文件夹
    if not INPUT_DIR.exists():
        INPUT_DIR.mkdir(parents=True)
        print(f"\n已创建 input 文件夹: {INPUT_DIR}")
        print("请将图片或文本文件放入此文件夹后重新运行。")
        return

    # 统计文件
    files = [f for f in INPUT_DIR.iterdir() if f.is_file() and not f.name.startswith(".")]
    if not files:
        print(f"\n  input 文件夹为空: {INPUT_DIR}")
        print("  请将图片(.png/.jpg) 或 文本(.txt) 文件放入后重新运行。")
        return

    print(f"\n  发现 {len(files)} 个文件，开始处理...\n")

    records, updated_count = process_files()

    if updated_count == 0:
        print("\n  所有文件均已处理过，无新变更。")
        print("  如需重新生成 Excel，请删除 .processed_files.json 后重新运行。")
    else:
        print(f"\n  本次处理了 {updated_count} 个新/变更文件")

    write_excel(records)

    print(f"\n  总计 {len(records)} 条数据记录")
    print("=" * 50)


if __name__ == "__main__":
    main()
