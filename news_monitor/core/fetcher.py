# core/fetcher.py
import feedparser
import time
import random
import logging
import requests
from ..utils.time_utils import parse_pub_date, now_cst
from ..utils.region_utils import get_region

logger = logging.getLogger(__name__)

def fetch_source(source, seven_days_ago, seen_urls):
    name           = source["name"]
    rss_url        = source["rss"]
    supports_paged = source.get("paged", True)
    stop_on_old    = source.get("stop_on_old", True)
    new_data       = []
    today_str      = now_cst().strftime('%Y-%m-%d')

    logger.info(f"\n{'='*50}\n📡 来源：{name}\n{'='*50}")

    page = 1
    added_in_this_page = 0
    while True:
        if page > 1 and not supports_paged:
            logger.info("  🏁 该源不支持分页，停止。")
            break

        paged_url = f"{rss_url}?paged={page}" if page > 1 else rss_url
        logger.info(f"  🔍 第 {page} 页：{paged_url}")

        # 使用 requests 获取内容，便于设置完整请求头
        content = None
        for attempt in range(3):
            try:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Referer': rss_url.split('/feed')[0] + '/',
                }
                resp = requests.get(paged_url, timeout=30, headers=headers)
                resp.raise_for_status()
                content = resp.text
                break
            except Exception as e:
                logger.error(f"  ⚠️ 第 {attempt+1} 次请求异常：{e}")
                time.sleep(random.uniform(3.0, 6.0))
                content = None

        if not content:
            logger.info("  🏁 重试3次仍无内容，停止。")
            break

        # 用 feedparser 解析内容
        feed = feedparser.parse(content)
        if not feed.entries:
            logger.info("  🏁 解析后无条目，停止。")
            break

        added_in_this_page = 0
        hit_old = False
        for entry in feed.entries:
            link = entry.link
            pub_date = parse_pub_date(entry)
            if not pub_date:
                continue

            if pub_date >= seven_days_ago:
                if link not in seen_urls:
                    new_data.append([
                        name,
                        get_region(entry.title),
                        entry.title,
                        pub_date.strftime('%Y-%m-%d'),
                        link,
                        today_str,
                    ])
                    seen_urls.add(link)
                    added_in_this_page += 1
            else:
                if stop_on_old:
                    logger.info(f"  🛑 触达时间边界 ({pub_date.strftime('%Y-%m-%d')})，停止。")
                    hit_old = True
                    break
                else:
                    logger.info(f"  ℹ️ 跳过旧新闻 {pub_date.strftime('%Y-%m-%d')}，但继续抓取后续条目。")

        if hit_old:
            break

        if added_in_this_page == 0:
            logger.info("  🏁 本页无新增新闻（所有链接已存在），停止翻页。")
            break

        page += 1
        time.sleep(random.uniform(1.5, 3.0))

    logger.info(f"  ✅ {name} 本次新增：{len(new_data)} 条")
    return new_data