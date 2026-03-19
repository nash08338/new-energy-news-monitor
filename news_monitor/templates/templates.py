# templates/templates.py
# 保持原有的四个渲染函数不变，只需要修改导入的FOOTER
from ..config import Config

def render_overview_html(data):
    """渲染概览HTML（普通版）"""
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
  .news-list {{ padding-left:18px; }}
  .news-list li {{ font-size:15px; color:#334155; line-height:1.9; margin-bottom:2px; }}
  .footer {{ overflow:hidden; padding:14px 16px; font-size:12px;
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
    <span style="float:left;">Data Sources: {Config.FOOTER_SHORT}</span>
    <span style="float:right;font-size:12px;color:rgba(0,0,0,0.40);
                 font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;">Created by 香港汇展 Nash</span>
  </div>
</div></body></html>"""

def render_overview_xhs_html(data):
    """渲染概览HTML（小红书版）"""
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
  .news-list {{ padding-left:24px; }}
  .news-list li {{ font-size:19px; color:#334155; line-height:1.9; margin-bottom:4px; }}
  .footer {{ overflow:hidden; padding:20px 24px; font-size:13px;
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
    <span style="float:left;">Data Sources: {Config.FOOTER_SHORT}</span>
    <span style="float:right;font-size:13px;color:rgba(0,0,0,0.40);
                 font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;">Created by 香港汇展 Nash</span>
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
    titles_html = "".join(f"<li>{t}</li>" for t in sec["titles"])
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
  .news-list {{ padding-left:18px; }}
  .news-list li {{ font-size:14px; color:#1e293b; line-height:1.9; margin-bottom:4px; }}
  .footer {{ overflow:hidden; padding:12px 16px; font-size:11px;
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
    <span style="float:left;">Data Sources: {footer_src}</span>
    <span style="float:right;font-size:11px;color:rgba(0,0,0,0.40);
                 font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;">Created by 香港汇展 Nash</span>
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
    titles_html = "".join(f"<li>{t}</li>" for t in sec["titles"])
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
  .news-list {{ padding-left:28px; }}
  .news-list li {{ font-size:21px; color:#1e293b; line-height:2.0; margin-bottom:8px; }}
  .footer {{ overflow:hidden; padding:20px 24px; font-size:13px;
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
    <span style="float:left;">Data Sources: {footer_src}</span>
    <span style="float:right;font-size:13px;color:rgba(0,0,0,0.40);
                 font-family:'PingFang SC','Microsoft YaHei',Arial,sans-serif;">Created by 香港汇展 Nash</span>
  </div>
</div></body></html>"""
