# -*- coding: utf-8 -*-
"""Google Trends topic source via RSS feed (reliable, no pytrends dependency)."""

import xml.etree.ElementTree as ET

import requests

from .base import TopicCandidate, TopicSource


# Supported countries with geo codes
GEO_COUNTRIES = {
    "TR": "Türkiye",
    "DE": "Deutschland",
    "GB": "United Kingdom",
    "US": "United States",
    "ES": "España",
    "IT": "Italia",
    "FR": "France",
    "NL": "Nederland",
    "BR": "Brasil",
    "IN": "India",
    "JP": "Japan",
    "KR": "South Korea",
    "AU": "Australia",
    "CA": "Canada",
    "MX": "México",
    "AR": "Argentina",
    "SA": "Saudi Arabia",
    "AE": "UAE",
}


class GoogleTrendsSource(TopicSource):
    name = "google_trends"

    def __init__(self, config: dict = None):
        config = config or {}
        self.geo = config.get("geo", "US")

    @property
    def is_available(self) -> bool:
        return True  # RSS always available, no API key needed

    def fetch_topics(self, limit: int = 10, geo: str = None) -> list[TopicCandidate]:
        """Fetch trending topics from Google Trends RSS feed.

        Args:
            limit: Max topics to return
            geo: Country code (TR, DE, GB, US, ES, IT, etc.)
        """
        region = geo or self.geo
        url = f"https://trends.google.com/trending/rss?geo={region}"

        r = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (RE-Tube Pipeline)"},
            timeout=15,
        )
        if r.status_code != 200:
            raise RuntimeError(f"Google Trends RSS failed for {region}: {r.status_code}")

        root = ET.fromstring(r.content)
        ns = {"ht": "https://trends.google.com/trending/rss"}

        topics = []
        items = root.findall(".//item")

        for i, item in enumerate(items[:limit]):
            title_el = item.find("title")
            title = title_el.text.strip() if title_el is not None and title_el.text else ""
            if not title:
                continue

            # Extract approximate traffic if available
            traffic_el = item.find("ht:approx_traffic", ns)
            traffic_str = traffic_el.text if traffic_el is not None and traffic_el.text else "0"
            traffic_str = traffic_str.replace("+", "").replace(",", "")
            try:
                traffic = int(traffic_str)
            except ValueError:
                traffic = 0

            # Score: higher traffic = higher score (normalize to 0-1)
            score = min(1.0, max(0.1, 1.0 - (i * 0.08)))
            if traffic > 0:
                import math
                score = min(1.0, math.log10(max(traffic, 1)) / 6)

            # Description/summary
            desc_el = item.find("ht:news_item/ht:news_item_title", ns)
            summary = desc_el.text.strip() if desc_el is not None and desc_el.text else ""

            # Link
            link_el = item.find("link")
            link = link_el.text.strip() if link_el is not None and link_el.text else ""

            country_name = GEO_COUNTRIES.get(region, region)
            topics.append(TopicCandidate(
                title=title,
                source=f"google_trends/{region}",
                trending_score=score,
                summary=summary,
                url=link,
                metadata={"traffic": traffic, "country": country_name, "geo": region},
            ))

        return topics
