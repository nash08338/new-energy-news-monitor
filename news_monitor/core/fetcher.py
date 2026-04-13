# core/fetcher.py
import feedparser
import time
import random
import logging
from ..utils.time_utils import parse_pub_date, now_cst
from ..utils.region_utils import get_region

logger = logging.getLogger(__name__)

def fetch_source(source, seven_days_ago, seen_urls):
    name           = source["name"]
    rss_url        = source["rss"]
    supports_paged = source.get("paged", True)
    stop_on_old    = source.get("stop_on_old", True)   # 默认 True（保持原有行为）
    new_data       = []
    today_str      = now_cst().strftime('%Y-%m-%d')

    logger.info(f"\n{'='*50}\n📡 来源：{name}\n{'='*50}")

    for page in range(1, 100):
        if page > 1 and not supports_paged:
            break

        paged_url = f"{rss_url}?paged={page}" if page > 1 else rss_url
        logger.info(f"  🔍 第 {page} 页：{paged_url}")

        feed = None
        for attempt in range(3):
            try:
                # 使用更真实的 User-Agent，模拟主流浏览器
                feed = feedparser.parse(
                    paged_url,
                    agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
                )
                if hasattr(feed, 'status') and feed.status in (301, 302) and feed.get("href"):
                    feed = feedparser.parse(
                        feed.href,
                        agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36"
                    )
                if feed.entries:
                    break
            except Exception as e:
                logger.error(f"  ⚠️ 第 {attempt+1} 次请求异常：{e}")
                feed = None
            logger.info(f"  ⚠️ 第 {attempt+1} 次返回空，等待后重试...")
            time.sleep(random.uniform(3.0, 6.0))

        if not feed or not feed.entries:
            logger.info("  🏁 重试3次仍为空，停止。")
            break

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
            else:
                if stop_on_old:
                    logger.info(f"  🛑 触达时间边界 ({pub_date.strftime('%Y-%m-%d')})，停止。")
                    hit_old = True
                    break
                else:
                    logger.info(f"  ℹ️ 跳过旧新闻 {pub_date.strftime('%Y-%m-%d')}，但继续抓取后续条目。")
                    # 不 break，继续循环

        if hit_old:
            break
        time.sleep(random.uniform(1.5, 3.0))

    logger.info(f"  ✅ {name} 本次新增：{len(new_data)} 条")
    return new_data
