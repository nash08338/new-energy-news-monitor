# core/esi_parser.py
import os
import json
import logging
from datetime import datetime

from ..utils.time_utils import now_cst
from ..utils.region_utils import get_region

logger = logging.getLogger(__name__)

def parse_esi_africa_json(esi_json_file, esi_keywords, seen_urls):
    """解析ESI Africa JSON文件"""
    if not os.path.exists(esi_json_file):
        logger.info("  ℹ️ ESI Africa JSON 不存在，跳过")
        return []

    try:
        with open(esi_json_file, "r", encoding="utf-8") as f:
            posts = json.load(f)
    except Exception as e:
        logger.error(f"  ⚠️ ESI Africa JSON 解析失败：{e}")
        return []

    new_data = []
    today_str = now_cst().strftime('%Y-%m-%d')
    skipped = 0

    for post in posts:
        title = post.get("title", {}).get("rendered", "").strip()
        link = post.get("link", "").strip()
        date_raw = post.get("date", "")
        classes = " ".join(post.get("class_list", []))

        try:
            date_str = datetime.fromisoformat(date_raw).strftime("%Y-%m-%d")
        except Exception:
            continue

        if not title or not link or not date_str:
            continue

        combined = (title + " " + classes).lower()
        if not any(kw in combined for kw in esi_keywords):
            skipped += 1
            continue

        if link not in seen_urls:
            new_data.append([
                "ESI_Africa",
                get_region(title),
                title,
                date_str,
                link,
                today_str,
            ])
            seen_urls.add(link)

    logger.info(f"  ✅ ESI Africa 注入：{len(new_data)} 条（过滤掉 {skipped} 条无关内容）")
    return new_data
