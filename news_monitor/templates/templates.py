# templates/templates.py
# 更新后的渲染函数，适配新的 news 数据结构，并优化页脚，统一样式管理
from ..config import Config

def _get_importance_emoji(text):
    """根据重要性文本关键词匹配emoji"""
    text_lower = text.lower()
    
    # 政策/法规类
    if any(k in text_lower for k in ["政策", "法规", "补贴", "关税", "mandate", "policy", "规则", "法案", "regulation"]):
        return "🏛️"
    # 项目/投资类
    if any(k in text_lower for k in ["项目", "投资", "投产", "产能", "project", "investment", "工厂", "产线", "部署"]):
        return "🏗️"
    # 技术突破类
    if any(k in text_lower for k in ["技术", "效率", "研发", "突破", "technology", "efficiency", "创新", "认证"]):
        return "🔬"
    # 市场准入类
    if any(k in text_lower for k in ["市场", "准入", "出口", "market", "access", "准入", "壁垒", "机会"]):
        return "🚪"
    # 环境/气候类
    if any(k in text_lower for k in ["环境", "气候", "减排", "绿色", "environment", "climate", "sustainable"]):
        return "🌍"
    # 风险/挑战类
    if any(k in text_lower for k in ["风险", "挑战", "压力", "risk", "challenge", "危机", "不确定性"]):
        return "⚠️"
    # 储能/电池类
    if any(k in text_lower for k in ["储能", "电池", "battery", "storage", "bess"]):
        return "🔋"
    # 光伏/太阳能类
    if any(k in text_lower for k in ["光伏", "太阳能", "solar", "pv", "photovoltaic"]):
        return "☀️"
    # 电网/电力类
    if any(k in text_lower for k in ["电网", "电力", "grid", "power", "electricity"]):
        return "⚡"
    
    return "📢"  # 默认







# 基础样式（所有版本共享）
BASE_STYLE = """
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif; background:#F0F4F8; }
  .card { background:white; border-radius:16px; overflow:hidden; box-shadow:0 2px 12px rgba(0,0,0,0.08); }
  .header { background:linear-gradient(135deg,#1a1a2e,#0f3460); }
  .header-top { display:flex; justify-content:space-between; align-items:center; }
  .date { color:#94a3b8; }
  .focus-box { background:rgba(255,255,255,0.07); border-left:3px solid #38bdf8; }
  .focus-box p { color:#e2e8f0; line-height:1.8; }
  .section { border-bottom:1px solid #f1f5f9; }
  .section:last-child { border-bottom:none; }
  .region-tag { background:#0f3460; color:white; font-weight:500; border-radius:20px; }
  .insight { color:#0369a1; background:#f0f9ff; border-left:3px solid #38bdf8; line-height:1.7; }
  .news-list { list-style:none; padding-left:0; margin:0; }
  .news-list li { margin-bottom:8px; }
  .news-title { font-size:14px; font-weight:500; color:#1e293b; line-height:1.4; }
  .news-importance { font-size:12px; color:#ea580c; background:#f9fafb; border-radius:4px; border-left:3px solid #9ca3af; line-height:1.4; padding:4px 8px; margin-top:2px; }
  .footer { display:flex; justify-content:space-between; align-items:center; color:#94a3b8; background:#f8fafc; border-top:1px solid #f1f5f9; }
  .footer-left { flex:1; white-space:normal; word-wrap:break-word; }
  .footer-right { flex-shrink:0; font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif; }
"""
  





def _format_region_name(region):
    """格式化区域名称：将“中非及北非其他”显示为“中非”"""
    return "中非" if region == "中非及北非其他" else region

def render_overview_html(data):
    """渲染概览HTML（普通版）"""
    sections_html = ""
    for sec in data["news_sections"]:
        region_display = _format_region_name(sec['region'])
        news_html = ""
        for item in sec.get("news", []):
            emoji = _get_importance_emoji(item['importance'])
            news_html += f"""
            <li>
                <div class="news-title">{item['title']}</div>
                <div class="news-importance">{emoji} {item['importance']}</div>
            </li>
            """
     
        sections_html += f"""
        <div class="section">
          <div class="region-header">
            <span class="region-tag">{region_display}</span>
          </div>
          <div class="insight">💡 {sec['market_insight']}</div>
          <ul class="news-list">{news_html}</ul>
        </div>"""

    # 普通版特定样式
    specific_style = """
    body { width:820px; padding:28px; }
    .header { padding:24px 28px; }
    .header h1 { font-size:24px; font-weight:600; color:white; }
    .date { font-size:15px; }
    .focus-box { padding:14px 16px; }
    .focus-box p { font-size:15px; }
    .body { padding:20px 28px; }
    .section { padding:16px 0; }
    .region-tag { font-size:14px; padding:4px 14px; }
    .insight { font-size:14px; padding:10px 14px; margin:8px 0 10px; }
    .news-list li { margin-bottom:12px; }
    .news-title { font-size:15px; }
    .news-importance { font-size:13px; padding:6px 10px; margin-top:4px; }
    .footer { padding:14px 16px; font-size:12px; }
    .footer-right { margin-left:10px; font-size:12px; }
    """

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
{BASE_STYLE}
{specific_style}
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
    <span class="footer-left">Data Sources: {Config.FOOTER_SHORT}</span>
    <span class="footer-right">Created by {Config.CREATED_BY}</span>
  </div>
</div></body></html>"""

def render_overview_xhs_html(data):
    """渲染概览HTML（小红书版）"""
    sections_html = ""
    for sec in data["news_sections"]:
        region_display = _format_region_name(sec['region'])
        news_html = ""
        for item in sec.get("news", []):
            emoji = _get_importance_emoji(item['importance'])
            news_html += f"""
            <li>
                <div class="news-title">{item['title']}</div>
                <div class="news-importance">{emoji} {item['importance']}</div>
            </li>
            """
     
        sections_html += f"""
        <div class="section">
          <div class="region-header">
            <span class="region-tag">{region_display}</span>
          </div>
          <div class="insight">💡 {sec['market_insight']}</div>
          <ul class="news-list">{news_html}</ul>
        </div>"""

    # 小红书版特定样式
    specific_style = """
    body { width:1242px; padding:48px; }
    .header { padding:40px 48px; }
    .header h1 { font-size:32px; font-weight:600; color:white; }
    .date { font-size:20px; }
    .focus-box { padding:20px 24px; border-left:4px solid #38bdf8; }
    .focus-box p { font-size:20px; }
    .body { padding:32px 48px; }
    .section { padding:24px 0; }
    .region-tag { font-size:18px; padding:5px 18px; }
    .insight { font-size:18px; padding:14px 18px; margin:12px 0 16px; border-left:4px solid #38bdf8; }
    .news-list li { margin-bottom:16px; }
    .news-title { font-size:20px; }
    .news-importance { font-size:17px; padding:8px 12px; margin-top:6px; border-left:4px solid #9ca3af; }
    .footer { padding:20px 24px; font-size:13px; }
    .footer-right { margin-left:15px; font-size:13px; }
    """

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
{BASE_STYLE}
{specific_style}
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
    <span class="footer-left">Data Sources: {Config.FOOTER_SHORT}</span>
    <span class="footer-right">Created by {Config.CREATED_BY}</span>
  </div>
</div></body></html>"""

def render_region_html(sec, date_str, sources_used=""):
    """渲染区域HTML（普通版）"""
    color_map = {
        "北非及中东":"#b45309","南亚":"#15803d","东南亚":"#0e7490",
        "东亚":"#1d4ed8","西欧":"#6d28d9","南欧":"#be185d",
        "北欧":"#0369a1","东欧":"#4d7c0f","北美":"#7c2d12",
        "拉丁美洲":"#065f46","大洋洲":"#1e40af",
        "西非":"#92400e","东非":"#065f46","非洲南部":"#1e3a5f",
        "中亚":"#7c3aed","俄罗斯及高加索":"#991b1b","中非及北非其他":"#854d0e",
    }
    accent = color_map.get(sec["region"], "#0f3460")
    region_display = _format_region_name(sec['region'])
    
    news_html = ""
    for item in sec.get("news", []):
        emoji = _get_importance_emoji(item['importance'])
        news_html += f"""
        <li>
            <div class="news-title">{item['title']}</div>
            <div class="news-importance">{emoji} {item['importance']}</div>
        </li>
        """
    
    footer_src = sources_used if sources_used else Config.FOOTER_SHORT

    # 区域普通版特定样式（覆盖 header 颜色等）
    specific_style = f"""
    body {{ width:820px; padding:28px; }}
    .header {{ background:{accent}; padding:22px 28px; display:flex; justify-content:space-between; align-items:flex-start; }}
    .header-left h1 {{ color:white; font-size:19px; font-weight:600; }}
    .header-right {{ color:rgba(255,255,255,0.6); font-size:12px; }}
    .body {{ padding:22px 28px; }}
    .insight {{ font-size:13px; color:{accent}; border-left:4px solid {accent}; padding:12px 16px; margin-bottom:18px; }}
    .news-title {{ font-size:13px; color:#64748b; margin-bottom:10px; font-weight:500; }}
    .news-list li {{ margin-bottom:14px; }}
    .news-title {{ font-size:14px; }}
    .news-importance {{ font-size:12px; padding:5px 8px; margin-top:3px; border-left:3px solid #9ca3af; }}
    .footer {{ padding:12px 16px; font-size:11px; }}
    .footer-right {{ margin-left:10px; }}
    """

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
{BASE_STYLE}
{specific_style}
</style></head><body>
<div class="card">
  <div class="header">
    <div class="header-left">
      <h1>⚡ {region_display} · 光储电桩市场动态</h1>
    </div>
    <div class="header-right">{date_str}</div>
  </div>
  <div class="body">
    <div class="insight">💡 市场研判：{sec['market_insight']}</div>
    <div class="news-title">本期精选资讯</div>
    <ul class="news-list">{news_html}</ul>
  </div>
  <div class="footer">
    <span class="footer-left">Data Sources: {footer_src}</span>
    <span class="footer-right">Created by {Config.CREATED_BY}</span>
  </div>
</div></body></html>"""

def render_region_xhs_html(sec, date_str, sources_used=""):
    """渲染区域HTML（小红书版）"""
    color_map = {
        "北非及中东":"#b45309","南亚":"#15803d","东南亚":"#0e7490",
        "东亚":"#1d4ed8","西欧":"#6d28d9","南欧":"#be185d",
        "北欧":"#0369a1","东欧":"#4d7c0f","北美":"#7c2d12",
        "拉丁美洲":"#065f46","大洋洲":"#1e40af",
        "西非":"#92400e","东非":"#065f46","非洲南部":"#1e3a5f",
        "中亚":"#7c3aed","俄罗斯及高加索":"#991b1b","中非及北非其他":"#854d0e",
    }
    accent = color_map.get(sec["region"], "#0f3460")
    region_display = _format_region_name(sec['region'])
    
    news_html = ""
    for item in sec.get("news", []):
        emoji = _get_importance_emoji(item['importance'])
        news_html += f"""
        <li>
            <div class="news-title">{item['title']}</div>
            <div class="news-importance">{emoji} {item['importance']}</div>
        </li>
        """
    
    footer_src = sources_used if sources_used else Config.FOOTER_SHORT

    # 区域小红书版特定样式
    specific_style = f"""
    body {{ width:1242px; padding:48px; }}
    .header {{ background:{accent}; padding:40px 48px; display:flex; justify-content:space-between; align-items:flex-start; }}
    .header-left h1 {{ color:white; font-size:30px; font-weight:600; }}
    .header-right {{ color:rgba(255,255,255,0.6); font-size:20px; }}
    .body {{ padding:36px 48px; }}
    .insight {{ font-size:20px; color:{accent}; border-left:6px solid {accent}; padding:20px 24px; margin-bottom:28px; }}
    .news-title {{ font-size:20px; color:#64748b; margin-bottom:16px; font-weight:500; }}
    .news-list li {{ margin-bottom:24px; }}
    .news-title {{ font-size:21px; }}
    .news-importance {{ font-size:18px; padding:10px 14px; margin-top:6px; border-left:5px solid #9ca3af; }}
    .footer {{ padding:20px 24px; font-size:13px; }}
    .footer-right {{ margin-left:15px; }}
    """

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
{BASE_STYLE}
{specific_style}
</style></head><body>
<div class="card">
  <div class="header">
    <div class="header-left">
      <h1>⚡ {region_display} · 光储电桩市场动态</h1>
    </div>
    <div class="header-right">{date_str}</div>
  </div>
  <div class="body">
    <div class="insight">💡 市场研判：{sec['market_insight']}</div>
    <div class="news-title">本期精选资讯</div>
    <ul class="news-list">{news_html}</ul>
  </div>
  <div class="footer">
    <span class="footer-left">Data Sources: {footer_src}</span>
    <span class="footer-right">Created by {Config.CREATED_BY}</span>
  </div>
</div></body></html>"""
