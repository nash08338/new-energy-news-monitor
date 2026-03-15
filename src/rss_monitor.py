import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import feedparser
import os
import csv
import time
import random
import glob
import json
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
#  配置区
# ══════════════════════════════════════
DAYS_BACK = 7

BASE_DIR    = os.path.dirname(os.path.abspath(__file__))  # src/rss_monitor.py 所在目录
ROOT_DIR    = os.path.dirname(BASE_DIR)                   # 项目根目录

DAILY_DIR   = os.path.join(ROOT_DIR, "docs", "daily")
MASTER_FILE = os.path.join(ROOT_DIR, "docs", "news_master.csv")
USED_FILE   = os.path.join(ROOT_DIR, "docs", "used_news.csv")
IMAGE_DIR   = os.path.join(ROOT_DIR, "docs", "images")
HEADER      = ['来源', '所属区域', '文章标题', '发布日期', '详情链接']

SOURCES = [
    {"name": "SolarQuarter",      "rss": "https://solarquarter.com/category/news/feed/"},
    {"name": "Electrive",         "rss": "https://www.electrive.com/category/energy-infrastructure/feed/"},
    {"name": "PowerTechnology",   "rss": "https://www.power-technology.com/news/feed/"},
    {"name": "EnergyStorageNews", "rss": "https://www.energy-storage.news/category/news/feed/"},
    {"name": "PVMagazine",        "rss": "https://www.pv-magazine.com/news/feed/"},
]

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

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
    file_exists = os.path.exists(USED_FILE)
    with open(USED_FILE, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["详情链接", "使用日期"])
        for link in links:
            writer.writerow([link, now_cst().strftime("%Y-%m-%d")])

def load_unused_news():
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

    print(f"  📰 未使用新闻：{len(unused)} 条")
    if len(unused) < 8:
        print(f"  ⚠️ 未使用新闻不足8条，建议增加抓取频率或扩大 DAYS_BACK")
    return unused

def match_used_links(unused_news, data):
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
    name, rss_url = source["name"], source["rss"]
    new_data = []

    print(f"\n{'='*50}\n📡 来源：{name}\n{'='*50}")

    for page in range(1, 100):
        paged_url = f"{rss_url}?paged={page}" if page > 1 else rss_url
        print(f"  🔍 第 {page} 页：{paged_url}")

        feed = None
        for attempt in range(3):
            feed = feedparser.parse(
                paged_url,
                agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
            )
            if hasattr(feed, 'status') and feed.status in (301, 302) and feed.get("href"):
                feed = feedparser.parse(
                    feed.href,
                    agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
                )
            if feed.entries:
                break
            print(f"  ⚠️ 第 {attempt+1} 次返回空，等待后重试...")
            time.sleep(random.uniform(3.0, 6.0))

        if not feed or not feed.entries:
            print("  🏁 重试3次仍为空，停止。")
            break

        hit_old = False
        for entry in feed.entries:
            link = entry.link
            try:
                pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
            except Exception:
                continue

            if pub_date >= seven_days_ago:
                if link not in seen_urls:
                    new_data.append([
                        name, get_region(entry.title),
                        entry.title, pub_date.strftime('%Y-%m-%d'), link
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

# ══════════════════════════════════════
#  CSV 处理函数
# ══════════════════════════════════════
def split_by_date(all_new_data):
    os.makedirs(DAILY_DIR, exist_ok=True)
    grouped = defaultdict(list)
    for row in all_new_data:
        grouped[row[3]].append(row)

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
        print(f"  📅 {date_str}：新增 {len(new_rows)} 条 → {daily_file}")

def merge_to_master():
    all_files = sorted(glob.glob(os.path.join(DAILY_DIR, "news_*.csv")))
    if not all_files:
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
    for f in all_files:
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
#  DeepSeek 调用（含重试 + 字段校验）
# ══════════════════════════════════════
def call_deepseek(unused_news):
    if not unused_news:
        print("  ⚠️ 没有未使用的新闻，跳过生成图片")
        return None, []

    print(f"\n🤖 调用 DeepSeek，从 {len(unused_news)} 条未使用新闻中筛选...")
    today_str = now_cst().strftime("%Y年%m月%d日")
    news_text = "\n".join(
        f"{i+1}. [{r[1]}] {r[2]} ({r[3]})"
        for i, r in enumerate(unused_news)
    )

    prompt = f"""
# Role
你是一名资深的全球新能源行业分析师，深度聚焦于"光储充"一体化及智能电网领域。

# Task
对下方原始新闻标题进行筛选和润色，生成专业"行业内参"。

# Requirements
1. 仅保留【光伏、储能、充电桩、微电网、电力/电网/能源转型】相关内容
2. 彻底剔除【风能、氢能、生物质能、核能】
3. 精选 8-10 条，若实际不够则按实际数量精选，按区域归类
4. 术语专业准确（工商业储能、并网政策、户用光伏等）
5. 每个区域给出一条出海机遇或准入门槛的专业点评（中性）

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
  ]
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
            assert "news_sections" in data, "缺少 news_sections"
            assert "daily_focus"   in data, "缺少 daily_focus"
            assert len(data["news_sections"]) > 0, "news_sections 为空"

            used_links = match_used_links(unused_news, data)
            print(f"  ✅ 第{attempt+1}次调用成功，匹配到 {len(used_links)} 条已用链接")
            return data, used_links

        except json.JSONDecodeError as e:
            print(f"  ⚠️ 第{attempt+1}次 JSON 解析失败：{e}")
        except AssertionError as e:
            print(f"  ⚠️ 第{attempt+1}次字段校验失败：{e}")
        except Exception as e:
            print(f"  ⚠️ 第{attempt+1}次调用异常：{e}")

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
  <div class="footer">SolarQuarter · PV Magazine · Energy Storage News · Power Technology · Electrive</div>
  <div style="position:absolute;bottom:18px;right:22px;font-size:11px;
              color:rgba(0,0,0,0.12);
              font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;
              letter-spacing:0.5px;user-select:none;">Created by 香港汇展 Nash</div>
</div></body></html>"""

def render_region_html(sec, date_str, daily_focus):
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
  .focus-box {{ margin-top:20px; background:#f8fafc; border-radius:8px;
                padding:12px 16px; border-top:1px solid #e2e8f0; }}
  .focus-box p {{ font-size:12px; color:#64748b; line-height:1.6; }}
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
    <div class="focus-box"><p>📌 今日关注：{daily_focus}</p></div>
  </div>
  <div class="footer">SolarQuarter · PV Magazine · Energy Storage News · Power Technology · Electrive</div>
  <div style="position:absolute;bottom:18px;right:22px;font-size:11px;
              color:rgba(0,0,0,0.12);
              font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;
              letter-spacing:0.5px;user-select:none;">Created by 香港汇展 Nash </div>
</div></body></html>"""

# ══════════════════════════════════════
#  截图函数
# ══════════════════════════════════════
def html_to_image(html_content, output_path):
    result = {"error": None}

    def run():
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                page = browser.new_page(viewport={"width": 876, "height": 1200})
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
#  生成图片入口
# ══════════════════════════════════════
def generate_images():
    os.makedirs(IMAGE_DIR, exist_ok=True)
    date_str = now_cst().strftime("%Y-%m-%d")

    unused_news = load_unused_news()
    data, used_links = call_deepseek(unused_news)

    if not data:
        print("⚠️ 无可用新闻，跳过图片生成。")
        return

    # 总图
    html_to_image(
        render_overview_html(data),
        os.path.join(IMAGE_DIR, f"overview_{date_str}.png")
    )

    # 各区域子图
    for sec in data["news_sections"]:
        slug = sec["region"].replace("/", "_").replace(" ", "_")
        html_to_image(
            render_region_html(sec, data["date"], data["daily_focus"]),
            os.path.join(IMAGE_DIR, f"region_{slug}_{date_str}.png")
        )

    if used_links:
        save_used_links(used_links)
        print(f"  ✅ 已标记 {len(used_links)} 条新闻为已使用")

    print(f"\n📁 图片已保存至 {IMAGE_DIR}/")

# ══════════════════════════════════════
#  主程序
# ══════════════════════════════════════
def main():
    seven_days_ago = now_cst() - timedelta(days=DAYS_BACK)
    seven_days_ago = seven_days_ago.replace(hour=0, minute=0, second=0)

    print(f"[{now_cst().strftime('%Y-%m-%d %H:%M:%S')}] 启动全球新能源新闻监控（北京时间）")
    print(f"📅 抓取范围：{seven_days_ago.strftime('%Y-%m-%d')} 至今")

    # 第一步：从总表加载已有链接用于去重
    seen_urls = set()
    if os.path.exists(MASTER_FILE):
        with open(MASTER_FILE, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            next(reader, None)
            for r in reader:
                if len(r) >= 5:
                    seen_urls.add(r[4])
    print(f"📋 总表已有记录：{len(seen_urls)} 条，用于去重")

    # 第二步：抓取新闻
    all_new_data = []
    for source in SOURCES:
        all_new_data.extend(fetch_source(source, seven_days_ago, seen_urls))

    # 第三步：存入子文件和总表
    if all_new_data:
        all_new_data.sort(key=lambda x: x[3], reverse=True)
        split_by_date(all_new_data)
        merge_to_master()
        print(f"  🎉 本次新增 {len(all_new_data)} 条新闻入库")
    else:
        print("☕ 本次无新增新闻。")

    # 第四步：从总表未使用新闻生成图片
    generate_images()

    print(f"\n✅ 全部完成！")

if __name__ == "__main__":
    main()
