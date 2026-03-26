# core/archive_parser.py
import xml.etree.ElementTree as ET
import requests
from datetime import datetime
import logging
from ..utils.time_utils import now_cst
from ..utils.region_utils import get_region

logger = logging.getLogger(__name__)

def fetch_ev_archive(source_name, base_url, seven_days_ago, seen_urls):
    """
    抓取 EV Infrastructure News 的月度归档 XML。
    base_url 示例：https://www.evinfrastructurenews.com/news/archive/{year}/{month}.xml
    函数内会自动替换为当前年月。
    """
    # 动态构造当前月份的 URL
    current_date = now_cst()
    year = current_date.strftime("%Y")
    month = current_date.strftime("%B").lower()  # 例如 "march"
    url = base_url.format(year=year, month=month)
    
    logger.info(f"\n📡 来源：{source_name}")
    logger.info(f"  🔍 抓取：{url}")
    
    new_data = []
    today_str = now_cst().strftime('%Y-%m-%d')
    
    try:
        resp = requests.get(url, timeout=30, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        resp.raise_for_status()
        
        # 解析 XML
        root = ET.fromstring(resp.content)
        # 命名空间（如果存在）
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        # 遍历所有 <url> 元素
        for url_elem in root.findall('ns:url', ns):
            loc_elem = url_elem.find('ns:loc', ns)
            lastmod_elem = url_elem.find('ns:lastmod', ns)
            
            if loc_elem is None or lastmod_elem is None:
                continue
            
            link = loc_elem.text
            if link in seen_urls:
                continue
            
            # 解析发布日期
            try:
                # 格式: 2026-03-25T11:32:13.000Z
                date_str = lastmod_elem.text.split('T')[0]
                pub_date = datetime.strptime(date_str, '%Y-%m-%d')
                # 添加时区
                if seven_days_ago.tzinfo is not None:
                    try:
                        import pytz
                        tz = pytz.timezone("Asia/Shanghai")
                        pub_date = tz.localize(pub_date)
                    except ImportError:
                        from zoneinfo import ZoneInfo
                        pub_date = pub_date.replace(tzinfo=ZoneInfo("Asia/Shanghai"))
            except Exception as e:
                logger.debug(f"日期解析失败: {e}")
                continue
            
            # 只保留近7天的新闻
            if pub_date < seven_days_ago:
                continue
            
            # 从 URL 中提取标题
            # 例如：/us-electric-truck-shared-charging-infrastructure-expands
            slug = link.rstrip('/').split('/')[-1]
            title = slug.replace('-', ' ').title()
            # 如果标题为空，尝试用 URL 倒数第二段
            if not title or len(title) < 5:
                parts = link.rstrip('/').split('/')
                if len(parts) >= 2:
                    title = parts[-2].replace('-', ' ').title()
            
            # 确定区域
            region = get_region(title)
            
            new_data.append([
                source_name,
                region,
                title,
                pub_date.strftime('%Y-%m-%d'),
                link,
                today_str,
            ])
            seen_urls.add(link)
        
        logger.info(f"  ✅ {source_name} 归档抓取：{len(new_data)} 条")
        
    except Exception as e:
        logger.error(f"  ⚠️ {source_name} 归档抓取失败: {e}")
    
    return new_data