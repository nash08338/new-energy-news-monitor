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
from datetime import datetime
from bs4 import BeautifulSoup

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
HISTORY_FILE = "history.txt"

# ========== 辅助函数 ==========
def check_history(link):
    if not os.path.exists(HISTORY_FILE):
        return False
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return link in f.read()

def save_history(link):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(link + "\n")

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
                    {"role": "system", "content": "你是一位专业资深的能源分析师，请用中文总结这篇新闻。要求：分为"核心内容"和"商业机会"两个部分。"},
                    {"role": "user", "content": full_text}
                ],
                "temperature": 0.3,
                "max_tokens": 500
            }
            response = requests.post(url, headers=headers_ds, data=json.dumps(data), timeout=30)
            return response.json()['choices'][0]['message']['content']
            
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
    today = datetime.now().strftime("%Y-%m-%d")
    md_filename = f"Energy_Report_{today}.md"
    html_filename = f"Energy_Report_{today}.html"
    
    # Markdown 报告
    with open(md_filename, "w", encoding="utf-8") as f:
        f.write(f"# 🌍 全球能源内参 ({today})\n\n{report_data}")
    
    # HTML 报告
    body_html = report_data.replace('### ', '<div class="news-item"><h3>')
    body_html = body_html.replace('\n', '<br>')
    
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
</style>
</head>
<body>
    <h1>🌍 全球能源新闻 ({today})</h1>
    <div class="main-content">{body_html}</div>
</body>
</html>"""
    
    with open(html_filename, "w", encoding="utf-8") as f:
        f.write(html_template)
    
    print(f"✅ 报告已生成：{md_filename}, {html_filename}")

def monitor_all_sources():
    """监控所有新闻源"""
    full_report = ""
    bad_keywords = ['newsletter', 'feed', 'contact', 'about', 'events', 'advertise', 'privacy', 'terms', 'subscribe', 'img', 'image']
    bad_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.pdf', '.webp', '.avif']

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

                if is_news and not check_history(link_original):
                    print(f"✅ 捕获情报：{title}")
                    
                    publish_date = get_news_publish_date(link_original, debug=True)
                    print(f"   📅 发布时间：{publish_date}")
                    
                    summary = get_ai_summary(link_original)
                    summary = clean_ai_summary(summary)
                    
                    full_report += f"### {title}\n"
                    full_report += f"<p class='publish-date'>📅 发布时间：{publish_date}</p>\n"
                    full_report += f"**来源**: {source['name']} | [查看原文]({link_original})\n\n"
                    full_report += f"📝 中文摘要:\n{summary}\n\n---\n\n"
                    
                    save_history(link_original)
                    found_count += 1
                    time.sleep(random.uniform(3, 8))
                    if found_count >= 3:
                    break
            if found_count == 0:
                print("✨ 未发现新内容。")
        except Exception as e:
            print(f"❌ 出错：{e}")

    if full_report:
        generate_reports(full_report)
    else:
        print("📭 本次无新报告生成")

if __name__ == "__main__":
    print("=" * 50)
    print("🌍 能源新闻监控系统启动")
    print(f"⏰ 运行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    monitor_all_sources()