#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
能源新闻监控脚本 - GitHub Actions 安全版本
API Key 从环境变量读取，不硬编码
"""

import os
import re
import time
import random
import requests
import json
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup

# ========== 路径配置 ==========
# 获取仓库根目录（脚本所在目录的父目录）
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_FILE = os.path.join(BASE_DIR, "history.txt")

# 报告输出目录
REPORTS_DIR = os.path.join(BASE_DIR, "docs")

TOKEN_USAGE_FILE = os.path.join(REPORTS_DIR, "token_usage.json")  # ⭐ 新增

# ========== Token 监控配置 ==========
# ⭐ 新增：Token 使用统计
token_stats = {
    "date": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d"),
    "jina_requests": 0,
    "jina_tokens": 0,
    "deepseek_requests": 0,
    "deepseek_input_tokens": 0,
    "deepseek_output_tokens": 0,
    "deepseek_total_tokens": 0,
}

# ⭐ 新增：加载历史 Token 使用记录
def load_token_history():
    """加载历史 Token 使用记录"""
    if os.path.exists(TOKEN_USAGE_FILE):
        try:
            with open(TOKEN_USAGE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

# ⭐ 新增：保存 Token 使用记录
def save_token_usage():
    """保存今日 Token 使用统计"""
    history = load_token_history()
    
    # 查找是否已有今日记录
    today = token_stats["date"]
    found = False
    for record in history:
        if record.get("date") == today:
            # 更新今日记录
            record.update(token_stats)
            found = True
            break
    
    if not found:
        history.append(token_stats.copy())
    
    # 只保留最近 30 天记录
    history = history[-30:]
    
    # 保存
    os.makedirs(REPORTS_DIR, exist_ok=True)
    with open(TOKEN_USAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    
    print(f"💰 Token 使用记录已保存：{TOKEN_USAGE_FILE}")

# ⭐ 新增：估算 Jina AI Token 数（按字符数估算）
def estimate_jina_tokens(text):
    """估算 Jina AI 的 Token 数（1 Token ≈ 4 字符）"""
    return len(text) // 4


# ========== 安全配置区 ==========
# 从环境变量读取 API Key（GitHub Actions 会自动注入）
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
JINA_KEY = os.getenv('JINA_KEY', '')

# 验证密钥
if not DEEPSEEK_API_KEY:
    print("⚠️ 警告：DEEPSEEK_API_KEY 未配置，AI 摘要将跳过")
if not JINA_KEY:
    print("ℹ️ 提示：JINA_KEY 未配置，使用免费版 Jina 读取器")

SOURCES = [
    {"name": "Power Technology", "url": "https://www.power-technology.com/news/", "type": "path_filter"},
    {"name": "Energy Storage News", "url": "https://www.energy-storage.news/news/", "type": "feature_filter"}
]


# ========== 辅助函数 ==========
def check_history(link):
    """检查链接是否已存在于历史记录中"""
    if not os.path.exists(HISTORY_FILE):
        return False
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            # 精确匹配整行
            return link + "\n" in content or link in content.splitlines()
    except Exception as e:
        print(f"   ⚠️ 检查历史记录失败：{e}")
        return False


def save_history(link):
    """保存链接到历史记录"""
    try:
        # 先检查是否已存在，避免重复写入
        if check_history(link):
            print(f"   ⚠️ 链接已存在，跳过保存：{link[:50]}...")
            return
        
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(link + "\n")
            f.flush()  # 立即写入磁盘
        print(f"   💾 已保存：{link[:50]}...")
    except Exception as e:
        print(f"   ❌ 保存失败：{e}")


def get_ai_summary(link):
    """获取 AI 摘要"""
    if not DEEPSEEK_API_KEY:
        return "⚠️ 未配置 AI API 密钥，跳过摘要生成"
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 使用 Jina AI 读取文章内容
            headers = {"X-Return-Format": "markdown"}
            if JINA_KEY:
                headers["Authorization"] = f"Bearer {JINA_KEY}"
            
            jina_url = f"https://r.jina.ai/{link}"
            response = requests.get(jina_url, headers=headers, timeout=60)
            
            full_text = ""
            if response.status_code == 200:
                full_text = response.text[:3500]
                # ⭐ 新增：统计 Jina Token
                token_stats["jina_requests"] += 1
                token_stats["jina_tokens"] += estimate_jina_tokens(full_text)
            
            if not full_text:
                continue

            # 调用 DeepSeek API
            url = "https://api.deepseek.com/chat/completions"
            headers_ds = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
            }
            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一位专业资深的能源分析师，请用中文总结这篇新闻。要求：分为'核心内容'和'商业机会'两个部分。"},
                    {"role": "user", "content": full_text}
                ],
                "temperature": 0.3,
                "max_tokens": 500
            }
            response = requests.post(url, headers_ds, data=json.dumps(data), timeout=30)
            
            # ⭐ 统计 DeepSeek Token
            result = response.json()
            usage = result.get('usage', {})
            token_stats["deepseek_requests"] += 1
            token_stats["deepseek_input_tokens"] += usage.get('prompt_tokens', 0)
            token_stats["deepseek_output_tokens"] += usage.get('completion_tokens', 0)
            token_stats["deepseek_total_tokens"] += usage.get('total_tokens', 0)
            
            return result['choices'][0]['message']['content']
            
        except requests.exceptions.Timeout:
            print(f"⚠️ 第 {attempt + 1} 次尝试超时，正在重试...")
            time.sleep(2)
        except Exception as e:
            if attempt == max_retries - 1:
                return f"AI 总结最终出错：{e}"
            print(f"⚠️ 发生错误 {e}，正在重试...")
            time.sleep(2)
            
    return "AI 总结出错：多次尝试后依然无法获取内容。"


def normalize_date(date_str):
    """将各种日期格式标准化为 YYYY-MM-DD"""
    try:
        if not date_str or not isinstance(date_str, str):
            return "未知"
        
        date_str = date_str.strip()
        if len(date_str) < 8:
            return "未知"
        
        if 'T' in date_str:
            date_str = date_str.split('T')[0]
        if '+' in date_str:
            date_str = date_str.split('+')[0]
        
        if '年' in date_str:
            date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
        
        month_map = {
            'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
            'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
            'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
        }
        
        date_lower = date_str.lower()
        for m_en, m_num in month_map.items():
            if m_en in date_lower:
                date_str = re.sub(rf'\b{m_en}\w*\b', m_num, date_str, flags=re.IGNORECASE)
                parts = re.sub(r'[,,\s]+', ' ', date_str).strip().split()
                parts = [p for p in parts if p]
                
                if len(parts) >= 3:
                    year = None
                    for i, p in enumerate(parts):
                        if len(p) == 4 and p.isdigit():
                            year = p
                            parts.pop(i)
                            break
                    
                    if year and len(parts) >= 2:
                        month = parts[0] if len(parts[0]) <= 2 else parts[1]
                        day = parts[1] if len(parts[0]) <= 2 else parts[0]
                        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        date_str = re.sub(r'[^0-9-]', '', date_str.replace('/', '-'))
        
        match = re.match(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})', date_str)
        if match:
            year, month, day = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        match = re.match(r'(\d{1,2})[-/](\d{1,2})[-/](\d{4})', date_str)
        if match:
            month, day, year = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        return "未知"
    except:
        return "未知"


def get_news_publish_date_jina(url):
    """Jina AI 方式提取时间"""
    try:
        jina_url = f"https://r.jina.ai/{url}"
        response = requests.get(jina_url, timeout=30)
        content = response.text
        
        date_patterns = [
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}',
            r'(\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4})',
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                date_str = normalize_date(match.group(1))
                if date_str != "未知":
                    return date_str, True
        return "未知", False
    except:
        return "未知", False


def get_news_publish_date_bs4(url):
    """BeautifulSoup 方式提取时间"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=30)
        response.encoding = response.apparent_encoding
        soup = BeautifulSoup(response.text, 'html.parser')
        
        meta_patterns = [
            soup.find('meta', property='article:published_time'),
            soup.find('meta', attrs={'name': 'date'}),
            soup.find('meta', attrs={'itemprop': 'datePublished'}),
        ]
        
        for meta in meta_patterns:
            if meta:
                content = meta.get('content', '')
                if content:
                    date_str = normalize_date(content)
                    if date_str != "未知":
                        return date_str, True
        
        time_tag = soup.find('time')
        if time_tag:
            datetime_attr = time_tag.get('datetime', '')
            if datetime_attr:
                date_str = normalize_date(datetime_attr)
                if date_str != "未知":
                    return date_str, True
        
        return "未知", False
    except:
        return "未知", False


def get_news_publish_date(url):
    """双重备份时间提取"""
    date_jina, success = get_news_publish_date_jina(url)
    if success:
        return date_jina
    
    date_bs4, success = get_news_publish_date_bs4(url)
    if success:
        return date_bs4
    
    return "未知"


def clean_ai_summary(text):
    """清理 AI 摘要中的套话"""
    unwanted_phrases = [
        "好的，作为一名专业资深的能源分析师，我已仔细阅读并分析了这篇新闻。以下是总结：",
        "好的，作为一名专业资深的能源分析师，",
        "以下是我的总结：",
        "以下是总结：",
        "---",
    ]
    for phrase in unwanted_phrases:
        text = text.replace(phrase, "")
    return text.strip()


def generate_reports(report_data):
    """生成 Markdown 和 HTML 报告"""
    today = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d")
    
    # ⭐ 关键修改：确保 docs 文件夹存在
    os.makedirs(REPORTS_DIR, exist_ok=True)
    
    # 关键修改：文件路径改为 docs/ 文件夹
    md_filename = os.path.join(REPORTS_DIR, f"Energy_Report_{today}.md")
    html_filename = os.path.join(REPORTS_DIR, f"Energy_Report_{today}.html")

    # ⭐ 新增：在报告中添加 Token 使用统计
    token_summary = f"""
## 💰 API Token 使用统计

| API | 请求次数 | Token 用量 |
|-----|----------|------------|
| Jina AI | {token_stats['jina_requests']} | ~{token_stats['jina_tokens']} tokens |
| DeepSeek | {token_stats['deepseek_requests']} | {token_stats['deepseek_total_tokens']} tokens |
| **合计** | {token_stats['jina_requests'] + token_stats['deepseek_requests']} | ~{token_stats['jina_tokens'] + token_stats['deepseek_total_tokens']} tokens |

"""
       
    # Markdown 报告
    with open(md_filename, "w", encoding="utf-8") as f:
        f.write(f"# 🌍 全球能源新闻 ({today})\n\n{token_summary}{report_data}")
    
    # HTML 报告
    body_html = report_data.replace('### ', '<div class="news-item"><h3>')
    body_html = body_html.replace('\n', '<br>')
    
    # ⭐ 新增：Token 统计 HTML
    token_html = f"""
    <div class="token-stats">
        <h2>💰 API Token 使用统计</h2>
        <table>
            <tr><th>API</th><th>请求次数</th><th>Token 用量</th></tr>
            <tr><td>Jina AI</td><td>{token_stats['jina_requests']}</td><td>~{token_stats['jina_tokens']} tokens</td></tr>
            <tr><td>DeepSeek</td><td>{token_stats['deepseek_requests']}</td><td>{token_stats['deepseek_total_tokens']} tokens</td></tr>
            <tr><td><strong>合计</strong></td><td><strong>{token_stats['jina_requests'] + token_stats['deepseek_requests']}</strong></td><td><strong>~{token_stats['jina_tokens'] + token_stats['deepseek_total_tokens']}</strong></td></tr>
        </table>
    </div>
    """
    
    html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>全球能源新闻 ({today})</title>
<style>
    * {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif; color: #333; line-height: 1.6; box-sizing: border-box; }}
    body {{ background: #fff; padding: 60px 20px; max-width: 800px; margin: 0 auto; }}
    h1 {{ text-align: center; color: #1a202c; margin-bottom: 60px; font-size: 2rem; }}
    .news-item {{ margin-bottom: 40px; padding-bottom: 30px; border-bottom: 1px solid #e2e8f0; }}
    h3 {{ color: #2b6cb0; font-size: 1.3rem; margin-top: 0; }}
    .publish-date {{ font-size: 0.85rem; color: #718096; font-style: italic; }}
    a {{ color: #3182ce; text-decoration: none; }}
    .token-stats {{ background: #f7fafc; padding: 20px; border-radius: 10px; margin-bottom: 40px; }}
    .token-stats table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
    .token-stats th, .token-stats td {{ padding: 10px; text-align: left; border-bottom: 1px solid #e2e8f0; }}
    .token-stats th {{ background: #edf2f7; }}
</style>
</head>
<body>
    <h1>🌍 全球能源新闻 ({today})</h1>
    {token_html}
    <div class="main-content">{body_html}</div>
</body>
</html>"""
    
    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    # ⭐ 保存 Token 使用记录
    save_token_usage()

    print(f"✅ 报告已生成：{md_filename}, {html_filename}")


def monitor_all_sources():
    """监控所有新闻源，仅处理最近 7 天内的新闻"""
    # === 调试输出 ===
    print(f"📍 当前工作目录：{os.getcwd()}")
    print(f"📍 history.txt 完整路径：{os.path.abspath(HISTORY_FILE)}")
    print(f"📍 history.txt 是否存在：{os.path.exists(HISTORY_FILE)}")
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            print(f"📍 当前历史记录数：{len(lines)} 条")
    else:
        print("📍 history.txt 不存在，将创建新文件")
    # ===============
    
    full_report = ""
    bad_keywords = ['newsletter', 'feed', 'contact', 'about', 'events', 'advertise', 'privacy', 'terms', 'subscribe', 'img', 'image']
    bad_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.pdf', '.webp', '.avif']

    # 计算一周前的日期（用于比较）
    one_week_ago = datetime.now() - timedelta(days=7)

    for source in SOURCES:
        print(f"\n" + "="*30)
        print(f"🚀 正在扫描：{source['name']}")
        print("="*30)
        try:
            jina_url = f"https://r.jina.ai/{source['url']}"
            response = requests.get(jina_url, timeout=60)
            content = response.text
            all_links = re.findall(r'\[([^\]]+)\]\((https?://www\.energy-storage\.news/[^\s\)]+|https?://www\.power-technology\.com/[^\s\)]+)\)', content)
            
            found_count = 0
            for title, link in all_links:
                if found_count >= 3:
                    break  # 提前退出内层循环
                
                title = title.strip()
                link_original = re.split(r'[\s"]', link)[0]
                link_lower = link_original.lower()
                
                is_file = any(link_lower.endswith(ext) for ext in bad_extensions)
                is_noise = any(word in link_lower for word in bad_keywords)
                is_short = len(title) < 20

                is_news = False
                if not is_file and not is_noise and not is_short:
                    if source['type'] == "path_filter":
                        if any(p in link_lower for p in ['/news/', '/features/']):
                            is_news = True
                    elif source['type'] == "feature_filter":
                        if link_lower.count('-') >= 4:
                            is_news = True

                # 跳过非新闻
                if not is_news:
                    continue
                
                # 跳过已处理过的链接
                if check_history(link_original):
                    print(f"️  跳过（已处理）：{title}")
                    continue

                print(f"✅ 捕获情报：{title}")
                publish_date_str = get_news_publish_date(link_original)
                print(f"   📅 发布时间：{publish_date_str}")

                # === 时间筛选逻辑 ===
                skip_due_to_date = False
                if publish_date_str == "未知":
                    print("   ⏭️  跳过：无法确定发布时间")
                    skip_due_to_date = True
                else:
                    try:
                        # 尝试解析为 datetime
                        pub_dt = datetime.strptime(publish_date_str, "%Y-%m-%d")
                        if pub_dt.date() < one_week_ago.date():
                            print(f"   ⏭️  跳过：发布时间早于 {one_week_ago.strftime('%Y-%m-%d')}（超过 7 天）")
                            skip_due_to_date = True
                        else:
                            print("   ✅ 时间符合要求（7 天内）")
                    except Exception as e:
                        print(f"   ⏭️  跳过：日期解析失败 - {e}")
                        skip_due_to_date = True

                if skip_due_to_date:
                    # 即使跳过也保存记录，避免重复检查旧新闻
                    save_history(link_original)
                    continue

                # === 仅当时间合格时，才获取 AI 摘要 ===
                summary = get_ai_summary(link_original)
                summary = clean_ai_summary(summary)
                
                full_report += f"### {title}\n"
                full_report += f"<p class='publish-date'>📅 发布时间：{publish_date_str}</p>\n"
                full_report += f"**来源**: {source['name']} | [查看原文]({link_original})\n\n"
                full_report += f"📝 中文摘要:\n{summary}\n\n---\n\n"
                
                # === 关键：保存到历史记录 ===
                save_history(link_original)
                found_count += 1
                time.sleep(random.uniform(3, 8))

            if found_count == 0:
                print("✨ 未发现新内容（或无 7 天内新闻）。")
        except Exception as e:
            print(f"❌ 出错：{e}")

    if full_report:
        generate_reports(full_report)
    else:
        print("📭 本次无新报告生成（无 7 天内有效新闻）")
        # 即使无报告，也保存 Token 记录（可能为 0）
        save_token_usage()


if __name__ == "__main__":
    print("=" * 50)
    print("🌍 能源新闻监控系统启动")
    print(f"⏰ 运行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    monitor_all_sources()