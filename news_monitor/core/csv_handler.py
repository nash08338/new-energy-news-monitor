# core/csv_handler.py
import os
import csv
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

def split_by_date(all_new_data, daily_dir, header):
    """按日期拆分新闻到每日文件"""
    os.makedirs(daily_dir, exist_ok=True)
    grouped = defaultdict(list)
    for row in all_new_data:
        grouped[row[3]].append(row)

    written_files = []
    for date_str, rows in grouped.items():
        daily_file = os.path.join(daily_dir, f"news_{date_str}.csv")
        existing_links = set()
        if os.path.isfile(daily_file):
            with open(daily_file, "r", encoding="utf-8-sig", errors="replace") as f:
                reader = csv.reader(f)
                next(reader, None)
                for r in reader:
                    if len(r) >= 5:
                        existing_links.add(r[4])

        new_rows = [r for r in rows if r[4] not in existing_links]
        if not new_rows:
            continue

        file_exists = os.path.isfile(daily_file)
        with open(daily_file, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(header)
            writer.writerows(new_rows)

        written_files.append(daily_file)
        logger.info(f"  📅 {date_str}：新增 {len(new_rows)} 条 → {daily_file}")

    return written_files

def merge_to_master(daily_files, master_file, header):
    """合并到总表"""
    if not daily_files:
        return

    existing_links = set()
    if os.path.exists(master_file):
        with open(master_file, "r", encoding="utf-8-sig", errors="replace") as f:
            reader = csv.reader(f)
            next(reader, None)
            for r in reader:
                if len(r) >= 5:
                    existing_links.add(r[4])

    new_rows = []
    for filepath in daily_files:
        try:
            with open(filepath, "r", encoding="utf-8-sig", errors="replace") as fh:
                reader = csv.reader(fh)
                next(reader, None)
                for r in reader:
                    if len(r) >= 5 and r[4] not in existing_links:
                        new_rows.append(r)
                        existing_links.add(r[4])
        except Exception as e:
            logger.error(f"  ⚠️ 读取 {filepath} 失败：{e}")

    if not new_rows:
        logger.info("📋 总表无新增内容。")
        return

    file_exists = os.path.exists(master_file)
    with open(master_file, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(header)
        writer.writerows(new_rows)

    # 去重和排序
    all_rows = []
    with open(master_file, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        next(reader, None)
        seen = set()
        for r in reader:
            if len(r) >= 5 and r[4] not in seen:
                all_rows.append(r)
                seen.add(r[4])

    all_rows.sort(key=lambda x: x[3], reverse=True)
    with open(master_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(all_rows)

    logger.info(f"📋 总表已更新，新增 {len(new_rows)} 条，共 {len(all_rows)} 条")
