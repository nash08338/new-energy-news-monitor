# utils/file_utils.py
import os
import csv
import json
import logging
from datetime import datetime, timedelta

from .time_utils import now_cst

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


# 区域历史文件路径（指向项目根目录下的 docs）
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
REGION_HISTORY_FILE = os.path.join(ROOT_DIR, "docs", "used_regions.json")


def save_region_history(regions):
    """保存当天选中的区域列表到历史文件"""
    # 确保 docs 目录存在
    os.makedirs(os.path.dirname(REGION_HISTORY_FILE), exist_ok=True)
    today_str = now_cst().strftime("%Y-%m-%d")
    history = {}
    if os.path.exists(REGION_HISTORY_FILE):
        with open(REGION_HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    history[today_str] = regions
    # 只保留最近7天记录（按日期比较）
    cutoff_date = (now_cst() - timedelta(days=7)).date()
    history = {date: reg for date, reg in history.items()
               if datetime.strptime(date, "%Y-%m-%d").date() >= cutoff_date}
    with open(REGION_HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_recent_regions(days=3):
    """获取最近几天出现的区域（不含今天）"""
    if not os.path.exists(REGION_HISTORY_FILE):
        return []
    with open(REGION_HISTORY_FILE, "r", encoding="utf-8") as f:
        history = json.load(f)
    today = now_cst().strftime("%Y-%m-%d")
    cutoff_date = (now_cst() - timedelta(days=days)).date()
    recent = []
    for date, regions in sorted(history.items(), reverse=True):
        if date == today:
            continue
        dt_date = datetime.strptime(date, "%Y-%m-%d").date()
        if dt_date >= cutoff_date:
            recent.extend(regions)
        else:
            break   # 日期降序，一旦早于截止日就停止
    return list(set(recent))
