# core/wp_api_parser.py
import requests
import logging
from datetime import datetime
from ..utils.time_utils import now_cst
from ..utils.region_utils import get_region

logger = logging.getLogger(__name__)

def fetch_wp_api(source, base_url, seven_days_ago, seen_urls, keywords=None):
    """
    抓取 WordPress REST API 分页数据
    :param source: 源配置字典（需包含 name, api_url）
    :param base_url: API 基础 URL
    :param seven_days_ago: 时间边界
    :param seen_urls: 全局去重集合
    :param keywords: 可选的关键词列表（小写），若提供则只保留标题中含任一关键词的新闻
    :return: 新闻列表
    """
    name = source["name"]
    per_page = 100  # 每页最多 100 条
    page = 1
    new_data = []
    today_str = now_cst().strftime('%Y-%m-%d')
    
    # 确保关键词列表为小写
    if keywords:
        keywords_lower = [kw.lower() for kw in keywords]
    else:
        keywords_lower = []

    logger.info(f"\n{'='*50}\n📡 来源：{name}\n{'='*50}")

    while True:
        url = f"{base_url}?page={page}&per_page={per_page}"
        try:
            resp = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            resp.raise_for_status()
            posts = resp.json()
            if not posts:
                break  # 无数据，停止

            for post in posts:
                link = post.get('link')
                if link in seen_urls:
                    continue

                title = post.get('title', {}).get('rendered', '')
                if not title:
                    continue

                # 关键词筛选
                title_lower = title.lower()
                if keywords_lower and not any(kw in title_lower for kw in keywords_lower):
                    continue  # 不符合关键词，跳过

                date_str = post.get('date')
                try:
                    pub_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    # 为 pub_date 添加时区（假设与 seven_days_ago 一致）
                    if seven_days_ago.tzinfo is not None:
                        import pytz
                        tz = pytz.timezone("Asia/Shanghai")
                        pub_date = tz.localize(pub_date)
                except Exception:
                    continue

                if pub_date < seven_days_ago:
                    # API 按时间倒序，遇到旧新闻后可以停止翻页
                    return new_data

                region = get_region(title)

                new_data.append([
                    name,
                    region,
                    title,
                    pub_date.strftime('%Y-%m-%d'),
                    link,
                    today_str,
                ])
                seen_urls.add(link)

            logger.info(f"  📄 第 {page} 页：{len(posts)} 条")
            page += 1
        except Exception as e:
            logger.error(f"  ⚠️ 第 {page} 页抓取失败: {e}")
            break

    logger.info(f"  ✅ {name} API 抓取：{len(new_data)} 条")
    return new_data