# utils/time_utils.py
from datetime import datetime, timedelta
import time
import logging

logger = logging.getLogger(__name__)

# 时区处理
try:
    from zoneinfo import ZoneInfo
    USE_ZONEINFO = True
except ImportError:
    try:
        import pytz
        USE_ZONEINFO = False
    except ImportError:
        USE_ZONEINFO = None

def now_cst():
    """返回上海时间，兼容 zoneinfo/pytz/固定偏移"""
    if USE_ZONEINFO is True:
        return datetime.now(ZoneInfo("Asia/Shanghai"))
    elif USE_ZONEINFO is False:
        tz = pytz.timezone("Asia/Shanghai")
        return datetime.now(tz)
    else:
        return datetime.utcnow() + timedelta(hours=8)

def parse_pub_date(entry):
    """安全地解析发布日期，返回带时区的 datetime 对象（Asia/Shanghai）"""
    try:
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            timestamp = time.mktime(entry.published_parsed)
            # 优先使用 pytz（兼容性好）
            try:
                import pytz
                tz = pytz.timezone("Asia/Shanghai")
                return datetime.fromtimestamp(timestamp, tz=tz)
            except ImportError:
                # 回退到 zoneinfo（Python 3.9+）
                from zoneinfo import ZoneInfo
                return datetime.fromtimestamp(timestamp, tz=ZoneInfo("Asia/Shanghai"))
    except Exception as e:
        logger.debug(f"日期解析失败：{e}")
        return None
    return None
