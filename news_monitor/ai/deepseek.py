# ai/deepseek.py
import json
import time
import random
import logging
import csv
import os
from openai import OpenAI
from ..utils.time_utils import now_cst
from ..utils.file_utils import save_used_links
from ..utils.file_utils import get_recent_regions, save_region_history

logger = logging.getLogger(__name__)

def match_used_links_by_title(unused_news, data):
    """改进的标题匹配函数（适配新数据结构）"""
    selected_titles = []
    for sec in data.get("news_sections", []):
        for item in sec.get("news", []):
            selected_titles.append(item.get("title", ""))

    used_links = []
    for title in selected_titles:
        keywords = [w for w in title.split() if len(w) > 3]
        if not keywords:
            title_segment = title[:20].lower()
            for row in unused_news:
                if title_segment in row[2].lower():
                    if row[4] not in used_links:
                        used_links.append(row[4])
                    break
        else:
            for row in unused_news:
                original = row[2].lower()
                matches = sum(1 for kw in keywords if kw.lower() in original)
                if matches >= 2:
                    if row[4] not in used_links:
                        used_links.append(row[4])
                    break
    return used_links

def cross_validate_regions(unused_news, data, conflict_file):
    """区域交叉验证（保持不变）"""
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

def deduplicate_news_by_similarity(news_items, threshold=0.7):
    """基于标题相似度的去重"""
    if not news_items:
        return news_items
    def jaccard_similarity(a, b):
        set_a = set(a.lower().split())
        set_b = set(b.lower().split())
        if not set_a or not set_b:
            return 0
        return len(set_a & set_b) / len(set_a | set_b)
    unique_items = []
    for item in news_items:
        is_dup = False
        for existing in unique_items:
            if jaccard_similarity(item['title'], existing['title']) >= threshold:
                is_dup = True
                break
        if not is_dup:
            unique_items.append(item)
    return unique_items

def resolve_source_cross_validate(item, unused_news, threshold=0.5):
    """
    交叉验证新闻来源
    返回 (source, is_conflict, matched_by_index)
    """
    idx = item.get("index")
    title = item.get("title", "")
    source_by_index = None
    if idx and 1 <= idx <= len(unused_news):
        source_by_index = unused_news[idx-1][0]
    
    # 标题匹配
    source_by_title = None
    best_score = 0
    title_lower = title.lower()
    title_words = set(title_lower.split())
    for row in unused_news:
        original_title = row[2].lower()
        orig_words = set(original_title.split())
        if not title_words or not orig_words:
            continue
        intersection = len(title_words & orig_words)
        union = len(title_words | orig_words)
        score = intersection / union if union > 0 else 0
        if score > best_score and score >= threshold:
            best_score = score
            source_by_title = row[0]
    
    if source_by_index and source_by_title:
        if source_by_index != source_by_title:
            logger.warning(f"来源冲突: index={source_by_index}, title_match={source_by_title}, title={title}")
            # 记录冲突到文件
            try:
                conflict_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "docs", "source_conflicts.csv")
                file_exists = os.path.exists(conflict_file)
                with open(conflict_file, "a", newline="", encoding="utf-8-sig") as f:
                    writer = csv.writer(f)
                    if not file_exists:
                        writer.writerow(["date", "title", "index_source", "title_match_source", "matched_score"])
                    writer.writerow([now_cst().strftime("%Y-%m-%d"), title, source_by_index, source_by_title, best_score])
            except Exception as e:
                logger.debug(f"记录来源冲突失败: {e}")
            return source_by_title, True, False   # 采用标题匹配结果
        else:
            return source_by_index, False, True
    elif source_by_index:
        return source_by_index, False, True
    elif source_by_title:
        return source_by_title, True, False
    else:
        return "Unknown", False, False

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

    recent_regions = get_recent_regions(days=3)
    recent_hint = ""
    if recent_regions:
        recent_hint = f"\n**注意：最近3天已重点报道的区域有：{', '.join(recent_regions)}。请优先选择其他区域，若其他区域新闻不足，可酌情包含部分重复区域。**\n"

    # 构建区域白名单字符串
    if hasattr(config, 'REGION_LIST') and config.REGION_LIST:
        region_list_str = "、".join(config.REGION_LIST)
    else:
        from ..utils.region_utils import REGION_MAP
        region_list_str = "、".join(REGION_MAP.keys())
    
    prompt = f"""
# Role
你是一名资深的全球新能源行业分析师，深度聚焦于"光储充"一体化及智能电网、电力领域。

# Task
对下方原始新闻标题进行筛选、翻译和润色，生成专业"行业内参"。

# Requirements
1. 仅保留【光伏、储能、充电桩、微电网、电力/电网/能源转型】相关内容
2. 彻底剔除【风能、氢能、生物质能、核能、电动汽车整车、消费电子、家用小电器】
3. **选题优先级：优先选择以下市场的新闻：南欧（意大利/西班牙）、东南亚（菲律宾/泰国/马来西亚）、西欧（英国/荷兰）、拉丁美洲（阿根廷）、东欧（捷克/波兰）、非洲南部（南非）、西非（尼日利亚）、中亚（乌兹别克斯坦/哈萨克斯坦）。其他区域作为补充。**
4. **按区域归类，选择新闻最集中的{config.MIN_REGIONS}-{config.MAX_REGIONS}个核心区域**
   - 区域名称必须严格从以下列表中选择，不得使用其他名称：
     {region_list_str}
   - 国家归属规则（强制执行）：
     * 希腊、意大利、西班牙、葡萄牙 → 南欧
     * 波兰、罗马尼亚、捷克、匈牙利、乌克兰、塞尔维亚 → 东欧
     * 英国、德国、法国、荷兰、比利时、瑞典、丹麦、挪威、芬兰、奥地利、瑞士 → 西欧
     * 美国、加拿大 → 北美
     * 墨西哥、巴西、智利、秘鲁、哥伦比亚、阿根廷、厄瓜多尔 → 拉丁美洲
     * 澳大利亚、新西兰 → 大洋洲
     * 沙特、UAE、伊拉克、以色列、约旦、土耳其、埃及、摩洛哥、突尼斯、阿尔及利亚 → 中东/北非
     * 肯尼亚、坦桑尼亚、埃塞俄比亚、乌干达、卢旺达 → 东非
     * 南非、赞比亚、津巴布韦、莫桑比克、纳米比亚、博茨瓦纳 → 非洲南部
     * 尼日利亚、加纳、塞内加尔、科特迪瓦、喀麦隆 → 西非
     * 中国、日本、韩国、台湾 → 东亚
     * 印度、巴基斯坦、孟加拉、斯里兰卡、尼泊尔 → 南亚
     * 泰国、越南、印尼、菲律宾、马来西亚、新加坡、缅甸、柬埔寨 → 东南亚
     * 哈萨克斯坦、乌兹别克斯坦、吉尔吉斯斯坦、塔吉克斯坦、土库曼斯坦 → 中亚
   - 若新闻涉及多国或全球性内容，归入"跨区域"或"全球/其他"
{recent_hint}
5. **区域轮换强制规则：除非其他区域当天新闻数量不足2条，否则禁止选择最近3天已出现的区域。**
6. 每个精选区域保留{config.MIN_TITLES_PER_REGION}-{config.MAX_TITLES_PER_REGION}条新闻
7. **去重规则：同一事件若被多个来源报道，只保留信息量最大的一条，其余剔除。**
8. 所有标题必须翻译成中文，术语专业准确（工商业储能、并网政策、户用光伏等）
9. 每个区域给出一条市场点评，**字数严格控制在35字以内，一句话，中性表述，不带销售或推广导向**
10. **每条新闻必须附加一句"为什么重要"的解读，要求：**
    - **字数严格控制在15字以内**
    - 必须结合新闻中的具体主体（国家、公司、技术、政策名称、数据等）
    - 从以下角度切入（不限于）：市场准入、技术突破、竞争格局、投资风向、政策示范
    - 避免使用"A类企业""某些市场"等模糊指代
    - 同一区域内的解读不能雷同，跨区域也尽量多样化
    - **语言中性，不带推广或销售导向，不使用"机遇""红利""布局"等营销词汇**
11. **daily_focus 字数严格控制在20字以内，点明今日新闻最值得关注的市场动向，中性表述**
12. used_indices 必须返回你选中新闻对应的编号，编号来自新闻列表前的序号
13. 同一条新闻只能出现在一个区域，严禁在不同区域重复出现同一内容
14. **每条新闻必须附带其在新闻列表中的原始编号（`index` 字段），编号与提供的列表序号一致（从1开始）。编号错误会导致来源追溯失败，请务必准确。**

# Output
只返回 JSON 本身，不要任何多余文字或 markdown 代码块标记：

{{
  "date": "{today_str}",
  "daily_focus": "今日核心关注点（20字以内，中性，一句话）",
  "news_sections": [
    {{
      "region": "区域名称（必须来自上方白名单）",
      "market_insight": "该区域市场点评（35字以内，中性）",
      "news": [
        {{
          "title": "标题1",
          "importance": "重要性解读（15字以内，中性）",
          "index": 1
        }},
        {{
          "title": "标题2",
          "importance": "重要性解读（15字以内，中性）",
          "index": 3
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
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()
            data = json.loads(raw)
            
            # 基础字段验证
            if "news_sections" not in data:
                raise ValueError("缺少 news_sections")
            if "daily_focus" not in data:
                raise ValueError("缺少 daily_focus")
            if not data["news_sections"]:
                logger.warning("  ⚠️ news_sections 为空")
                return None, []
            
            # 区域数量优化
            regions_count = len(data["news_sections"])
            if regions_count > config.MAX_REGIONS:
                logger.info(f"  ⚠️ DeepSeek 返回了 {regions_count} 个区域，超过{config.MAX_REGIONS}个限制，进行智能筛选")
                data["news_sections"].sort(key=lambda x: len(x.get("news", [])), reverse=True)
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
            
            # 语义相似度去重
            for sec in data["news_sections"]:
                sec["news"] = deduplicate_news_by_similarity(sec.get("news", []), threshold=0.7)
            
            # 过滤掉没有新闻的区域
            data["news_sections"] = [sec for sec in data["news_sections"] if sec.get("news")]
            
            # 统计优化后的总条数
            total_titles_after = sum(len(sec.get("news", [])) for sec in data["news_sections"])
            if total_titles_after > 0:
                logger.info(f"  📊 优化后：{len(data['news_sections'])} 个区域，共 {total_titles_after} 条新闻")
                if total_titles_before != total_titles_after:
                    logger.info(f"     原返回 {total_titles_before} 条，优化后 {total_titles_after} 条")
            
            # ========== 新增：为每条新闻交叉验证来源 ==========
            for sec in data["news_sections"]:
                for item in sec.get("news", []):
                    source, is_conflict, matched_by_index = resolve_source_cross_validate(item, unused_news)
                    item["source"] = source
                    item["source_conflict"] = is_conflict
                    item["source_matched_by_index"] = matched_by_index
            # =============================================
            
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
            # 保存当天选中的区域
            regions_today = [sec['region'] for sec in data.get('news_sections', [])]
            if regions_today:
                save_region_history(regions_today)
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