import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import zipfile
import concurrent.futures
import feedparser
import os
import csv
import time
import random
import glob
import json
import re
import threading
from zoneinfo import ZoneInfo
from collections import defaultdict
from datetime import datetime, timedelta
from openai import OpenAI
from playwright.sync_api import sync_playwright

# ══════════════════════════════════════
#  时区
# ══════════════════════════════════════
def now_cst():
    return datetime.now(ZoneInfo("Asia/Shanghai"))

# ══════════════════════════════════════
#  区域映射库
# ══════════════════════════════════════
REGION_MAP = {
    "北非及中东": [
        "Middle East", "MENA",
        # 中东
        "Saudi", "Saudi Arabia", "UAE", "United Arab Emirates", "Dubai", "Abu Dhabi",
        "Oman", "Qatar", "Kuwait", "Bahrain", "Yemen", "Iraq", "Jordan", "Lebanon",
        "Syria", "Israel", "Palestine", "Iran",
        # 北非
        "Egypt", "Morocco", "Algeria", "Tunisia", "Libya",
    ],
    "南亚": [
        "India", "Pakistan", "Bangladesh", "Sri Lanka", "Nepal",
        "Bhutan", "Maldives", "Afghanistan",
    ],
    "东南亚": [
        "Southeast Asia", "ASEAN",
        "Vietnam", "Thailand", "Indonesia", "Malaysia", "Philippines",
        "Singapore", "Cambodia", "Myanmar", "Laos", "Brunei", "Timor-Leste",
    ],
    "东亚": [
        "East Asia", "China", "Japan", "Korea", "South Korea", "North Korea",
        "Taiwan", "Mongolia", "Hong Kong", "Macau",
    ],
    "中亚": [
        "Central Asia",
        "Kazakhstan", "Uzbekistan", "Turkmenistan", "Kyrgyzstan", "Tajikistan",
    ],
    "西欧": [
        "Western Europe",
        "UK", "Britain", "England", "Scotland", "Wales",
        "France", "Germany", "Netherlands", "Belgium",
        "Switzerland", "Ireland", "Austria", "Luxembourg",
        "Liechtenstein", "Monaco",
    ],
    "南欧": [
        "Southern Europe",
        "Spain", "Italy", "Greece", "Portugal", "Turkey",
        "Malta", "Cyprus", "Croatia", "Slovenia", "Serbia",
        "Bosnia", "Montenegro", "Albania", "Macedonia", "Kosovo",
    ],
    "北欧": [
        "Northern Europe", "Nordic", "Scandinavia",
        "Sweden", "Norway", "Denmark", "Finland", "Iceland",
        "Estonia", "Latvia", "Lithuania",
    ],
    "东欧": [
        "Eastern Europe",
        "Poland", "Hungary", "Romania", "Ukraine", "Czech",
        "Slovakia", "Bulgaria", "Belarus", "Moldova",
    ],
    "俄罗斯及高加索": [
        "Russia", "Georgia", "Armenia", "Azerbaijan",
    ],
    "拉丁美洲": [
        "Latin America", "LATAM",
        "Brazil", "Mexico", "Chile", "Argentina", "Colombia",
        "Peru", "Venezuela", "Ecuador", "Bolivia", "Paraguay",
        "Uruguay", "Costa Rica", "Panama", "Guatemala", "Honduras",
        "El Salvador", "Nicaragua", "Cuba", "Dominican Republic",
        "Puerto Rico", "Jamaica", "Trinidad",
    ],
    "北美": [
        "North America", "USA", "United States", "Canada",
    ],
    "大洋洲": [
        "Oceania", "Pacific",
        "Australia", "New Zealand", "Fiji", "Papua New Guinea",
        "Solomon Islands", "Vanuatu", "Samoa", "Tonga",
    ],
    "西非": [
        "West Africa",
        "Nigeria", "Ghana", "Senegal", "Ivory Coast", "Cote d'Ivoire",
        "Mali", "Burkina", "Burkina Faso", "Guinea", "Guinea-Bissau",
        "Sierra Leone", "Liberia", "Togo", "Benin", "Niger",
        "Mauritania", "Gambia", "Cape Verde",
    ],
    "东非": [
        "East Africa",
        "Kenya", "Ethiopia", "Tanzania", "Uganda",
        "Rwanda", "Burundi", "Somalia", "Eritrea",
        "Djibouti", "Mozambique", "Madagascar",
        "Comoros", "Seychelles", "Mauritius",
    ],
    "非洲南部": [
        "Southern Africa",
        "South Africa", "Namibia", "Zambia", "Zimbabwe",
        "Botswana", "Lesotho", "Eswatini", "Swaziland",
        "Malawi", "Angola",
    ],
    "中非及北非其他": [
        "Central Africa",
        "Congo", "DRC", "Democratic Republic", "Cameroon",
        "Central African Republic", "Chad", "Gabon",
        "Equatorial Guinea", "Sudan", "South Sudan",
    ],
}

# ══════════════════════════════════════
#  配置区
# ══════════════════════════════════════
DAYS_BACK = 7

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR    = os.path.dirname(BASE_DIR)

DAILY_DIR   = os.path.join(ROOT_DIR, "docs", "daily")
MASTER_FILE = os.path.join(ROOT_DIR, "docs", "news_master.csv")
USED_FILE   = os.path.join(ROOT_DIR, "docs", "used_news.csv")
IMAGE_DIR   = os.path.join(ROOT_DIR, "docs", "images")
CONFLICT_FILE = os.path.join(ROOT_DIR, "docs", "region_conflicts.csv")
XHS_DIR     = os.path.join(ROOT_DIR, "docs", "images", "xhs")
HEADER = ['来源', '所属区域', '文章标题', '发布日期', '详情链接', '抓取日期']

SOURCES = [
    {"name": "SolarQuarter",      "rss": "https://solarquarter.com/category/news/feed/",                   "paged": True},
    {"name": "Electrive",         "rss": "https://www.electrive.com/category/energy-infrastructure/feed/", "paged": True},
    {"name": "PowerTechnology",   "rss": "https://www.power-technology.com/news/feed/",                    "paged": True},
    {"name": "EnergyStorageNews", "rss": "https://www.energy-storage.news/category/news/feed/",            "paged": True},
    {"name": "PVMagazine",        "rss": "https://www.pv-magazine.com/news/feed/",                         "paged": True},
    {"name": "PVTech",            "rss": "https://www.pv-tech.org/feed/",                                  "paged": True},
    {"name": "EnergyCapitalPow",  "rss": "https://energycapitalpower.com/feed/",                           "paged": True},
    {"name": "RenewEconomy",      "rss": "https://reneweconomy.com.au/feed/",                              "paged": True},
    {"name": "EnergyNewsNetwork", "rss": "https://energy-news-network.com/feed/",                          "paged": True},
    {"name": "MercomIndia",       "rss": "https://mercomindia.com/feed/",                                  "paged": False},
    {"name": "RenewablesNow_SSA", "rss": "https://renewablesnow.com/news/news_feed/?region=sub-saharan+africa", "paged": False},
    {"name": "GNews_SouthAfrica", "rss": "https://news.google.com/rss/search?q=south+africa+solar+battery+storage&hl=en-US&gl=US&ceid=US:en", "paged": False},
    {"name": "GNews_WestAfrica",  "rss": "https://news.google.com/rss/search?q=west+africa+solar+energy+storage&hl=en-US&gl=US&ceid=US:en",  "paged": False},
    {"name": "GNews_EastAfrica",  "rss": "https://news.google.com/rss/search?q=east+africa+kenya+solar+storage&hl=en-US&gl=US&ceid=US:en",   "paged": False},
]

# 动态生成 footer 来源字符串
FOOTER_LINE1 = " · ".join(s["name"] for s in SOURCES[:7])   # 前7个一行
FOOTER_LINE2 = " · ".join(s["name"] for s in SOURCES[7:])   # 后7个一行

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
if not DEEPSEEK_API_KEY:
    raise ValueError("DEEPSEEK_API_KEY 未设置，请检查 GitHub Secrets")

client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com",
    timeout=60.0
)

# ══════════════════════════════════════
#  工具函数
# ══════════════════════════════════════
def get_region(title):
    matched = []
    for region, keywords in REGION_MAP.items():
        if any(k.lower() in title.lower() for k in keywords):
            matched.append(region)
    if not matched:
        return "全球/其他"
    return matched[0] if len(matched) == 1 else "跨区域"

def safe_slug(region):
    """区域名转文件名安全字符串，过滤所有特殊字符"""
    return re.sub(r'[\\/:*?"<>|]', '_', region).replace(" ", "_")

def load_used_links():
    used = set()
    if os.path.exists(USED_FILE):
        with open(USED_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader, None)
            for r in reader:
                if r:
                    used.add(r[0])
    return used

def save_used_links(links):
    # 先读取已有链接
    existing = set()
    if os.path.exists(USED_FILE):
        with open(USED_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader, None)
            for r in reader:
                if r:
                    existing.add(r[0])

    # 只写入不存在的链接
    new_links = [l for l in links if l not in existing]
    if not new_links:
        print("  ℹ️ 无新链接需要写入 used_news")
        return

    file_exists = os.path.exists(USED_FILE)
    with open(USED_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["详情链接", "使用日期"])
        for link in new_links:
            writer.writerow([link, now_cst().strftime("%Y-%m-%d")])

    print(f"  ✅ 写入 {len(new_links)} 条到 used_news（跳过 {len(links)-len(new_links)} 条重复）")

def load_unused_news(max_count=150):   # ← 新增 max_count 参数
    if not os.path.exists(MASTER_FILE):
        print("  ⚠️ 总表不存在，跳过")
        return []

    used_links = load_used_links()
    unused = []
    with open(MASTER_FILE, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader, None)
        for r in reader:
            if len(r) >= 5 and r[4] not in used_links:
                unused.append(r)

    total = len(unused)

    # 总表已按日期降序，直接取前 max_count 条（最新的）
    if total > max_count:
        unused = unused[:max_count]
        print(f"  📰 未使用新闻：{total} 条，取最新 {max_count} 条传给 DeepSeek")
    else:
        print(f"  📰 未使用新闻：{total} 条")

    if len(unused) < 8:
        print(f"  ⚠️ 未使用新闻不足8条，建议增加抓取频率或扩大 DAYS_BACK")

    return unused
def match_used_links_by_title(unused_news, data):
    """标题反查兜底：中文标题关键词匹配原始英文标题"""
    selected_titles = []
    for sec in data.get("news_sections", []):
        selected_titles.extend(sec.get("titles", []))

    used_links = []
    for title in selected_titles:
        keywords = [w for w in title[:20].split() if len(w) > 1]
        for row in unused_news:
            original = row[2].lower()
            if any(kw.lower() in original for kw in keywords):
                if row[4] not in used_links:
                    used_links.append(row[4])
                break
    return used_links

# ══════════════════════════════════════
#  核心抓取函数
# ══════════════════════════════════════
def fetch_source(source, seven_days_ago, seen_urls):
    name           = source["name"]
    rss_url        = source["rss"]
    supports_paged = source.get("paged", True)
    new_data       = []
    today_str      = now_cst().strftime('%Y-%m-%d')   # ← 抓取日期

    print(f"\n{'='*50}\n📡 来源：{name}\n{'='*50}")

    for page in range(1, 100):
        if page > 1 and not supports_paged:
            break

        paged_url = f"{rss_url}?paged={page}" if page > 1 else rss_url
        print(f"  🔍 第 {page} 页：{paged_url}")

        feed = None
        for attempt in range(3):
            try:
                feed = feedparser.parse(
                    paged_url,
                    agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
                )
                if hasattr(feed, 'status') and feed.status in (301, 302) and feed.get("href"):
                    feed = feedparser.parse(
                        feed.href,
                        agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                              "AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
                    )
                if feed.entries:
                    break
            except Exception as e:
                print(f"  ⚠️ 第 {attempt+1} 次请求异常：{e}")
                feed = None
            print(f"  ⚠️ 第 {attempt+1} 次返回空，等待后重试...")
            time.sleep(random.uniform(3.0, 6.0))

        if not feed or not feed.entries:
            print("  🏁 重试3次仍为空，停止。")
            break

        hit_old = False
        for entry in feed.entries:
            link = entry.link
            try:
                pub_date = datetime.fromtimestamp(
                    time.mktime(entry.published_parsed),
                    tz=ZoneInfo("Asia/Shanghai")
                )
            except Exception:
                continue

            if pub_date >= seven_days_ago:
                if link not in seen_urls:
                    new_data.append([
                        name,
                        get_region(entry.title),
                        entry.title,
                        pub_date.strftime('%Y-%m-%d'),
                        link,
                        today_str,              # ← 抓取日期（第6列）
                    ])
                    seen_urls.add(link)
            else:
                print(f"  🛑 触达时间边界 ({pub_date.strftime('%Y-%m-%d')})，停止。")
                hit_old = True
                break

        if hit_old:
            break
        time.sleep(random.uniform(1.5, 3.0))

    print(f"  ✅ {name} 本次新增：{len(new_data)} 条")
    return new_data

def cross_validate_regions(unused_news, data):
    """
    交叉验证：对比 get_region 预判 vs DeepSeek 归类的区域
    若 ref_region 有明确判断但完全不在 DeepSeek 任何区域里，记录为冲突
    """
    conflicts  = []
    index_map  = {i + 1: row for i, row in enumerate(unused_news)}
    used_indices = data.get("used_indices", [])

    # 收集本次 DeepSeek 所有出现的区域
    all_ds_regions = {sec.get("region", "") for sec in data.get("news_sections", [])}

    for idx in used_indices:
        if idx not in index_map:
            continue
        original_row   = index_map[idx]
        ref_region     = original_row[1]
        original_title = original_row[2]

        # 全球/其他 和 跨区域 本来就不确定，跳过
        if ref_region in ("全球/其他", "跨区域"):
            continue

        # ref_region 有明确判断，但完全不在 DeepSeek 的任何区域里
        if ref_region not in all_ds_regions:
            conflicts.append({
                "index":          idx,
                "original_title": original_title,
                "ref_region":     ref_region,
                "ds_region":      "未归入任何区域",
                "date":           original_row[3],
            })

    if conflicts:
        file_exists = os.path.exists(CONFLICT_FILE)
        with open(CONFLICT_FILE, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "index", "original_title", "ref_region", "ds_region", "date"
            ])
            if not file_exists:
                writer.writeheader()
            writer.writerows(conflicts)
        print(f"  ⚠️  区域不一致：{len(conflicts)} 条 → {CONFLICT_FILE}")
    else:
        print("  ✅ 区域交叉验证通过，无冲突")

    return conflicts
# ══════════════════════════════════════
#  CSV 处理函数
# ══════════════════════════════════════
def split_by_date(all_new_data):
    os.makedirs(DAILY_DIR, exist_ok=True)
    grouped = defaultdict(list)
    for row in all_new_data:
        grouped[row[3]].append(row)
    written_files = [] 
    for date_str, rows in grouped.items():
        daily_file = os.path.join(DAILY_DIR, f"news_{date_str}.csv")
        existing_links = set()
        if os.path.isfile(daily_file):
            with open(daily_file, "r", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                next(reader, None)
                for r in reader:
                    if len(r) >= 5:
                        existing_links.add(r[4])

        new_rows = [r for r in rows if r[4] not in existing_links]
        if not new_rows:
            continue

        file_exists = os.path.isfile(daily_file)
        with open(daily_file, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(HEADER)
            writer.writerows(new_rows)
            
        written_files.append(daily_file)   # ← 记录
        print(f"  📅 {date_str}：新增 {len(new_rows)} 条 → {daily_file}")
        
    return written_files   # ← 返回
    
def merge_to_master(daily_files):   # ← 接收参数
    if not daily_files:
        return

    existing_links = set()
    if os.path.exists(MASTER_FILE):
        with open(MASTER_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader, None)
            for r in reader:
                if len(r) >= 5:
                    existing_links.add(r[4])

    new_rows = []
    for f in daily_files:   # ← 只扫本次文件
        try:
            with open(f, "r", encoding="utf-8-sig") as fh:
                reader = csv.reader(fh)
                next(reader, None)
                for r in reader:
                    if len(r) >= 5 and r[4] not in existing_links:
                        new_rows.append(r)
                        existing_links.add(r[4])
        except Exception as e:
            print(f"  ⚠️ 读取 {f} 失败：{e}")

    if not new_rows:
        print("📋 总表无新增内容。")
        return

    file_exists = os.path.exists(MASTER_FILE)
    with open(MASTER_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(HEADER)
        writer.writerows(new_rows)

    all_rows = []
    with open(MASTER_FILE, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader, None)
        seen = set()
        for r in reader:
            if len(r) >= 5 and r[4] not in seen:
                all_rows.append(r)
                seen.add(r[4])

    all_rows.sort(key=lambda x: x[3], reverse=True)
    with open(MASTER_FILE, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        writer.writerows(all_rows)

    print(f"📋 总表已更新，新增 {len(new_rows)} 条，共 {len(all_rows)} 条")

# ══════════════════════════════════════
#  DeepSeek 调用（编号优先 + 标题反查兜底）
# ══════════════════════════════════════
def call_deepseek(unused_news):
    if not unused_news:
        print("  ⚠️ 没有未使用的新闻，跳过生成图片")
        return None, []

    print(f"\n🤖 调用 DeepSeek，从 {len(unused_news)} 条未使用新闻中筛选...")
    today_str = now_cst().strftime("%Y年%m月%d日")
    news_text = "\n".join(
        f"{i+1}. [ref_region:{r[1]}] {r[2]} ({r[3]})"
        for i, r in enumerate(unused_news)
    )
    prompt = f"""
# Role
你是一名资深的全球新能源行业分析师，深度聚焦于"光储充"一体化及智能电网领域。

# Task
对下方原始新闻标题进行筛选、翻译和润色，生成专业"行业内参"。

# Requirements
1. 仅保留【光伏、储能、充电桩、微电网、电力/电网/能源转型】相关内容
2. 彻底剔除【风能、氢能、生物质能、核能】
3. 精选 8-10 条，若实际不够则按实际数量精选，按区域归类，
    ref_region 是系统预判的参考区域，你需要根据新闻语义自行判断，
    判断依据是新闻涉及的目标市场，而非公司国籍，可以覆盖 ref_region。
4. 所有标题必须翻译成中文，术语专业准确（工商业储能、并网政策、户用光伏等）
5. 每个区域给出一条出海机遇或准入门槛的专业点评（中性）
6. used_indices 必须返回你选中新闻对应的编号，编号来自新闻列表前的序号，此字段为必填
7. 同一条新闻只能出现在一个区域，严禁在不同区域重复出现同一内容
# Output
只返回 JSON 本身，不要任何多余文字或 markdown：
{{
  "date": "{today_str}",
  "daily_focus": "今日核心关注点的专业分析",
  "news_sections": [
    {{
      "region": "区域名称",
      "market_insight": "该区域光储充市场研判",
      "titles": ["标题1", "标题2"]
    }}
  ],
  "used_indices": [1, 3, 5, 8, 12]
}}

# 新闻列表
{news_text}
"""

    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            raw = resp.choices[0].message.content.strip()

            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            data = json.loads(raw)
            assert "news_sections" in data and len(data["news_sections"]) > 0, "缺少 news_sections"
            assert "daily_focus"   in data, "缺少 daily_focus"
            # ── 新增：跨区域标题去重 ──
            seen_titles = set()
            for sec in data["news_sections"]:
                unique_titles = []
                for title in sec.get("titles", []):
                    # 用前15个字符做去重 key，避免轻微措辞差异导致漏判
                    key = title[:15].strip()
                    if key not in seen_titles:
                        seen_titles.add(key)
                        unique_titles.append(title)
                sec["titles"] = unique_titles
            
            # 去掉去重后 titles 为空的区域
            data["news_sections"] = [
                sec for sec in data["news_sections"]
                if sec.get("titles")
            ]

            # 方式一：编号直接取链接（精准）
            used_links = []
            indices = data.get("used_indices", [])
            if indices:
                for idx in indices:
                    pos = idx - 1
                    if 0 <= pos < len(unused_news):
                        link = unused_news[pos][4]
                        if link not in used_links:
                            used_links.append(link)
                print(f"  ✅ 第{attempt+1}次调用成功，编号匹配：标记 {len(used_links)} 条")

            # 方式二：编号为空或数量明显不足，启用标题反查兜底
            total_titles = sum(len(sec.get("titles", [])) for sec in data["news_sections"])
            if not used_links or len(used_links) < max(1, total_titles // 2):
                print("  ⚠️ 编号匹配不足，启用标题反查兜底...")
                fallback_links = match_used_links_by_title(unused_news, data)
                for link in fallback_links:
                    if link not in used_links:
                        used_links.append(link)
                print(f"  ✅ 兜底后共标记 {len(used_links)} 条")
            # 交叉验证区域（不影响任何返回值和流程）
            if used_links:
                cross_validate_regions(unused_news, data)
            return data, used_links
        
        except json.JSONDecodeError as e:
            print(f"  ⚠️ 第{attempt+1}次 JSON 解析失败：{e}")
            print(f"  原始返回内容：{raw[:200]}")   # ← 加这行
        except AssertionError as e:
            print(f"  ⚠️ 第{attempt+1}次字段校验失败：{e}")
        except Exception as e:
            print(f"  ⚠️ 第{attempt+1}次调用异常：{type(e).__name__}: {e}")  # ← 加类型

        if attempt < 2:
            print("  🔄 等待重试...")
            time.sleep(5)

    print("  ❌ DeepSeek 连续3次失败，跳过图片生成")
    return None, []

# ══════════════════════════════════════
#  HTML 模板
# ══════════════════════════════════════
def render_overview_html(data):
    sections_html = ""
    for sec in data["news_sections"]:
        titles_html = "".join(f"<li>{t}</li>" for t in sec["titles"])
        sections_html += f"""
        <div class="section">
          <div class="region-header">
            <span class="region-tag">{sec['region']}</span>
          </div>
          <div class="insight">💡 {sec['market_insight']}</div>
          <ul class="news-list">{titles_html}</ul>
        </div>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;
          background:#F0F4F8; width:820px; padding:28px; }}
  .card {{ background:white; border-radius:16px; overflow:hidden;
           box-shadow:0 2px 12px rgba(0,0,0,0.08); position:relative; }}
  .header {{ background:linear-gradient(135deg,#1a1a2e,#0f3460); padding:24px 28px; }}
  .header-top {{ display:flex; justify-content:space-between;
                 align-items:center; margin-bottom:12px; }}
  .header h1 {{ color:white; font-size:20px; font-weight:600; }}
  .date {{ color:#94a3b8; font-size:13px; }}
  .focus-box {{ background:rgba(255,255,255,0.07); border-radius:10px;
                padding:14px 16px; border-left:3px solid #38bdf8; }}
  .focus-box p {{ color:#e2e8f0; font-size:13px; line-height:1.7; }}
  .body {{ padding:20px 28px; }}
  .section {{ border-bottom:1px solid #f1f5f9; padding:16px 0; }}
  .section:last-child {{ border-bottom:none; }}
  .region-tag {{ background:#0f3460; color:white; font-size:12px;
                 padding:3px 12px; border-radius:20px; font-weight:500; }}
  .insight {{ font-size:12px; color:#0369a1; background:#f0f9ff;
              border-radius:6px; padding:8px 12px; margin:8px 0 10px;
              border-left:3px solid #38bdf8; line-height:1.6; }}
  .news-list {{ padding-left:16px; }}
  .news-list li {{ font-size:13px; color:#334155; line-height:1.8; }}
  .footer {{ text-align:center; padding:14px; font-size:11px;
             color:#94a3b8; background:#f8fafc; border-top:1px solid #f1f5f9; }}
</style></head><body>
<div class="card">
  <div class="header">
    <div class="header-top">
      <h1>⚡ 光储电桩通 · 全球情报</h1>
      <span class="date">{data['date']}</span>
    </div>
    <div class="focus-box"><p>{data['daily_focus']}</p></div>
  </div>
  <div class="body">{sections_html}</div>
  <div class="footer">
    <span style="float:left;">Data Sources: {FOOTER_LINE1}<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{FOOTER_LINE2}</span>
    <span style="float:right;font-size:11px;color:rgba(0,0,0,0.40);
                 font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;">Created by 香港汇展 Nash</span>
  </div>
</div></body></html>"""

def render_overview_xhs_html(data):
    sections_html = ""
    for sec in data["news_sections"]:
        titles_html = "".join(f"<li>{t}</li>" for t in sec["titles"])
        sections_html += f"""
        <div class="section">
          <div class="region-header">
            <span class="region-tag">{sec['region']}</span>
          </div>
          <div class="insight">💡 {sec['market_insight']}</div>
          <ul class="news-list">{titles_html}</ul>
        </div>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;
          background:#F0F4F8; width:1242px; padding:48px; }}
  .card {{ background:white; border-radius:24px; overflow:hidden;
           box-shadow:0 4px 24px rgba(0,0,0,0.08); position:relative; }}
  .header {{ background:linear-gradient(135deg,#1a1a2e,#0f3460); padding:40px 48px; }}
  .header-top {{ display:flex; justify-content:space-between;
                 align-items:center; margin-bottom:20px; }}
  .header h1 {{ color:white; font-size:32px; font-weight:600; }}
  .date {{ color:#94a3b8; font-size:20px; }}
  .focus-box {{ background:rgba(255,255,255,0.07); border-radius:14px;
                padding:20px 24px; border-left:4px solid #38bdf8; }}
  .focus-box p {{ color:#e2e8f0; font-size:20px; line-height:1.8; }}
  .body {{ padding:32px 48px; }}
  .section {{ border-bottom:1px solid #f1f5f9; padding:24px 0; }}
  .section:last-child {{ border-bottom:none; }}
  .region-tag {{ background:#0f3460; color:white; font-size:18px;
                 padding:5px 18px; border-radius:30px; font-weight:500; }}
  .insight {{ font-size:18px; color:#0369a1; background:#f0f9ff;
              border-radius:10px; padding:14px 18px; margin:12px 0 16px;
              border-left:4px solid #38bdf8; line-height:1.7; }}
  .news-list {{ padding-left:24px; }}
  .news-list li {{ font-size:19px; color:#334155; line-height:1.9; margin-bottom:4px; }}
  .footer {{ text-align:center; padding:20px; font-size:13px;
             color:#94a3b8; background:#f8fafc; border-top:1px solid #f1f5f9; }}
</style></head><body>
<div class="card">
  <div class="header">
    <div class="header-top">
      <h1>⚡ 光储电桩通 · 全球情报</h1>
      <span class="date">{data['date']}</span>
    </div>
    <div class="focus-box"><p>{data['daily_focus']}</p></div>
  </div>
  <div class="body">{sections_html}</div>
  <div class="footer">
    <span style="float:left;">Data Sources: {FOOTER_LINE1}<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{FOOTER_LINE2}</span>
    <span style="float:right;font-size:11px;color:rgba(0,0,0,0.40);
                 font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;">Created by 香港汇展 Nash</span>
  </div>
</div></body></html>"""

def render_region_html(sec, date_str):
    color_map = {
        "北非及中东":"#b45309","南亚":"#15803d","东南亚":"#0e7490",
        "东亚":"#1d4ed8","西欧":"#6d28d9","南欧":"#be185d",
        "北欧":"#0369a1","东欧":"#4d7c0f","北美":"#7c2d12",
        "拉丁美洲":"#065f46","大洋洲":"#1e40af",
        "西非":    "#92400e",
        "东非":    "#065f46",
        "非洲南部":"#1e3a5f",
    }
    accent      = color_map.get(sec["region"], "#0f3460")
    titles_html = "".join(f"<li>{t}</li>" for t in sec["titles"])

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;
          background:#F0F4F8; width:820px; padding:28px; }}
  .card {{ background:white; border-radius:16px; overflow:hidden;
           box-shadow:0 2px 12px rgba(0,0,0,0.08); position:relative; }}
  .header {{ background:{accent}; padding:22px 28px;
             display:flex; justify-content:space-between; align-items:flex-start; }}
  .header-left h1 {{ color:white; font-size:19px; font-weight:600; }}
  .header-right   {{ color:rgba(255,255,255,0.6); font-size:12px; }}
  .body {{ padding:22px 28px; }}
  .insight {{ font-size:13px; color:{accent}; background:#f8fafc;
              border-radius:8px; padding:12px 16px; margin-bottom:18px;
              border-left:4px solid {accent}; line-height:1.7; }}
  .news-title {{ font-size:13px; color:#64748b; margin-bottom:10px; font-weight:500; }}
  .news-list {{ padding-left:18px; }}
  .news-list li {{ font-size:14px; color:#1e293b; line-height:1.9; margin-bottom:4px; }}
  .footer {{ text-align:center; padding:12px; font-size:11px;
             color:#94a3b8; background:#f8fafc; border-top:1px solid #f1f5f9; }}
</style></head><body>
<div class="card">
  <div class="header">
    <div class="header-left">
      <h1>⚡ {sec['region']} · 光储电桩市场动态</h1>
    </div>
    <div class="header-right">{date_str}</div>
  </div>
  <div class="body">
    <div class="insight">💡 市场研判：{sec['market_insight']}</div>
    <div class="news-title">本期精选资讯</div>
    <ul class="news-list">{titles_html}</ul>
  </div>
  <div class="footer">
    <span style="float:left;">Data Sources: {FOOTER_LINE1}<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{FOOTER_LINE2}</span>
    <span style="float:right;font-size:11px;color:rgba(0,0,0,0.40);
                 font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;">Created by 香港汇展 Nash</span>
  </div>
</div></body></html>"""

def render_region_xhs_html(sec, date_str):
    color_map = {
        "北非及中东":"#b45309","南亚":"#15803d","东南亚":"#0e7490",
        "东亚":"#1d4ed8","西欧":"#6d28d9","南欧":"#be185d",
        "北欧":"#0369a1","东欧":"#4d7c0f","北美":"#7c2d12",
        "拉丁美洲":"#065f46","大洋洲":"#1e40af",
    }
    accent      = color_map.get(sec["region"], "#0f3460")
    titles_html = "".join(f"<li>{t}</li>" for t in sec["titles"])

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;
          background:#F0F4F8; width:1242px; padding:48px; }}
  .card {{ background:white; border-radius:24px; overflow:hidden;
           box-shadow:0 4px 24px rgba(0,0,0,0.08); position:relative; }}
  .header {{ background:{accent}; padding:40px 48px;
             display:flex; justify-content:space-between; align-items:flex-start; }}
  .header-left h1 {{ color:white; font-size:30px; font-weight:600; }}
  .header-right   {{ color:rgba(255,255,255,0.6); font-size:20px; }}
  .body {{ padding:36px 48px; }}
  .insight {{ font-size:20px; color:{accent}; background:#f8fafc;
              border-radius:12px; padding:20px 24px; margin-bottom:28px;
              border-left:6px solid {accent}; line-height:1.8; }}
  .news-title {{ font-size:20px; color:#64748b; margin-bottom:16px; font-weight:500; }}
  .news-list {{ padding-left:28px; }}
  .news-list li {{ font-size:21px; color:#1e293b; line-height:2.0; margin-bottom:8px; }}
  .footer {{ text-align:center; padding:20px; font-size:13px;
             color:#94a3b8; background:#f8fafc; border-top:1px solid #f1f5f9; }}

</style></head><body>
<div class="card">
  <div class="header">
    <div class="header-left">
      <h1>⚡ {sec['region']} · 光储电桩市场动态</h1>
    </div>
    <div class="header-right">{date_str}</div>
  </div>
  <div class="body">
    <div class="insight">💡 市场研判：{sec['market_insight']}</div>
    <div class="news-title">本期精选资讯</div>
    <ul class="news-list">{titles_html}</ul>
  </div>
  <div class="footer">
    <span style="float:left;">Data Sources: {FOOTER_LINE1}<br>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;{FOOTER_LINE2}</span>
    <span style="float:right;font-size:11px;color:rgba(0,0,0,0.40);
                 font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;">Created by 香港汇展 Nash</span>
  </div>
</div></body></html>"""

# ══════════════════════════════════════
#  截图函数（普通版，2x 高清）
# ══════════════════════════════════════
def html_to_image(html_content, output_path):
    result = {"error": None}

    def run():
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                page = browser.new_page(
                    viewport={"width": 876, "height": 1200},
                    device_scale_factor=2
                )
                page.set_content(html_content, wait_until="networkidle")
                height = page.evaluate("document.querySelector('.card').scrollHeight + 56")
                page.set_viewport_size({"width": 876, "height": int(height)})
                page.locator(".card").screenshot(path=output_path)
                browser.close()
        except Exception as e:
            result["error"] = e

    t = threading.Thread(target=run)
    t.start()
    t.join()

    if result["error"]:
        raise result["error"]

    print(f"  🖼️  已生成：{output_path}")

# ══════════════════════════════════════
#  截图函数（小红书版，2x 高清竖图）
# ══════════════════════════════════════
def html_to_image_xhs(html_content, output_path):
    result = {"error": None}

    def run():
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                page = browser.new_page(
                    viewport={"width": 1242, "height": 1660},
                    device_scale_factor=2
                )
                page.set_content(html_content, wait_until="networkidle")
                height = page.evaluate("document.querySelector('.card').scrollHeight + 96")
                page.set_viewport_size({"width": 1242, "height": int(height)})
                page.locator(".card").screenshot(path=output_path)
                browser.close()
        except Exception as e:
            result["error"] = e

    t = threading.Thread(target=run)
    t.start()
    t.join()

    if result["error"]:
        raise result["error"]

    print(f"  📱 已生成（小红书）：{output_path}")

# ══════════════════════════════════════
#  生成图片入口
# ══════════════════════════════════════
def generate_images():


    os.makedirs(IMAGE_DIR, exist_ok=True)
    os.makedirs(XHS_DIR, exist_ok=True)
    date_str = now_cst().strftime("%Y-%m-%d")

    unused_news = load_unused_news()
    print(f"DEBUG: unused_news 数量 = {len(unused_news)}")

    data, used_links = call_deepseek(unused_news)

    if not data:
        print("⚠️ 无可用新闻，跳过图片生成。")
        return

    # ── 构建截图任务 ──
    tasks = [
        (render_overview_html(data),
         os.path.join(IMAGE_DIR, f"overview_{date_str}.png"),
         False),
        (render_overview_xhs_html(data),
         os.path.join(XHS_DIR, f"overview_xhs_{date_str}.png"),
         True),
    ]

    region_images     = []   # 普通版区域图路径
    xhs_region_images = []   # 小红书版区域图路径

    for sec in data["news_sections"]:
        slug       = safe_slug(sec["region"])
        region_img = os.path.join(IMAGE_DIR, f"region_{slug}_{date_str}.png")
        region_xhs = os.path.join(XHS_DIR,   f"region_{slug}_xhs_{date_str}.png")

        tasks.append((render_region_html(sec, data["date"]),     region_img, False))
        tasks.append((render_region_xhs_html(sec, data["date"]), region_xhs, True))

        region_images.append(region_img)
        xhs_region_images.append(region_xhs)

    # ── 并发截图 ──
    def take_shot(task):
        html_content, output_path, is_xhs = task
        if is_xhs:
            html_to_image_xhs(html_content, output_path)
        else:
            html_to_image(html_content, output_path)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(take_shot, t) for t in tasks]
        for f in concurrent.futures.as_completed(futures):
            try:
                f.result()
            except Exception as e:
                print(f"  ⚠️ 截图失败：{e}")

    # ── 标记已用新闻 ──
    if used_links:
        save_used_links(used_links)
        print(f"  ✅ 已标记 {len(used_links)} 条新闻为已使用")

    # ── 打包普通版区域图 ──
    zip_region = os.path.join(IMAGE_DIR, f"regions_{date_str}.zip")
    with zipfile.ZipFile(zip_region, "w", zipfile.ZIP_DEFLATED) as zf:
        for img_path in region_images:
            if os.path.exists(img_path):
                zf.write(img_path, os.path.basename(img_path))
    print(f"  📦 普通版区域图已打包：{zip_region}（共 {len(region_images)} 张）")

    # ── 打包小红书版区域图 ──
    zip_xhs = os.path.join(XHS_DIR, f"regions_xhs_{date_str}.zip")
    with zipfile.ZipFile(zip_xhs, "w", zipfile.ZIP_DEFLATED) as zf:
        for img_path in xhs_region_images:
            if os.path.exists(img_path):
                zf.write(img_path, os.path.basename(img_path))
    print(f"  📦 小红书版区域图已打包：{zip_xhs}（共 {len(xhs_region_images)} 张）")

    # ── 删除散装区域图，只保留总图和压缩包 ──
    for img_path in region_images + xhs_region_images:
        if os.path.exists(img_path):
            os.remove(img_path)
    print("  🗑️  散装区域图已清理")

    print(f"\n📁 普通版总图：{os.path.join(IMAGE_DIR, f'overview_{date_str}.png')}")
    print(f"📦 普通版区域包：{zip_region}")
    print(f"📁 小红书版总图：{os.path.join(XHS_DIR, f'overview_xhs_{date_str}.png')}")
    print(f"📦 小红书版区域包：{zip_xhs}")

# ══════════════════════════════════════
#  主程序
# ══════════════════════════════════════
def main():
    seven_days_ago = now_cst() - timedelta(days=DAYS_BACK)
    seven_days_ago = seven_days_ago.replace(hour=0, minute=0, second=0)  # 修复：不重复设置 tzinfo

    print(f"[{now_cst().strftime('%Y-%m-%d %H:%M:%S')}] 启动全球新能源新闻监控（北京时间）")
    print(f"📅 抓取范围：{seven_days_ago.strftime('%Y-%m-%d')} 至今")

    seen_urls = set()
    if os.path.exists(MASTER_FILE):
        with open(MASTER_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader, None)
            for r in reader:
                if len(r) >= 5:
                    seen_urls.add(r[4])
    print(f"📋 总表已有记录：{len(seen_urls)} 条，用于去重")

    all_new_data = []
    for source in SOURCES:
        all_new_data.extend(fetch_source(source, seven_days_ago, seen_urls))

    if all_new_data:
        all_new_data.sort(key=lambda x: x[3], reverse=True)
        written_files = split_by_date(all_new_data)   # ← 接收返回值
        merge_to_master(written_files)                 # ← 传入
        print(f"  🎉 本次新增 {len(all_new_data)} 条新闻入库")
    else:
        print("☕ 本次无新增新闻。")

    generate_images()

    print(f"\n✅ 全部完成！")

if __name__ == "__main__":
    main()
