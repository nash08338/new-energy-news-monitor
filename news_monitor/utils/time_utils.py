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
    """安全地解析发布日期"""
    try:
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            timestamp = time.mktime(entry.published_parsed)
            if USE_ZONEINFO is True:
                return datetime.fromtimestamp(timestamp, tz=ZoneInfo("Asia/Shanghai"))
            else:
                return datetime.utcfromtimestamp(timestamp) + timedelta(hours=8)
    except Exception as e:
        logger.debug(f"日期解析失败：{e}")
        return None
    return None
