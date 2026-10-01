"""RSS source adapter — 1 source đầu tiên cho MVP (§41: 1 source adapter)."""
from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime

import httpx

from app.discovery.base import ContentCandidate, EngagementSnapshot, SourceConfig


async def _fetch(url: str) -> str:
    async with httpx.AsyncClient(timeout=30, follow_redirects=True,
                                 headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}) as c:
        r = await c.get(url)
        r.raise_for_status()
        return r.text


def _parse_rss(xml_text: str, source_id: str) -> list[ContentCandidate]:
    root = ET.fromstring(xml_text)
    out: list[ContentCandidate] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        desc = (item.findtext("description") or "").strip()
        guid = (item.findtext("guid") or link or title).strip()
        if not guid:
            continue
        # media url: enclosure > media:content > link
        media_url = None
        enc = item.find("enclosure")
        if enc is not None and enc.get("url"):
            media_url = enc.get("url")
        if not media_url:
            for ns in ("{http://search.yahoo.com/mrss/}content", "{http://www.w3.org/2005/Atom}link"):
                el = item.find(ns)
                if el is not None and (el.get("url") or el.get("href")):
                    media_url = el.get("url") or el.get("href")
                    break
        out.append(ContentCandidate(
            external_id=hashlib.sha256(guid.encode()).hexdigest()[:32],
            source_id=source_id,
            source_url=link,
            title=title or None,
            description=desc or None,
            language=None,
            published_at=None,
            engagement=EngagementSnapshot(),
            media_url=media_url or link,
        ))
    return out


class RSSAdapter:
    async def discover(self, source_config: SourceConfig) -> list[ContentCandidate]:
        feed_url = source_config.config.get("feed_url", "")
        if not feed_url:
            return []
        xml_text = await _fetch(feed_url)
        return _parse_rss(xml_text, source_config.source_id)
