# screenshot/generator.py
import os
import threading
import zipfile
import concurrent.futures
import logging
from utils.region_utils import safe_slug
from utils.file_utils import save_used_links

logger = logging.getLogger(__name__)

# Playwright可用性检查
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    logger.warning("Playwright 未安装，截图功能将不可用。")

def html_to_image(html_content, output_path):
    """生成普通版截图"""
    if not PLAYWRIGHT_AVAILABLE:
        logger.warning(f"  ⚠️ Playwright 不可用，无法生成截图：{output_path}")
        return

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
        logger.error(f"  ⚠️ 截图失败 {output_path}：{result['error']}")
    else:
        logger.info(f"  🖼️  已生成：{output_path}")

def html_to_image_xhs(html_content, output_path):
    """生成小红书版截图"""
    if not PLAYWRIGHT_AVAILABLE:
        logger.warning(f"  ⚠️ Playwright 不可用，无法生成截图：{output_path}")
        return

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
        logger.error(f"  ⚠️ 截图失败 {output_path}：{result['error']}")
    else:
        logger.info(f"  📱 已生成（小红书）：{output_path}")

def generate_images(data, unused_news, used_links, config):
    """生成所有图片"""
    import os
    from ..templates import render_overview_html, render_overview_xhs_html, render_region_html, render_region_xhs_html
    
    os.makedirs(config.IMAGE_DIR, exist_ok=True)
    os.makedirs(config.XHS_DIR, exist_ok=True)
    date_str = data['date'].replace('年', '-').replace('月', '-').replace('日', '')

    if not data:
        logger.info("⚠️ 无可用新闻，跳过图片生成。")
        return

    # 建立 index → 来源名映射
    index_to_source = {i + 1: row[0] for i, row in enumerate(unused_news)}
    used_indices = data.get("used_indices", [])
    all_sources_str = " · ".join(dict.fromkeys(
        index_to_source[idx] for idx in used_indices if idx in index_to_source
    ))

    tasks = [
        (render_overview_html(data),
         os.path.join(config.IMAGE_DIR, f"overview_{date_str}.png"), False),
        (render_overview_xhs_html(data),
         os.path.join(config.XHS_DIR, f"overview_xhs_{date_str}.png"), True),
    ]

    region_images = []
    xhs_region_images = []

    for sec in data["news_sections"]:
        slug = safe_slug(sec["region"])
        region_img = os.path.join(config.IMAGE_DIR, f"region_{slug}_{date_str}.png")
        region_xhs = os.path.join(config.XHS_DIR, f"region_{slug}_xhs_{date_str}.png")

        tasks.append((templates.render_region_html(sec, data["date"], all_sources_str), region_img, False))
        tasks.append((templates.render_region_xhs_html(sec, data["date"], all_sources_str), region_xhs, True))

        region_images.append(region_img)
        xhs_region_images.append(region_xhs)

    def take_shot(task):
        html_content, output_path, is_xhs = task
        if is_xhs:
            html_to_image_xhs(html_content, output_path)
        else:
            html_to_image(html_content, output_path)

    # 降低最大并发数到 2，减少内存压力
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(take_shot, t) for t in tasks]
        for f in concurrent.futures.as_completed(futures):
            try:
                f.result()
            except Exception as e:
                logger.error(f"  ⚠️ 截图任务异常：{e}")

    if used_links:
        save_used_links(used_links, config.USED_FILE)
        logger.info(f"  ✅ 已标记 {len(used_links)} 条新闻为已使用")

    # 打包区域图
    zip_region = os.path.join(config.IMAGE_DIR, f"regions_{date_str}.zip")
    with zipfile.ZipFile(zip_region, "w", zipfile.ZIP_DEFLATED) as zf:
        for img_path in region_images:
            if os.path.exists(img_path):
                zf.write(img_path, os.path.basename(img_path))
    logger.info(f"  📦 普通版区域图已打包：{zip_region}（共 {len(region_images)} 张）")

    zip_xhs = os.path.join(config.XHS_DIR, f"regions_xhs_{date_str}.zip")
    with zipfile.ZipFile(zip_xhs, "w", zipfile.ZIP_DEFLATED) as zf:
        for img_path in xhs_region_images:
            if os.path.exists(img_path):
                zf.write(img_path, os.path.basename(img_path))
    logger.info(f"  📦 小红书版区域图已打包：{zip_xhs}（共 {len(xhs_region_images)} 张）")

    for img_path in region_images + xhs_region_images:
        if os.path.exists(img_path):
            os.remove(img_path)
    logger.info("  🗑️  散装区域图已清理")

    logger.info(f"\n📁 普通版总图：{os.path.join(config.IMAGE_DIR, f'overview_{date_str}.png')}")
    logger.info(f"📦 普通版区域包：{zip_region}")
    logger.info(f"📁 小红书版总图：{os.path.join(config.XHS_DIR, f'overview_xhs_{date_str}.png')}")
    logger.info(f"📦 小红书版区域包：{zip_xhs}")
