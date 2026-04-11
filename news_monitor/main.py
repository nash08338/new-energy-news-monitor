# main.py
import sys
import asyncio
import os
import logging
from datetime import datetime, timedelta
from openai import OpenAI

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from .config import Config
from .utils.time_utils import now_cst
from .utils.file_utils import load_unused_news
from .core.fetcher import fetch_source
from .core.sitemap_parser import fetch_from_sitemap   # sitemap 解析器
from .core.csv_handler import split_by_date, merge_to_master
from .ai.deepseek import call_deepseek
from .screenshot.generator import generate_images
from .core.archive_parser import fetch_ev_archive      # 归档解析器
from .core.esi_parser import parse_esi_africa_json
from .core.wp_api_parser import fetch_wp_api           # WordPress REST API 解析器
from .core.archive_parser import fetch_ev_archive, fetch_ev_googlenews

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# DeepSeek客户端初始化
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not DEEPSEEK_API_KEY:
    logger.warning("DEEPSEEK_API_KEY 未设置，后续 DeepSeek 调用将跳过，图片生成功能不可用。")
    client = None
else:
    client = OpenAI(
        api_key=DEEPSEEK_API_KEY,
        base_url="https://api.deepseek.com",
        timeout=Config.DEEPSEEK_TIMEOUT
    )

def deduplicate_unused_news(news_list, threshold=0.8):
    """对未使用新闻列表进行相似度去重，保留最新的一条"""
    if not news_list:
        return news_list
    # 按发布日期降序排序（最新在前）
    sorted_news = sorted(news_list, key=lambda x: x[3], reverse=True)
    unique = []
    for news in sorted_news:
        title = news[2]
        is_dup = False
        for existing in unique:
            # 计算 Jaccard 相似度
            set1 = set(title.lower().split())
            set2 = set(existing[2].lower().split())
            if not set1 or not set2:
                continue
            sim = len(set1 & set2) / len(set1 | set2)
            if sim >= threshold:
                is_dup = True
                break
        if not is_dup:
            unique.append(news)
    # 恢复按日期降序（已有序）
    return unique

def main():
    """主程序入口"""
    seven_days_ago = now_cst() - timedelta(days=Config.DAYS_BACK)
    seven_days_ago = seven_days_ago.replace(hour=0, minute=0, second=0)

    logger.info(f"[{now_cst().strftime('%Y-%m-%d %H:%M:%S')}] 启动全球新能源新闻监控（北京时间）")
    logger.info(f"📅 抓取范围：{seven_days_ago.strftime('%Y-%m-%d')} 至今")

    # 加载已存在的链接
    seen_urls = set()
    if os.path.exists(Config.MASTER_FILE):
        with open(Config.MASTER_FILE, "r", encoding="utf-8-sig", errors="replace") as f:
            import csv
            reader = csv.reader(f)
            next(reader, None)
            for r in reader:
                if len(r) >= 5:
                    seen_urls.add(r[4])
    logger.info(f"📋 总表已有记录：{len(seen_urls)} 条，用于去重")


    # 抓取所有 RSS / sitemap / 归档 / API 源
    all_new_data = []
    for source in Config.SOURCES:
        # 特殊处理 EVInfrastructureNews（googlenews.xml 是 Google News Sitemap 格式，feedparser 无法解析）
        if source["name"] == "EVInfrastructureNews":
            all_new_data.extend(fetch_ev_googlenews(
                source["name"],
                source["rss"],
                seven_days_ago,
                seen_urls
            ))
        # 特殊处理 EVInfrastructureNews 归档源
        elif source["name"] == "EVInfrastructureNews_Archive":
            base_url = "https://www.evinfrastructurenews.com/news/archive/{year}/{month}.xml"
            all_new_data.extend(fetch_ev_archive(
                source["name"],
                base_url,
                seven_days_ago,
                seen_urls
            ))
        # 特殊处理 RenewablesNow 的 sitemap（动态生成当前月份）
        elif source["name"] == "RenewablesNow" and "sitemap" in source:
            current_month = now_cst().strftime('%Y-%m')
            sitemap_url = f"https://renewablesnow.com/sitemap/news-{current_month}.xml"
            all_new_data.extend(fetch_from_sitemap(
                sitemap_url,
                seven_days_ago,
                seen_urls,
                source["name"],
                keywords=getattr(Config, "SOLAR_STORAGE_KEYWORDS", None)
            ))
        # 处理 WordPress REST API 源
        elif "api" in source:
            # 对于 ESI Africa API 源，不进行关键词筛选（因为已通过分类筛选）
            if source["name"] == "ESI_Africa_API":
                keywords = None
            else:
                keywords = getattr(Config, "SOLAR_STORAGE_KEYWORDS", None)
            all_new_data.extend(fetch_wp_api(
                source,
                source["api"],
                seven_days_ago,
                seen_urls,
                keywords=keywords
            ))
        # 其他 sitemap 源（如果有）仍可使用配置中的固定 URL
        elif "sitemap" in source:
            all_new_data.extend(fetch_from_sitemap(
                source["sitemap"],
                seven_days_ago,
                seen_urls,
                source["name"],
                keywords=getattr(Config, "SOLAR_STORAGE_KEYWORDS", None)
            ))
        else:
            # 原有 RSS 抓取
            all_new_data.extend(fetch_source(source, seven_days_ago, seen_urls))

    # ESI Africa JSON 解析（手动维护）
    all_new_data.extend(parse_esi_africa_json(Config.ESI_JSON_FILE, Config.ESI_KEYWORDS, seen_urls))
    
    def deduplicate_global(news_list, threshold=0.8):
        unique = []
        for news in sorted(news_list, key=lambda x: x[3], reverse=True):  # 按日期倒序
            title = news[2]
            is_dup = False
            for existing in unique:
                # 简单的 Jaccard 相似度
                set1 = set(title.lower().split())
                set2 = set(existing[2].lower().split())
                if not set1 or not set2:
                    continue
                sim = len(set1 & set2) / len(set1 | set2)
                if sim >= threshold:
                    is_dup = True
                    break
            if not is_dup:
                unique.append(news)
        return unique

    all_new_data = deduplicate_global(all_new_data)


    # 处理 CSV 文件
    if all_new_data:
        all_new_data.sort(key=lambda x: x[3], reverse=True)
        written_files = split_by_date(all_new_data, Config.DAILY_DIR, Config.HEADER)
        merge_to_master(written_files, Config.MASTER_FILE, Config.HEADER)
        logger.info(f"  🎉 本次新增 {len(all_new_data)} 条新闻入库")
    else:
        logger.info("☕ 本次无新增新闻。")

    # 生成图片
    unused_news = load_unused_news(Config.MASTER_FILE, Config.USED_FILE, max_count=300)
    # 对未使用新闻进行相似度去重，避免同一事件的不同报道被同时选中
    unused_news = deduplicate_unused_news(unused_news, threshold=0.8)
    data, used_links = call_deepseek(
        unused_news,
        Config,
        client,
        Config.USED_FILE,
        Config.CONFLICT_FILE
    )

    if data:
        generate_images(data, unused_news, used_links, Config)

    logger.info(f"\n✅ 全部完成！")

if __name__ == "__main__":
    main()