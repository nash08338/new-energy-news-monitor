# templates/templates.py
# 更新后的渲染函数，适配新的 news 数据结构，并优化页脚
from ..config import Config

def render_overview_html(data):
    """渲染概览HTML（普通版）"""
    sections_html = ""
    for sec in data["news_sections"]:
        news_html = ""
        for item in sec.get("news", []):
            news_html += f"""
            <li>
                <div class="news-title">{item['title']}</div>
                <div class="news-importance">💡 {item['importance']}</div>
            </li>
            """
        sections_html += f"""
        <div class="section">
          <div class="region-header">
            <span class="region-tag">{sec['region']}</span>
          </div>
          <div class="insight">💡 {sec['market_insight']}</div>
          <ul class="news-list">{news_html}</ul>
        </div>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;
          background:#F0F4F8; width:820px; padding:28px; }}
  .card {{ background:white; border-radius:16px; overflow:hidden;
           box-shadow:0 2px 12px rgba(0,0,0,0.08); }}
  .header {{ background:linear-gradient(135deg,#1a1a2e,#0f3460); padding:24px 28px; }}
  .header-top {{ display:flex; justify-content:space-between;
                 align-items:center; margin-bottom:12px; }}
  .header h1 {{ color:white; font-size:24px; font-weight:600; }}
  .date {{ color:#94a3b8; font-size:15px; }}
  .focus-box {{ background:rgba(255,255,255,0.07); border-radius:10px;
                padding:14px 16px; border-left:3px solid #38bdf8; }}
  .focus-box p {{ color:#e2e8f0; font-size:15px; line-height:1.8; }}
  .body {{ padding:20px 28px; }}
  .section {{ border-bottom:1px solid #f1f5f9; padding:16px 0; }}
  .section:last-child {{ border-bottom:none; }}
  .region-tag {{ background:#0f3460; color:white; font-size:14px;
                 padding:4px 14px; border-radius:20px; font-weight:500; }}
  .insight {{ font-size:14px; color:#0369a1; background:#f0f9ff;
              border-radius:6px; padding:10px 14px; margin:8px 0 10px;
              border-left:3px solid #38bdf8; line-height:1.7; }}
  .news-list {{ list-style:none; padding-left:0; margin:0; }}
  .news-list li {{ margin-bottom:12px; }}
  .news-title {{ font-size:15px; font-weight:500; color:#1e293b; line-height:1.5; }}
  .news-importance {{ font-size:13px; color:#4b5563; background:#f9fafb;
                      padding:6px 10px; border-radius:6px; margin-top:4px;
                      border-left:3px solid #9ca3af; line-height:1.5; }}
  .footer {{ display:flex; justify-content:space-between; align-items:center;
             padding:14px 16px; font-size:12px; color:#94a3b8;
             background:#f8fafc; border-top:1px solid #f1f5f9; }}
  .footer-left {{ flex:1; white-space:normal; word-wrap:break-word; }}
  .footer-right {{ flex-shrink:0; margin-left:10px;
                   font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif; }}
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
        news_html = ""
        for item in sec.get("news", []):
            news_html += f"""
            <li>
                <div class="news-title">{item['title']}</div>
                <div class="news-importance">💡 {item['importance']}</div>
            </li>
            """
        sections_html += f"""
        <div class="section">
          <div class="region-header">
            <span class="region-tag">{sec['region']}</span>
          </div>
          <div class="insight">💡 {sec['market_insight']}</div>
          <ul class="news-list">{news_html}</ul>
        </div>"""

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;
          background:#F0F4F8; width:1242px; padding:48px; }}
  .card {{ background:white; border-radius:24px; overflow:hidden;
           box-shadow:0 4px 24px rgba(0,0,0,0.08); }}
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
  .news-list {{ list-style:none; padding-left:0; margin:0; }}
  .news-list li {{ margin-bottom:16px; }}
  .news-title {{ font-size:20px; font-weight:500; color:#1e293b; line-height:1.5; }}
  .news-importance {{ font-size:17px; color:#4b5563; background:#f9fafb;
                      padding:8px 12px; border-radius:8px; margin-top:6px;
                      border-left:4px solid #9ca3af; line-height:1.5; }}
  .footer {{ display:flex; justify-content:space-between; align-items:center;
             padding:20px 24px; font-size:13px; color:#94a3b8;
             background:#f8fafc; border-top:1px solid #f1f5f9; }}
  .footer-left {{ flex:1; white-space:normal; word-wrap:break-word; }}
  .footer-right {{ flex-shrink:0; margin-left:15px;
                   font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif; }}
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
    
    news_html = ""
    for item in sec.get("news", []):
        news_html += f"""
        <li>
            <div class="news-title">{item['title']}</div>
            <div class="news-importance">💡 {item['importance']}</div>
        </li>
        """
    
    footer_src = sources_used if sources_used else Config.FOOTER_SHORT

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;
          background:#F0F4F8; width:820px; padding:28px; }}
  .card {{ background:white; border-radius:16px; overflow:hidden;
           box-shadow:0 2px 12px rgba(0,0,0,0.08); }}
  .header {{ background:{accent}; padding:22px 28px;
             display:flex; justify-content:space-between; align-items:flex-start; }}
  .header-left h1 {{ color:white; font-size:19px; font-weight:600; }}
  .header-right   {{ color:rgba(255,255,255,0.6); font-size:12px; }}
  .body {{ padding:22px 28px; }}
  .insight {{ font-size:13px; color:{accent}; background:#f8fafc;
              border-radius:8px; padding:12px 16px; margin-bottom:18px;
              border-left:4px solid {accent}; line-height:1.7; }}
  .news-title {{ font-size:13px; color:#64748b; margin-bottom:10px; font-weight:500; }}
  .news-list {{ list-style:none; padding-left:0; margin:0; }}
  .news-list li {{ margin-bottom:14px; }}
  .news-title {{ font-size:14px; font-weight:500; color:#1e293b; line-height:1.5; }}
  .news-importance {{ font-size:12px; color:#4b5563; background:#f9fafb;
                      padding:5px 8px; border-radius:4px; margin-top:3px;
                      border-left:3px solid #9ca3af; line-height:1.5; }}
  .footer {{ display:flex; justify-content:space-between; align-items:center;
             padding:12px 16px; font-size:11px; color:#94a3b8;
             background:#f8fafc; border-top:1px solid #f1f5f9; }}
  .footer-left {{ flex:1; white-space:normal; word-wrap:break-word; }}
  .footer-right {{ flex-shrink:0; margin-left:10px;
                   font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif; }}
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
    
    news_html = ""
    for item in sec.get("news", []):
        news_html += f"""
        <li>
            <div class="news-title">{item['title']}</div>
            <div class="news-importance">💡 {item['importance']}</div>
        </li>
        """
    
    footer_src = sources_used if sources_used else Config.FOOTER_SHORT

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;
          background:#F0F4F8; width:1242px; padding:48px; }}
  .card {{ background:white; border-radius:24px; overflow:hidden;
           box-shadow:0 4px 24px rgba(0,0,0,0.08); }}
  .header {{ background:{accent}; padding:40px 48px;
             display:flex; justify-content:space-between; align-items:flex-start; }}
  .header-left h1 {{ color:white; font-size:30px; font-weight:600; }}
  .header-right   {{ color:rgba(255,255,255,0.6); font-size:20px; }}
  .body {{ padding:36px 48px; }}
  .insight {{ font-size:20px; color:{accent}; background:#f8fafc;
              border-radius:12px; padding:20px 24px; margin-bottom:28px;
              border-left:6px solid {accent}; line-height:1.8; }}
  .news-title {{ font-size:20px; color:#64748b; margin-bottom:16px; font-weight:500; }}
  .news-list {{ list-style:none; padding-left:0; margin:0; }}
  .news-list li {{ margin-bottom:24px; }}
  .news-title {{ font-size:21px; font-weight:500; color:#1e293b; line-height:1.5; }}
  .news-importance {{ font-size:18px; color:#4b5563; background:#f9fafb;
                      padding:10px 14px; border-radius:8px; margin-top:6px;
                      border-left:5px solid #9ca3af; line-height:1.5; }}
  .footer {{ display:flex; justify-content:space-between; align-items:center;
             padding:20px 24px; font-size:13px; color:#94a3b8;
             background:#f8fafc; border-top:1px solid #f1f5f9; }}
  .footer-left {{ flex:1; white-space:normal; word-wrap:break-word; }}
  .footer-right {{ flex-shrink:0; margin-left:15px;
                   font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif; }}
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
    <ul class="news-list">{news_html}</ul>
  </div>
  <div class="footer">
    <span class="footer-left">Data Sources: {footer_src}</span>
    <span class="footer-right">Created by {Config.CREATED_BY}</span>
  </div>
</div></body></html>"""
