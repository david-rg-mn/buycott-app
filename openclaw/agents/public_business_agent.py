from __future__ import annotations

from dataclasses import dataclass

import requests
from bs4 import BeautifulSoup


@dataclass
class PublicBusinessSeed:
    name: str
    lat: float
    lng: float
    source_urls: list[str]
    fallback_text: str
    phone: str | None = None


@dataclass
class ExtractedBusiness:
    name: str
    lat: float
    lng: float
    extracted_text: str
    source_urls: list[str]
    phone: str | None
    is_chain: bool
    chain_name: str | None


class PublicBusinessExtractionAgent:
    ALLOWED_SOURCE_PREFIXES = ("http://", "https://")

    KNOWN_CHAIN_KEYWORDS = {
        "best buy": "Best Buy",
        "target": "Target",
        "walmart": "Walmart",
        "costco": "Costco",
        "home depot": "Home Depot",
    }

    def extract(self, seed: PublicBusinessSeed) -> ExtractedBusiness:
        collected_texts: list[str] = [seed.fallback_text.strip()]

        for source_url in seed.source_urls:
            if not source_url.startswith(self.ALLOWED_SOURCE_PREFIXES):
                continue
            html = self._safe_fetch_html(source_url)
            if not html:
                continue
            text = self._extract_visible_text(html)
            if text:
                collected_texts.append(text)

        merged_text = "\n\n".join(chunk for chunk in collected_texts if chunk)
        is_chain, chain_name = self._classify_chain(seed.name)

        return ExtractedBusiness(
            name=seed.name,
            lat=seed.lat,
            lng=seed.lng,
            extracted_text=merged_text,
            source_urls=seed.source_urls,
            phone=seed.phone,
            is_chain=is_chain,
            chain_name=chain_name,
        )

    def _safe_fetch_html(self, source_url: str) -> str | None:
        try:
            response = requests.get(source_url, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception:
            return None

    @staticmethod
    def _extract_visible_text(html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = " ".join(soup.stripped_strings)
        return text[:12000]

    def _classify_chain(self, business_name: str) -> tuple[bool, str | None]:
        name_lc = business_name.lower()
        for keyword, canonical in self.KNOWN_CHAIN_KEYWORDS.items():
            if keyword in name_lc:
                return True, canonical
        return False, None
