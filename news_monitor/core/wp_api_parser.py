# core/wp_api_parser.py
import requests
import logging
import time
from datetime import datetime
from ..utils.time_utils import now_cst
from ..utils.region_utils import get_region

logger = logging.getLogger(__name__)

def fetch_wp_api(source, base_url, seven_days_ago, seen_urls, keywords=None):
    """
    抓取 WordPress REST API 分页数据（针对 Cloudflare 优化）
    :param source: 源配置字典（需包含 name, api_url）
    :param base_url: API 基础 URL
    :param seven_days_ago: 时间边界（带时区）
    :param seen_urls: 全局去重集合
    :param keywords: 可选的关键词列表（小写），若提供则只保留标题中含任一关键词的新闻
    :return: 新闻列表
    """
    name = source["name"]
    per_page = 100
    page = 1
    new_data = []
    today_str = now_cst().strftime('%Y-%m-%d')
    
    if keywords:
        keywords_lower = [kw.lower() for kw in keywords]
    else:
        keywords_lower = []

    # 针对 Cloudflare 优化的请求头（模拟真实浏览器）
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'Sec-Ch-Ua': '"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # 创建 Session 对象，可以复用连接并保持 Cookie
    session = requests.Session()
    # 设置 Session 级别的 headers
    session.headers.update(headers)
    
    # 先访问首页获取 Cookie（模拟真实用户访问流程）
    try:
        home_url = base_url.split('?')[0].rsplit('/wp-json', 1)[0]  # 提取网站首页
        if home_url:
            logger.info(f"  🌐 预热访问首页获取 Cookie: {home_url}")
            home_resp = session.get(home_url, timeout=30)
            time.sleep(1)  # 等待一下，模拟真实用户
    except Exception as e:
        logger.debug(f"  预热访问失败（不影响主流程）: {e}")

    logger.info(f"\n{'='*50}\n📡 来源：{name}\n{'='*50}")

    while True:
        # 根据 base_url 是否已有查询参数决定连接符
        if '?' in base_url:
            url = f"{base_url}&page={page}&per_page={per_page}"
        else:
            url = f"{base_url}?page={page}&per_page={per_page}"

        logger.info(f"  🔍 第 {page} 页：{url}")

        try:
            # 使用 session 发起请求，自动携带 Cookie
            resp = session.get(url, timeout=30)
            
            # 如果返回 403，可能是 Cloudflare 挑战页，尝试等待后重试
            if resp.status_code == 403:
                logger.warning(f"  ⚠️ 第 {page} 页返回 403，可能是 Cloudflare 防护，等待 5 秒后重试...")
                time.sleep(5)
                resp = session.get(url, timeout=30)
                if resp.status_code == 403:
                    logger.error(f"  ❌ 第 {page} 页仍然返回 403，跳过此页")
                    break
            
            resp.raise_for_status()
            posts = resp.json()
            if not posts:
                break

            stop = False
            for post in posts:
                link = post.get('link')
                if link in seen_urls:
                    continue

                title = post.get('title', {}).get('rendered', '')
                if not title:
                    continue

                title_lower = title.lower()
                if keywords_lower and not any(kw in title_lower for kw in keywords_lower):
                    continue

                date_str = post.get('date')
                try:
                    pub_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                    if pub_date.date() < seven_days_ago.date():
                        logger.info(f"  🛑 触达时间边界 ({pub_date.date()})，停止。")
                        stop = True
                        break
                except Exception:
                    continue

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

            if stop:
                break

            # 若本页文章数少于 per_page，说明是最后一页
            if len(posts) < per_page:
                break

            page += 1
            # 增加请求间隔，降低被 Cloudflare 拦截的概率
            time.sleep(random.uniform(1.0, 2.0))
            
        except requests.exceptions.RequestException as e:
            logger.error(f"  ⚠️ 第 {page} 页请求失败: {e}")
            break
        except Exception as e:
            logger.error(f"  ⚠️ 第 {page} 页抓取失败: {e}")
            break

    logger.info(f"  ✅ {name} 本次新增：{len(new_data)} 条")
    return new_data
