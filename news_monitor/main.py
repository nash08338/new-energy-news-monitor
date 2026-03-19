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
from utils.time_utils import now_cst
from utils.file_utils import load_unused_news
from core.fetcher import fetch_source
from core.esi_parser import parse_esi_africa_json
from core.csv_handler import split_by_date, merge_to_master
from ai.deepseek import call_deepseek
from screenshot.generator import generate_images

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

    # 抓取所有RSS源
    all_new_data = []
    for source in Config.SOURCES:
        all_new_data.extend(fetch_source(source, seven_days_ago, seen_urls))

    # 解析ESI Africa
    all_new_data.extend(parse_esi_africa_json(
        Config.ESI_JSON_FILE, 
        Config.ESI_KEYWORDS, 
        seen_urls
    ))

    # 处理CSV文件
    if all_new_data:
        all_new_data.sort(key=lambda x: x[3], reverse=True)
        written_files = split_by_date(all_new_data, Config.DAILY_DIR, Config.HEADER)
        merge_to_master(written_files, Config.MASTER_FILE, Config.HEADER)
        logger.info(f"  🎉 本次新增 {len(all_new_data)} 条新闻入库")
    else:
        logger.info("☕ 本次无新增新闻。")

    # 生成图片
    unused_news = load_unused_news(Config.MASTER_FILE, Config.USED_FILE)
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
