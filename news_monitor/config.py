# config.py
import os

class Config:
    """集中管理所有配置"""

class Config:
    # 区域限制（根据新需求调整）
    MAX_REGIONS = 4                     # 从8降到4
    MIN_REGIONS = 3                      # 可保持3不变
    MAX_TITLES_PER_REGION = 4            # 从5降到4
    MIN_TITLES_PER_REGION = 3
    
    # 时间范围
    DAYS_BACK = 7
    
    # 路径配置
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ROOT_DIR = os.path.dirname(BASE_DIR)
    
    DAILY_DIR = os.path.join(ROOT_DIR, "docs", "daily")
    MASTER_FILE = os.path.join(ROOT_DIR, "docs", "news_master.csv")
    USED_FILE = os.path.join(ROOT_DIR, "docs", "used_news.csv")
    IMAGE_DIR = os.path.join(ROOT_DIR, "docs", "images")
    CONFLICT_FILE = os.path.join(ROOT_DIR, "docs", "region_conflicts.csv")
    XHS_DIR = os.path.join(ROOT_DIR, "docs", "images", "xhs")
    ESI_JSON_FILE = os.path.join(ROOT_DIR, "docs", "esi_africa_raw.json")
    
    # CSV 头
    HEADER = ['来源', '所属区域', '文章标题', '发布日期', '详情链接', '抓取日期']
    
    # RSS 源配置
    SOURCES = [
        {"name": "SolarQuarter",      "rss": "https://solarquarter.com/category/news/feed/",                        "paged": True},
        {"name": "Electrive",         "rss": "https://www.electrive.com/category/energy-infrastructure/feed/",      "paged": True},
        {"name": "PowerTechnology",   "rss": "https://www.power-technology.com/news/feed/",                         "paged": True},
        {"name": "EnergyStorageNews", "rss": "https://www.energy-storage.news/category/news/feed/",                 "paged": True},
        {"name": "PVMagazine",        "rss": "https://www.pv-magazine.com/news/feed/",                              "paged": True},
        {"name": "PVTech",            "rss": "https://www.pv-tech.org/feed/",                                       "paged": True},
        {"name": "EnergyCapitalPow",  "rss": "https://energycapitalpower.com/feed/",                                "paged": True},
        {"name": "RenewEconomy",      "rss": "https://reneweconomy.com.au/feed/",                                   "paged": True},
        {"name": "EnergyNewsNetwork", "rss": "https://energy-news-network.com/feed/",                               "paged": True},
        {"name": "MercomIndia",       "rss": "https://mercomindia.com/feed/",                                       "paged": False},
        {"name": "RenewablesNow_SSA", "rss": "https://renewablesnow.com/news/news_feed/?region=sub-saharan+africa", "paged": False},
        {"name": "GNews_SouthAfrica", "rss": "https://news.google.com/rss/search?q=south+africa+solar+battery+storage&hl=en-US&gl=US&ceid=US:en",  "paged": False},
        {"name": "GNews_WestAfrica",  "rss": "https://news.google.com/rss/search?q=west+africa+solar+energy+storage&hl=en-US&gl=US&ceid=US:en",   "paged": False},
        {"name": "GNews_EastAfrica",  "rss": "https://news.google.com/rss/search?q=east+africa+kenya+solar+storage&hl=en-US&gl=US&ceid=US:en",    "paged": False},
    ]
    
    # ESI Africa 关键词
    ESI_KEYWORDS = [
        "solar", "storage", "battery", "photovoltaic", "pv",
        "charging", "grid", "renewable", "energy transition",
        "microgrid", "power", "electricity", "bess",
    ]
    
    # Footer
    FOOTER_SHORT = "SolarQuarter · PVMagazine · PVTech · EnergyStorageNews · RenewEconomy · MercomIndia · ESI_Africa · 及其他"
    
    # DeepSeek 配置
    DEEPSEEK_TIMEOUT = 45
    DEEPSEEK_MAX_RETRIES = 5
    DEEPSEEK_TEMPERATURE = 0.3
    
    @classmethod
    def get_prompt_limits(cls):
        """返回prompt中的限制描述"""
        return f"{cls.MIN_REGIONS}-{cls.MAX_REGIONS}个核心区域，每个区域{cls.MIN_TITLES_PER_REGION}-{cls.MAX_TITLES_PER_REGION}条新闻"
