# ai/deepseek.py
import json
import time
import random
import logging
from openai import OpenAI
from ..utils.time_utils import now_cst
from ..utils.file_utils import save_used_links

logger = logging.getLogger(__name__)

def match_used_links_by_title(unused_news, data):
    """改进的标题匹配函数（适配新数据结构）"""
    selected_titles = []
    for sec in data.get("news_sections", []):
        for item in sec.get("news", []):
            selected_titles.append(item.get("title", ""))

    used_links = []
    for title in selected_titles:
        # 提取长关键词（长度>3）
        keywords = [w for w in title.split() if len(w) > 3]
        
        if not keywords:
            # 如果没有长关键词，使用标题的前20个字符
            title_segment = title[:20].lower()
            for row in unused_news:
                if title_segment in row[2].lower():
                    if row[4] not in used_links:
                        used_links.append(row[4])
                    break
        else:
            # 要求至少匹配2个关键词
            for row in unused_news:
                original = row[2].lower()
                matches = sum(1 for kw in keywords if kw.lower() in original)
                if matches >= 2:
                    if row[4] not in used_links:
                        used_links.append(row[4])
                    break
    return used_links

def cross_validate_regions(unused_news, data, conflict_file):
    """区域交叉验证"""
    conflicts = []
    index_map = {i + 1: row for i, row in enumerate(unused_news)}
    used_indices = data.get("used_indices", [])
    all_ds_regions = {sec.get("region", "") for sec in data.get("news_sections", [])}

    for idx in used_indices:
        if idx not in index_map:
            continue
        original_row = index_map[idx]
        ref_region = original_row[1]
        original_title = original_row[2]

        if ref_region in ("全球/其他", "跨区域"):
            continue

        if ref_region not in all_ds_regions:
            conflicts.append({
                "index": idx,
                "original_title": original_title,
                "ref_region": ref_region,
                "ds_region": "未归入任何区域",
                "date": original_row[3],
            })

    if conflicts:
        import csv
        import os
        file_exists = os.path.exists(conflict_file)
        with open(conflict_file, "a", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "index", "original_title", "ref_region", "ds_region", "date"
            ])
            if not file_exists:
                writer.writeheader()
            writer.writerows(conflicts)
        logger.info(f"  ⚠️  区域不一致：{len(conflicts)} 条 → {conflict_file}")
    else:
        logger.info("  ✅ 区域交叉验证通过，无冲突")

    return conflicts

def call_deepseek(unused_news, config, client, used_file, conflict_file):
    """调用DeepSeek API"""
    if not client:
        logger.warning("  ⚠️ DeepSeek 客户端未初始化，跳过筛选")
        return None, []

    if not unused_news:
        logger.warning("  ⚠️ 没有未使用的新闻，跳过生成图片")
        return None, []

    logger.info(f"\n🤖 调用 DeepSeek，从 {len(unused_news)} 条未使用新闻中筛选...")
    today_str = now_cst().strftime("%Y年%m月%d日")
    news_text = "\n".join(
        f"{i+1}. [ref_region:{r[1]}] {r[2]} ({r[3]})"
        for i, r in enumerate(unused_news)
    )

    prompt = f"""
# Role
你是一名资深的全球新能源行业分析师，深度聚焦于"光储充"一体化及智能电网、电力领域。

# Task
对下方原始新闻标题进行筛选、翻译和润色，生成专业"行业内参"。

# Requirements
1. 仅保留【光伏、储能、充电桩、微电网、电力/电网/能源转型】相关内容
2. 彻底剔除【风能、氢能、生物质能、核能】
3. **按区域归类，选择新闻最集中的{config.MIN_REGIONS}-{config.MAX_REGIONS}个核心区域**
4. 每个精选区域保留{config.MIN_TITLES_PER_REGION}-{config.MAX_TITLES_PER_REGION}条新闻
5. 所有标题必须翻译成中文，术语专业准确（工商业储能、并网政策、户用光伏等）
6. 每个区域给出一条出海机遇或准入门槛的专业点评（中性），**字数控制在35字以内，用一句话概括核心机会或门槛**，例如：“本土化清单扩展，外资需技术转让或合资以进入印度市场。”
7. **每条新闻必须附加一句“为什么重要”的解读，要求：**
   - **字数控制在15字以内，一句话点明核心价值**
   - 必须结合新闻中的具体主体（国家、公司、技术、政策名称、数据等）
   - 从以下角度切入（不限于）：市场准入、技术突破、竞争格局、投资风向、政策示范
   - 避免使用“A类企业”“某些市场”等模糊指代
   - 同一区域内的解读不能雷同，跨区域也尽量多样化
8. used_indices 必须返回你选中新闻对应的编号，编号来自新闻列表前的序号
9. 同一条新闻只能出现在一个区域，严禁在不同区域重复出现同一内容

# Output
只返回 JSON 本身，不要任何多余文字或 markdown：
{{
  "date": "{today_str}",
  "daily_focus": "今日核心关注点的专业分析",
  "news_sections": [
    {{
      "region": "区域名称",
      "market_insight": "该区域光储充市场研判",
      "news": [
        {{
          "title": "标题1",
          "importance": "为什么重要的解读（例如：此政策将允许外资独立开发智利锂矿，为宁德时代等电池巨头打开直接采购通道。）"
        }},
        {{
          "title": "标题2",
          "importance": "为什么重要的解读"
        }}
      ]
    }}
  ],
  "used_indices": [1, 3, 5, 8, 12]
}}

# 新闻列表
{news_text}
"""

    for attempt in range(config.DEEPSEEK_MAX_RETRIES):
        try:
            resp = client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=config.DEEPSEEK_TEMPERATURE,
                timeout=config.DEEPSEEK_TIMEOUT
            )
            raw = resp.choices[0].message.content.strip()

            # 清理可能的 markdown 代码块
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            # 解析 JSON
            data = json.loads(raw)
            
            # 基础字段验证
            if "news_sections" not in data:
                raise ValueError("返回数据缺少 news_sections 字段")
            if "daily_focus" not in data:
                raise ValueError("返回数据缺少 daily_focus 字段")
            
            if not data["news_sections"]:
                logger.warning("  ⚠️ 注意：news_sections 为空，可能当天没有符合条件的新闻")
                return None, []
            
            # 区域数量优化（基于 news 列表长度排序）
            regions_count = len(data["news_sections"])
            if regions_count > config.MAX_REGIONS:
                logger.info(f"  ⚠️ DeepSeek 返回了 {regions_count} 个区域，超过{config.MAX_REGIONS}个限制，进行智能筛选")
                data["news_sections"].sort(
                    key=lambda x: len(x.get("news", [])), 
                    reverse=True
                )
                data["news_sections"] = data["news_sections"][:config.MAX_REGIONS]
                logger.info(f"  ✅ 筛选后保留 {len(data['news_sections'])} 个区域")
            elif regions_count < config.MIN_REGIONS:
                logger.info(f"  ℹ️ 只有 {regions_count} 个区域有相关新闻，低于建议的{config.MIN_REGIONS}个")
            
            # 每个区域的新闻条数优化
            total_titles_before = sum(len(sec.get("news", [])) for sec in data["news_sections"])
            for sec in data["news_sections"]:
                news_list = sec.get("news", [])
                if len(news_list) > config.MAX_TITLES_PER_REGION:
                    logger.info(f"  ⚠️ 区域 {sec['region']} 有 {len(news_list)} 条新闻，精简到{config.MAX_TITLES_PER_REGION}条")
                    sec["news"] = news_list[:config.MAX_TITLES_PER_REGION]
                elif len(news_list) < config.MIN_TITLES_PER_REGION and news_list:
                    logger.info(f"  ℹ️ 区域 {sec['region']} 只有 {len(news_list)} 条新闻，低于建议的{config.MIN_TITLES_PER_REGION}条")
            
            # 标题去重（基于 title 字段）
            seen_titles = set()
            for sec in data["news_sections"]:
                unique_news = []
                for item in sec.get("news", []):
                    title = item.get("title", "")
                    key = title[:30].strip()
                    if key not in seen_titles:
                        seen_titles.add(key)
                        unique_news.append(item)
                sec["news"] = unique_news
            
            # 过滤掉没有新闻的区域
            data["news_sections"] = [
                sec for sec in data["news_sections"]
                if sec.get("news")
            ]
            
            # 统计优化后的总条数
            total_titles_after = sum(len(sec.get("news", [])) for sec in data["news_sections"])
            if total_titles_after > 0:
                logger.info(f"  📊 优化后：{len(data['news_sections'])} 个区域，共 {total_titles_after} 条新闻")
                if total_titles_before != total_titles_after:
                    logger.info(f"     原返回 {total_titles_before} 条，优化后 {total_titles_after} 条")
            
            # 处理 used_indices
            used_links = []
            indices = data.get("used_indices", [])
            
            if indices:
                for idx in indices:
                    pos = idx - 1
                    if 0 <= pos < len(unused_news):
                        link = unused_news[pos][4]
                        if link not in used_links:
                            used_links.append(link)
                logger.info(f"  ✅ 第{attempt+1}次调用成功，编号匹配：标记 {len(used_links)} 条")
            
            # 如果编号匹配不足，使用标题反查兜底
            if not used_links or len(used_links) < max(1, total_titles_after // 2):
                logger.info("  ⚠️ 编号匹配不足，启用标题反查兜底...")
                fallback_links = match_used_links_by_title(unused_news, data)
                for link in fallback_links:
                    if link not in used_links:
                        used_links.append(link)
                logger.info(f"  ✅ 兜底后共标记 {len(used_links)} 条")
            
            # 区域交叉验证
            if used_links:
                cross_validate_regions(unused_news, data, conflict_file)
            
            return data, used_links

        except json.JSONDecodeError as e:
            logger.error(f"  ⚠️ 第{attempt+1}次 JSON 解析失败：{e}")
            if attempt < config.DEEPSEEK_MAX_RETRIES - 1 and 'raw' in locals():
                logger.debug(f"  原始返回内容预览：{raw[:200]}...")
        except ValueError as e:
            logger.error(f"  ⚠️ 第{attempt+1}次字段校验失败：{e}")
        except Exception as e:
            logger.error(f"  ⚠️ 第{attempt+1}次调用异常：{type(e).__name__}: {e}")
            if "429" in str(e):
                logger.info("  ⚠️ 触发速率限制，延长等待时间")

        if attempt < config.DEEPSEEK_MAX_RETRIES - 1:
            sleep_time = (2 ** attempt) + random.uniform(0, 2)
            logger.info(f"  🔄 等待 {sleep_time:.1f} 秒后重试...")
            time.sleep(sleep_time)

    logger.error("  ❌ DeepSeek 连续5次失败，跳过图片生成")
    return None, []
