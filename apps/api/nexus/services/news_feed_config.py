"""News feed configuration — manages the user-customisable RSS feed list.

Ported from Shadowbroker ``news_feed_config.py``.
Feeds are stored in ``apps/api/config/news_feeds.json``.
"""

from __future__ import annotations

import json
import structlog
from pathlib import Path

logger = structlog.get_logger()

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "news_feeds.json"
MAX_FEEDS = 25

DEFAULT_FEEDS: list[dict] = [
    {"name": "NPR", "url": "https://feeds.npr.org/1004/rss.xml", "weight": 4},
    {"name": "BBC", "url": "http://feeds.bbci.co.uk/news/world/rss.xml", "weight": 3},
    {"name": "AlJazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "weight": 2},
    {"name": "NYT", "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "weight": 1},
    {"name": "GDACS", "url": "https://www.gdacs.org/xml/rss.xml", "weight": 5},
    {"name": "NHK", "url": "https://www3.nhk.or.jp/nhkworld/rss/world.xml", "weight": 3},
    {"name": "CNA", "url": "https://www.channelnewsasia.com/rssfeed/8395986", "weight": 3},
    {"name": "Mercopress", "url": "https://en.mercopress.com/rss/", "weight": 3},
    {"name": "FocusTaiwan", "url": "https://focustaiwan.tw/rss", "weight": 5},
    {"name": "Kyodo", "url": "https://english.kyodonews.net/rss/news.xml", "weight": 4},
    {"name": "SCMP", "url": "https://www.scmp.com/rss/91/feed", "weight": 4},
    {"name": "The Diplomat", "url": "https://thediplomat.com/feed/", "weight": 4},
    {"name": "Stars and Stripes", "url": "https://www.stripes.com/feeds/pacific.rss", "weight": 4},
    {"name": "Yonhap", "url": "https://en.yna.co.kr/RSS/news.xml", "weight": 4},
    {"name": "Nikkei Asia", "url": "https://asia.nikkei.com/rss", "weight": 3},
    {"name": "Taipei Times", "url": "https://www.taipeitimes.com/xml/pda.rss", "weight": 4},
    {"name": "Asia Times", "url": "https://asiatimes.com/feed/", "weight": 3},
    {"name": "Defense News", "url": "https://www.defensenews.com/arc/outboundfeeds/rss/", "weight": 3},
    {"name": "Japan Times", "url": "https://www.japantimes.co.jp/feed/", "weight": 3},
]


def get_feeds() -> list[dict]:
    """Load feeds from config file, falling back to defaults."""
    try:
        if CONFIG_PATH.exists():
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            feeds = data.get("feeds", []) if isinstance(data, dict) else data
            if isinstance(feeds, list) and len(feeds) > 0:
                return feeds
    except (IOError, OSError, json.JSONDecodeError, ValueError) as exc:
        logger.warning("news_feed_config.read_failed", error=str(exc))
    return list(DEFAULT_FEEDS)


def save_feeds(feeds: list[dict]) -> bool:
    """Validate and save feeds to config file."""
    if not isinstance(feeds, list) or len(feeds) > MAX_FEEDS:
        return False
    for f in feeds:
        if not isinstance(f, dict):
            return False
        name = f.get("name", "").strip()
        url = f.get("url", "").strip()
        weight = f.get("weight", 3)
        if not name or not url:
            return False
        if not isinstance(weight, (int, float)) or weight < 1 or weight > 5:
            return False
        f["name"] = name
        f["url"] = url
        f["weight"] = int(weight)
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps({"feeds": feeds}, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return True
    except (IOError, OSError) as exc:
        logger.error("news_feed_config.write_failed", error=str(exc))
        return False


def reset_feeds() -> bool:
    """Reset feeds to defaults."""
    return save_feeds(list(DEFAULT_FEEDS))
