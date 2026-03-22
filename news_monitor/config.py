# config.py
import os

class Config:
    """集中管理所有配置"""
    # 区域限制（根据新需求调整）
    
    CREATED_BY = "香港汇展 Nash"
    MAX_TITLES_PER_REGION = 3            
    MIN_TITLES_PER_REGION = 3
    MIN_REGIONS = 4
    MAX_REGIONS = 5

    
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
        {"name": "RenewablesNow", "sitemap": "placeholder", "paged": False},
        # 以下 Google News 源均添加 stop_on_old=False
        {"name": "GNews_SouthAfrica", "rss": "https://news.google.com/rss/search?q=south+africa+solar+battery+storage&hl=en-US&gl=US&ceid=US:en",  "paged": False, "stop_on_old": False},
        {"name": "GNews_WestAfrica",  "rss": "https://news.google.com/rss/search?q=west+africa+solar+energy+storage&hl=en-US&gl=US&ceid=US:en",   "paged": False, "stop_on_old": False},
        {"name": "GNews_EastAfrica",  "rss": "https://news.google.com/rss/search?q=east+africa+kenya+solar+storage&hl=en-US&gl=US&ceid=US:en",    "paged": False, "stop_on_old": False},
        {"name": "GNews_StrategicEnergy", "rss": "https://news.google.com/rss/search?q=Strategic+Energy&hl=en-US&gl=US&ceid=US:en", "paged": False, "stop_on_old": False},
        {"name": "GNews_ESI_Africa", "rss": "https://news.google.com/rss/search?q=site:esi-africa.com+energy&hl=en-US&gl=US&ceid=US:en", "paged": False, "stop_on_old": False},
    ]
    
    # ESI Africa 关键词
    ESI_KEYWORDS = [
        "solar", "storage", "battery", "photovoltaic", "pv",
        "charging", "grid", "renewable", "energy transition",
        "microgrid", "power", "electricity", "bess",
    ]
    
    # 新增：光伏与储能关键词（用于 sitemap 筛选）
    SOLAR_STORAGE_KEYWORDS = ["solar", "pv", "photovoltaic",  "storage", "battery", 
             "charging", "grid", "renewable", "energy transition",
             "microgrid", "power", "electricity", "bess", "solar-plus-storage"]


    # Footer
    FOOTER_SHORT = "SolarQuarter · PVMagazine · PVTech · EnergyStorageNews · RenewEconomy · MercomIndia · StrategicEnergy · ESIAfrica · 及其他"
    
    # DeepSeek 配置
    DEEPSEEK_TIMEOUT = 60
    DEEPSEEK_MAX_RETRIES = 5
    DEEPSEEK_TEMPERATURE = 0.3

    # 固定区域白名单（DeepSeek 只能从这里选）
    REGION_LIST = [
        "全球/其他",
        "东亚",        # 中国、日本、韩国、台湾
        "东南亚",      # 泰国、越南、印尼、菲律宾、马来西亚
        "南亚",        # 印度、巴基斯坦、孟加拉
        "大洋洲",      # 澳大利亚、新西兰
        "西欧",        # 英国、德国、法国、西班牙、葡萄牙、荷兰、比利时
        "南欧",        # 希腊、意大利、土耳其
        "东欧",        # 波兰、罗马尼亚、捷克、匈牙利、乌克兰
        "北美",        # 美国、加拿大、墨西哥
        "拉丁美洲",    # 巴西、智利、哥伦比亚、秘鲁、阿根廷
        "中东/北非",   # 沙特、UAE、埃及、摩洛哥
        "东非",        # 肯尼亚、坦桑尼亚、埃塞俄比亚
        "西非",        # 尼日利亚、加纳、塞内加尔
        "非洲南部",    # 南非、赞比亚、津巴布韦
        "跨区域",      # 多国联合项目
    ]

    
    @classmethod
    def get_prompt_limits(cls):
        """返回prompt中的限制描述"""
        return f"{cls.MIN_REGIONS}-{cls.MAX_REGIONS}个核心区域，每个区域{cls.MIN_TITLES_PER_REGION}-{cls.MAX_TITLES_PER_REGION}条新闻"
