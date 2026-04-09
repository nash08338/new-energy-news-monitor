# core/sitemap_parser.py
import xml.etree.ElementTree as ET
import requests
from datetime import datetime
import logging

from ..utils.time_utils import now_cst
from ..utils.region_utils import get_region

logger = logging.getLogger(__name__)

def fetch_from_sitemap(url, seven_days_ago, seen_urls, source_name="RenewablesNow", keywords=None):
    """
    从 sitemap XML 抓取新闻，返回格式与 fetch_source 一致。

    :param url: sitemap 的 URL
    :param seven_days_ago: datetime 对象，用于过滤旧新闻（带时区）
    :param seen_urls: 已见链接的集合（用于去重）
    :param source_name: 来源名称
    :param keywords: 可选的关键词列表（小写），若提供则只保留标题中含任一关键词的新闻
    :return: 新闻列表，每条为 [来源, 区域, 标题, 日期, 链接, 抓取日期]
    """
    new_data = []
    today_str = now_cst().strftime('%Y-%m-%d')
    
    # 如果没有传入关键词，尝试从 config 导入
    if keywords is None:
        try:
            from ..config import Config
            keywords = Config.SOLAR_STORAGE_KEYWORDS
        except (ImportError, AttributeError):
            logger.warning("  ⚠️ 未提供关键词，将抓取所有新闻")
            keywords = []
    
    # 确保关键词列表是小写
    keywords_lower = [kw.lower() for kw in keywords] if keywords else []

    # 增强的请求头，模拟真实浏览器
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }
    
    # 为特定域名添加 Referer（可选，提高成功率）
    if 'renewablesnow.com' in url:
        headers['Referer'] = 'https://renewablesnow.com/'

    try:
        # 下载 XML
        resp = requests.get(url, timeout=30, headers=headers)
        resp.raise_for_status()
        
        # 解析 XML
        root = ET.fromstring(resp.content)
        
        # sitemap 命名空间
        ns = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
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
                # 格式: 2026-03-20T18:51:22+02:00 或类似
                date_str = lastmod_elem.text.split('T')[0]
                pub_date = datetime.strptime(date_str, '%Y-%m-%d')
                # 为 pub_date 添加时区信息，以便与 seven_days_ago 比较
                # seven_days_ago 是带时区的（来自 now_cst），这里假设使用相同的时区
                if seven_days_ago.tzinfo is not None:
                    pub_date = pub_date.replace(tzinfo=seven_days_ago.tzinfo)
            except Exception as e:
                logger.debug(f"日期解析失败: {e}")
                continue
            
            if pub_date < seven_days_ago:
                continue
                
            # 获取标题：优先尝试从 image:title 获取，否则从 URL 中提取
            title = None
            # 检查是否有 image:title（Google sitemap 扩展）
            image_title = url_elem.find('.//{http://www.google.com/schemas/sitemap-image/1.1}title')
            if image_title is not None and image_title.text:
                title = image_title.text
            else:
                # 从 URL 路径提取标题（简单处理）
                # 示例：/news/xxxx-title-12345/
                parts = link.split('/')
                for part in reversed(parts):
                    if part and 'news' not in part and 'story' not in part:
                        title_candidate = part.replace('-', ' ').title()
                        if len(title_candidate) > 10:
                            title = title_candidate
                            break
                if not title:
                    title = "Unknown Title"
            
            # 关键词筛选
            title_lower = title.lower()
            if keywords_lower and not any(kw in title_lower for kw in keywords_lower):
                continue   # 不符合关键词，跳过
            
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
            
        logger.info(f"  ✅ {source_name} sitemap 抓取：{len(new_data)} 条（已过滤关键词）")
        
    except requests.exceptions.RequestException as e:
        logger.error(f"  ⚠️ {source_name} sitemap 抓取失败（网络请求错误）: {e}")
    except ET.ParseError as e:
        logger.error(f"  ⚠️ {source_name} sitemap XML 解析失败: {e}")
    except Exception as e:
        logger.error(f"  ⚠️ {source_name} sitemap 抓取失败: {e}")
    
    return new_data
