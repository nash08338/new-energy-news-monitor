# utils/file_utils.py
import os
import csv
from .time_utils import now_cst
import logging

logger = logging.getLogger(__name__)

def load_used_links(used_file):
    """加载已使用的链接"""
    used = set()
    if os.path.exists(used_file):
        with open(used_file, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader, None)
            for r in reader:
                if r:
                    used.add(r[0])
    return used

def save_used_links(links, used_file):
    """保存已使用的链接"""
    existing = set()
    if os.path.exists(used_file):
        with open(used_file, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader, None)
            for r in reader:
                if r:
                    existing.add(r[0])

    new_links = [l for l in links if l not in existing]
    if not new_links:
        logger.info("  ℹ️ 无新链接需要写入 used_news")
        return

    file_exists = os.path.exists(used_file)
    with open(used_file, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["详情链接", "使用日期"])
        for link in new_links:
            writer.writerow([link, now_cst().strftime("%Y-%m-%d")])

    logger.info(f"  ✅ 写入 {len(new_links)} 条到 used_news（跳过 {len(links)-len(new_links)} 条重复）")

def load_unused_news(master_file, used_file, max_count=150):
    """加载未使用的新闻"""
    if not os.path.exists(master_file):
        logger.info("  ⚠️ 总表不存在，跳过")
        return []

    used_links = load_used_links(used_file)
    unused = []
    with open(master_file, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.reader(f)
        next(reader, None)
        for r in reader:
            if len(r) >= 5 and r[4] not in used_links:
                unused.append(r)

    total = len(unused)
    if total > max_count:
        unused = unused[:max_count]
        logger.info(f"  📰 未使用新闻：{total} 条，取最新 {max_count} 条传给 DeepSeek")
    else:
        logger.info(f"  📰 未使用新闻：{total} 条")

    if len(unused) < 8:
        logger.info(f"  ⚠️ 未使用新闻不足8条，建议增加抓取频率或扩大 DAYS_BACK")
    return unused
