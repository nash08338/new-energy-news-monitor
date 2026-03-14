import feedparser
import os
import csv
import time
import random
from datetime import datetime, timedelta

# ══════════════════════════════════════
#  区域映射库（两个来源共用）
# ══════════════════════════════════════
REGION_MAP = {
    "北非及中东": ["Middle East", "MENA", "Saudi", "UAE", "Dubai", "Oman", "Qatar", "Egypt", "Iraq", "Jordan", "Kuwait", "Morocco", "Algeria", "Tunisia"],
    "南亚":       ["India", "Pakistan", "Bangladesh", "Sri Lanka", "Nepal"],
    "东南亚":     ["Southeast Asia", "ASEAN", "Vietnam", "Thailand", "Indonesia", "Malaysia", "Philippines", "Singapore", "Cambodia"],
    "东亚":       ["East Asia", "China", "Japan", "Korea", "Taiwan", "Mongolia"],
    "西欧":       ["Western Europe", "UK", "Britain", "France", "Germany", "Netherlands", "Belgium", "Switzerland", "Ireland", "Austria"],
    "南欧":       ["Southern Europe", "Spain", "Italy", "Greece", "Portugal", "Turkey"],
    "北欧":       ["Northern Europe", "Nordic", "Sweden", "Norway", "Denmark", "Finland"],
    "东欧":       ["Eastern Europe", "Poland", "Hungary", "Romania", "Ukraine", "Czech"],
    "西非":       ["West Africa", "Nigeria", "Ghana", "Senegal", "Ivory Coast"],
    "东非":       ["East Africa", "Kenya", "Ethiopia", "Tanzania", "Uganda"],
    "非洲南部":   ["Southern Africa", "South Africa", "Namibia", "Zambia", "Zimbabwe"],
    "拉丁美洲":   ["Latin America", "LATAM", "Brazil", "Mexico", "Chile", "Argentina", "Colombia"],
    "北美":       ["North America", "USA", "United States", "Canada"],
    "大洋洲":     ["Oceania", "Australia", "New Zealand", "Fiji"]
}

# ══════════════════════════════════════
#  数据源配置（新增来源在这里加即可）
# ══════════════════════════════════════
DAYS_BACK = 7


SOURCES = [
    {
        "name":    "SolarQuarter",
        "rss":     "https://solarquarter.com/category/news/feed/",
        "history": "solar_history.txt",    # 新文件，不影响原 history.txt
    },
    {
        "name":    "Electrive",
        "rss":     "https://www.electrive.com/category/energy-infrastructure/feed/",
        "history": "electrive_history.txt",
    },
]

CSV_FILE = "docs/news_output.csv"    # 输出到 docs/ 目录，与原报告并列
# ══════════════════════════════════════
#  工具函数
# ══════════════════════════════════════
def load_history(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return set(line.strip() for line in f)
    return set()

def save_history(filepath, url):
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(url + "\n")

def get_region(title):
    matched = []
    for region, keywords in REGION_MAP.items():
        if any(k.lower() in title.lower() for k in keywords):
            matched.append(region)
    if not matched:
        return "全球/其他"
    return matched[0] if len(matched) == 1 else "跨区域"

# ══════════════════════════════════════
#  单个来源抓取
# ══════════════════════════════════════
def fetch_source(source, seven_days_ago):
    name         = source["name"]
    rss_url      = source["rss"]
    history_file = source["history"]
    seen_urls    = load_history(history_file)
    new_data     = []

    print(f"\n{'='*50}")
    print(f"📡 来源：{name}")
    print(f"{'='*50}")

    for page in range(1, 100):
        paged_url = f"{rss_url}?paged={page}" if page > 1 else rss_url
        print(f"  🔍 第 {page} 页：{paged_url}")

        # ✅ 重试机制
        feed = None
        for attempt in range(3):
            feed = feedparser.parse(paged_url)
            if feed.entries:
                break
            print(f"  ⚠️ 第 {attempt+1} 次返回空，等待后重试...")
            time.sleep(random.uniform(3.0, 6.0))

        if not feed or not feed.entries:
            print("  🏁 重试3次仍为空，已到达最后一页。")
            break

        # ✅ 缩进正确，与 for page 同级
        hit_old = False
        for entry in feed.entries:
            link     = entry.link
            pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))

            if pub_date >= seven_days_ago:
                if link not in seen_urls:
                    region = get_region(entry.title)
                    new_data.append([
                        name,
                        region,
                        entry.title,
                        pub_date.strftime('%Y-%m-%d'),
                        link
                    ])
                    seen_urls.add(link)
                    save_history(history_file, link)
            else:
                print(f"  🛑 触达时间边界 ({pub_date.strftime('%Y-%m-%d')})，停止。")
                hit_old = True
                break

        if hit_old:
            break

        time.sleep(random.uniform(1.5, 3.0))

    print(f"  ✅ {name} 本次新增：{len(new_data)} 条")
    return new_data

# ══════════════════════════════════════
#  主程序
# ══════════════════════════════════════
def main():
    seven_days_ago = datetime.now() - timedelta(days=DAYS_BACK)
    seven_days_ago = seven_days_ago.replace(hour=0, minute=0, second=0)

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 启动全球新能源新闻监控")
    print(f"📅 抓取范围：{seven_days_ago.strftime('%Y-%m-%d')} 至今")

    all_new_data = []
    for source in SOURCES:
        data = fetch_source(source, seven_days_ago)
        all_new_data.extend(data)

    if all_new_data:
        all_new_data.sort(key=lambda x: (x[1], x[3]))  # 按区域+日期排序

        file_exists = os.path.isfile(CSV_FILE)
        with open(CSV_FILE, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['来源', '所属区域', '文章标题', '发布日期', '详情链接'])
            writer.writerows(all_new_data)

        print(f"\n🎉 完成！本次共新增 {len(all_new_data)} 条资讯，已保存至 {CSV_FILE}")
    else:
        print("\n☕ 暂无新资讯更新。")

if __name__ == "__main__":
    main()
