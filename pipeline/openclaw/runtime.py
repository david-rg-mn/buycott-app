from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
import random
import re
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

import httpx

try:
    from bs4 import BeautifulSoup
except Exception:  # pragma: no cover - optional runtime dependency
    BeautifulSoup = None  # type: ignore[assignment]

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0.0.0 Safari/537.36"
)
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
MODALITIES = ("html", "spa", "pdf", "image", "api", "social")
MENU_KEYWORDS = {
    "menu",
    "breakfast",
    "lunch",
    "dinner",
    "brunch",
    "dessert",
    "specials",
    "appetizer",
    "drinks",
    "beverage",
}
PRICE_RE = re.compile(r"(?:[$€£]\s?\d{1,3}(?:[.,]\d{2})?)|(?:\d{1,3}(?:[.,]\d{2})\s?(?:usd|eur|gbp))", re.I)
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE_RE = re.compile(r"(?:\+?\d[\d\-\s().]{7,}\d)")
HANDLE_RE = re.compile(r"@[A-Za-z0-9_.]{2,64}")
WHITESPACE_RE = re.compile(r"\s+")
TOKEN_RE = re.compile(r"[a-z0-9]+")
DIETARY_TAGS = {
    "vegan": "vegan",
    "vegetarian": "vegetarian",
    "gluten free": "gluten-free",
    "gluten-free": "gluten-free",
    "halal": "halal",
    "kosher": "kosher",
    "organic": "organic",
    "dairy free": "dairy-free",
    "dairy-free": "dairy-free",
}
SOURCE_TRUST = {
    "api": 92.0,
    "website": 84.0,
    "ordering_platform": 78.0,
    "directory": 74.0,
    "pdf": 80.0,
    "image": 68.0,
    "social": 58.0,
}
ORDERING_DOMAINS = {
    "toasttab.com",
    "chownow.com",
    "squarespace.com",
    "square.site",
    "squareup.com",
    "doordash.com",
    "ubereats.com",
    "grubhub.com",
}
SOCIAL_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "x.com",
    "twitter.com",
}


def normalize_text(value: str) -> str:
    return " ".join(WHITESPACE_RE.split(value.strip().lower()))


def sanitize_public_text(value: str) -> str:
    sanitized = EMAIL_RE.sub("[redacted-email]", value)
    sanitized = PHONE_RE.sub("[redacted-phone]", sanitized)
    sanitized = HANDLE_RE.sub("[redacted-handle]", sanitized)
    return " ".join(WHITESPACE_RE.split(sanitized.strip()))


def text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def content_hash(payload: bytes | str) -> str:
    raw = payload if isinstance(payload, bytes) else payload.encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def detect_dietary_tags(text: str) -> list[str]:
    lower = normalize_text(text)
    tags: list[str] = []
    for needle, tag in DIETARY_TAGS.items():
        if needle in lower and tag not in tags:
            tags.append(tag)
    return tags


def credibility_score(*, source_type: str, extraction_confidence: float, modality: str) -> float:
    base = SOURCE_TRUST.get(source_type, 62.0)
    modality_bonus = {
        "pdf": 3.0,
        "api": 5.0,
        "spa": 1.5,
        "html": 2.0,
        "image": -2.5,
        "social": -4.0,
    }.get(modality, 0.0)
    score = base + modality_bonus + (extraction_confidence * 12.0)
    return max(0.0, min(100.0, round(score, 2)))


def _host_from_url(url: str) -> str:
    return (urlparse(url).netloc or "").lower()


def _url_path(url: str) -> str:
    return (urlparse(url).path or "").lower()


def _text_tokens(value: str) -> list[str]:
    return TOKEN_RE.findall(value.lower())


def _safe_float(value: str | float | int | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, (float, int)):
        return float(value)
    candidate = value.strip().replace("$", "")
    if not candidate:
        return None
    try:
        return float(candidate)
    except ValueError:
        return None


@dataclass(slots=True)
class SourceCandidate:
    source_url: str
    source_type: str
    discovered_from: str = "business_profile"
    source_snippet: str = ""


@dataclass(slots=True)
class HttpProbe:
    source_url: str
    final_url: str
    status_code: int
    content_type: str
    text_sample: str
    bytes_sample: bytes
    headers: dict[str, str]
    attempts: int


@dataclass(slots=True)
class RouteDecision:
    source: SourceCandidate
    scores: dict[str, float]
    reasons: dict[str, list[str]]
    spawn_modalities: list[str]
    primary_modality: str
    probe: HttpProbe | None = None


@dataclass(slots=True)
class EvidenceClaim:
    source_type: str
    modality: str
    source_url: str
    source_snippet: str
    claim_text: str
    extraction_confidence: float
    credibility_score: float
    content_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class MenuItemDraft:
    source_type: str
    modality: str
    source_url: str
    source_snippet: str
    section: str | None
    item_name: str
    description: str | None
    price: float | None
    currency: str
    dietary_tags: list[str]
    raw_text: str
    extraction_confidence: float
    credibility_score: float
    content_hash: str | None = None


@dataclass(slots=True)
class ScrapeResult:
    modality: str
    source: SourceCandidate
    status_code: int
    attempts: int
    content_hash: str | None
    claims: list[EvidenceClaim]
    menu_items: list[MenuItemDraft]
    raw_summary: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SpawnTask:
    command: str
    agent_name: str
    source_url: str
    source: SourceCandidate
    future: Future[ScrapeResult]


class RetryingHttpClient:
    def __init__(self, timeout_seconds: float = 25.0, max_attempts: int = 4, base_backoff_seconds: float = 1.0):
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.base_backoff_seconds = base_backoff_seconds
        self._client = httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": DEFAULT_USER_AGENT},
        )

    def close(self) -> None:
        self._client.close()

    def _sleep_backoff(self, attempt: int) -> None:
        sleep_for = self.base_backoff_seconds * (2 ** (attempt - 1))
        jitter = random.uniform(0.0, 0.35)
        time.sleep(sleep_for + jitter)

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> tuple[httpx.Response, int]:
        attempt = 0
        while True:
            attempt += 1
            try:
                response = self._client.request(method=method, url=url, headers=headers, json=json_body)
            except httpx.HTTPError:
                if attempt >= self.max_attempts:
                    raise
                self._sleep_backoff(attempt)
                continue

            if response.status_code in RETRYABLE_STATUS_CODES and attempt < self.max_attempts:
                self._sleep_backoff(attempt)
                continue

            return response, attempt

    def probe(self, url: str) -> HttpProbe:
        response, attempts = self.request("GET", url)
        payload = response.content[:250_000]
        content_type = response.headers.get("content-type", "").lower()

        sample_text = ""
        if "text" in content_type or "json" in content_type or "xml" in content_type or "html" in content_type:
            sample_text = payload.decode("utf-8", errors="ignore")

        return HttpProbe(
            source_url=url,
            final_url=str(response.url),
            status_code=response.status_code,
            content_type=content_type,
            text_sample=sample_text,
            bytes_sample=payload,
            headers={k.lower(): v for k, v in response.headers.items()},
            attempts=attempts,
        )


class RouterMasterAgent:
    def __init__(self, http_client: RetryingHttpClient):
        self.http_client = http_client

    def _empty_scores(self) -> dict[str, float]:
        return {modality: 0.0 for modality in MODALITIES}

    def _empty_reasons(self) -> dict[str, list[str]]:
        return {modality: [] for modality in MODALITIES}

    def _add(self, scores: dict[str, float], reasons: dict[str, list[str]], modality: str, delta: float, reason: str) -> None:
        scores[modality] += delta
        reasons[modality].append(reason)

    def _route_by_url_patterns(
        self,
        candidate: SourceCandidate,
        scores: dict[str, float],
        reasons: dict[str, list[str]],
    ) -> None:
        url = candidate.source_url.lower()
        host = _host_from_url(url)
        path = _url_path(url)

        if path.endswith(".pdf"):
            self._add(scores, reasons, "pdf", 95.0, "URL ends with .pdf")
        if path.endswith(".json") or "/api/" in path or path.endswith(".xml"):
            self._add(scores, reasons, "api", 76.0, "URL path suggests API payload")
        if path.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tiff")):
            self._add(scores, reasons, "image", 94.0, "URL looks like an image asset")
        if any(host.endswith(domain) for domain in SOCIAL_DOMAINS):
            self._add(scores, reasons, "social", 90.0, "Known social domain")
        if any(host.endswith(domain) for domain in ORDERING_DOMAINS):
            self._add(scores, reasons, "html", 50.0, "Known ordering platform domain")
            self._add(scores, reasons, "spa", 48.0, "Ordering platforms often SPA rendered")
            self._add(scores, reasons, "api", 42.0, "Ordering platforms expose structured payloads")
        if "menu" in path or "food" in path:
            self._add(scores, reasons, "html", 12.0, "URL path includes menu-like hint")
            self._add(scores, reasons, "spa", 8.0, "Menu pages may use client-side rendering")

    def _route_by_probe(
        self,
        probe: HttpProbe,
        scores: dict[str, float],
        reasons: dict[str, list[str]],
    ) -> None:
        content_type = probe.content_type
        raw_text = probe.text_sample
        raw_lower = raw_text.lower()

        if "application/pdf" in content_type or probe.bytes_sample.startswith(b"%PDF"):
            self._add(scores, reasons, "pdf", 96.0, "Content-Type or magic bytes indicate PDF")
        if content_type.startswith("image/"):
            self._add(scores, reasons, "image", 95.0, "Content-Type indicates image")
        if "application/json" in content_type or "text/json" in content_type:
            self._add(scores, reasons, "api", 92.0, "Content-Type indicates JSON API")

        if not raw_text:
            return

        keyword_hits = sum(1 for word in MENU_KEYWORDS if word in raw_lower)
        price_hits = len(PRICE_RE.findall(raw_text))
        words = max(1, len(_text_tokens(raw_text)))
        tag_mentions = sum(raw_lower.count(tag) for tag in ("vegan", "gluten", "halal", "kosher", "organic"))

        if BeautifulSoup is not None and "<html" in raw_lower:
            soup = BeautifulSoup(raw_text, "lxml")
            li_count = len(soup.select("li"))
            tr_count = len(soup.select("tr"))
            script_count = len(soup.select("script"))
            table_count = len(soup.select("table"))
            body_text = soup.get_text(" ", strip=True)
            body_len = len(body_text)
            html_len = len(raw_text)
            li_density = (li_count + tr_count + (table_count * 2)) / max(1, words)

            html_score = min(
                100.0,
                (20.0 if keyword_hits > 0 else 0.0)
                + (30.0 if price_hits > 0 else 0.0)
                + min(50.0, li_density * 900.0)
                + min(12.0, tag_mentions * 2.0),
            )
            self._add(scores, reasons, "html", html_score, "HTML menu heuristics (keywords/prices/list density)")

            # SPA detection: sparse body + heavy JS shell and app root markers.
            app_shell_markers = (
                'id="root"',
                'id="app"',
                "__next",
                "data-reactroot",
                "ng-version",
                "webpack",
                "vite",
            )
            marker_hits = sum(1 for marker in app_shell_markers if marker in raw_lower)
            script_ratio = script_count / max(1.0, (li_count + tr_count + table_count))
            sparse_shell = body_len < 350 and html_len > 2_200
            if marker_hits > 0:
                self._add(scores, reasons, "spa", 22.0 + (marker_hits * 4.0), "SPA app shell markers found")
            if sparse_shell:
                self._add(scores, reasons, "spa", 28.0, "Sparse server-rendered body with large HTML shell")
            if script_count >= 10:
                self._add(scores, reasons, "spa", 16.0, "High script-tag count")
            if script_ratio >= 2.5:
                self._add(scores, reasons, "spa", 18.0, "Script to list/table ratio suggests JS rendering")

            # If strong static menu structure exists, de-emphasize SPA.
            if li_density > 0.06 and price_hits >= 2 and marker_hits == 0:
                self._add(scores, reasons, "spa", -12.0, "Strong static menu structure reduces SPA confidence")
        else:
            # Raw text response fallback
            html_like = "<" in raw_text and ">" in raw_text
            if html_like:
                self._add(scores, reasons, "html", 18.0, "Text payload appears HTML-like")
            if keyword_hits >= 2:
                self._add(scores, reasons, "html", 22.0, "Menu keyword signals in raw text")
            if price_hits >= 2:
                self._add(scores, reasons, "html", 25.0, "Price pattern signals in raw text")

        if '"menu"' in raw_lower or '"items"' in raw_lower or '"price"' in raw_lower:
            self._add(scores, reasons, "api", 20.0, "Response includes API-like menu keys")

    def detect(self, candidate: SourceCandidate) -> RouteDecision:
        scores = self._empty_scores()
        reasons = self._empty_reasons()

        self._route_by_url_patterns(candidate, scores, reasons)
        probe: HttpProbe | None = None
        try:
            probe = self.http_client.probe(candidate.source_url)
            self._route_by_probe(probe, scores, reasons)
        except httpx.HTTPError:
            # Keep URL-based scoring as fallback.
            pass

        # Normalize scores and choose modalities.
        for key in scores:
            scores[key] = max(0.0, min(100.0, round(scores[key], 2)))

        primary_modality = max(scores.keys(), key=lambda key: scores[key])
        best_score = scores[primary_modality]

        spawn_modalities: list[str] = []
        for modality in sorted(scores, key=lambda key: scores[key], reverse=True):
            score = scores[modality]
            if score >= 55.0:
                spawn_modalities.append(modality)
                continue
            if best_score >= 35.0 and (best_score - score) <= 12.0 and score >= 30.0:
                spawn_modalities.append(modality)

        if not spawn_modalities:
            spawn_modalities = [primary_modality]

        # Guardrail: for SPA-biased routes, always include HTML when it has non-trivial support.
        # This prevents missing extractable static content when Playwright times out.
        if primary_modality == "spa" and scores.get("html", 0.0) >= 15.0 and "html" not in spawn_modalities:
            spawn_modalities.append("html")

        # Keep modality fanout bounded.
        spawn_modalities = spawn_modalities[:3]
        return RouteDecision(
            source=candidate,
            scores=scores,
            reasons=reasons,
            spawn_modalities=spawn_modalities,
            primary_modality=primary_modality,
            probe=probe,
        )


class OpenClawSessions:
    def __init__(self, max_workers: int = 6):
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="openclaw-agent")
        self._tasks: list[SpawnTask] = []

    def spawn(
        self,
        agent_name: str,
        fn: Callable[[], ScrapeResult],
        *,
        source: SourceCandidate,
    ) -> SpawnTask:
        source_url = source.source_url
        command = f"/subagents spawn {agent_name} --source-url {source_url}"
        future = self._executor.submit(fn)
        task = SpawnTask(
            command=command,
            agent_name=agent_name,
            source_url=source_url,
            source=source,
            future=future,
        )
        self._tasks.append(task)
        return task

    def drain(self) -> list[tuple[SpawnTask, ScrapeResult]]:
        completed: list[tuple[SpawnTask, ScrapeResult]] = []
        for task in self._tasks:
            try:
                result = task.future.result()
            except Exception as exc:
                modality = task.agent_name.replace("-scraper", "")
                failure_claim = EvidenceClaim(
                    source_type=task.source.source_type,
                    modality=modality,
                    source_url=task.source.source_url,
                    source_snippet=task.source.source_snippet,
                    claim_text=f"Sub-agent failure: {exc}",
                    extraction_confidence=0.0,
                    credibility_score=0.0,
                    metadata={"error": str(exc)},
                )
                result = ScrapeResult(
                    modality=modality,
                    source=task.source,
                    status_code=0,
                    attempts=0,
                    content_hash=None,
                    claims=[failure_claim],
                    menu_items=[],
                    raw_summary=f"Sub-agent error: {exc}",
                    metadata={"error": str(exc)},
                )
            completed.append((task, result))
        self._tasks.clear()
        return completed

    def close(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=False)


class BaseScraperAgent:
    modality: str = "html"

    def __init__(self, http_client: RetryingHttpClient):
        self.http_client = http_client

    def run(self, source: SourceCandidate, probe: HttpProbe | None = None) -> ScrapeResult:
        raise NotImplementedError

    def _build_claim(
        self,
        *,
        source: SourceCandidate,
        claim_text: str,
        extraction_confidence: float,
        content_hash_value: str | None,
        metadata: dict[str, Any] | None = None,
    ) -> EvidenceClaim:
        return EvidenceClaim(
            source_type=source.source_type,
            modality=self.modality,
            source_url=source.source_url,
            source_snippet=source.source_snippet,
            claim_text=claim_text,
            extraction_confidence=extraction_confidence,
            credibility_score=credibility_score(
                source_type=source.source_type,
                extraction_confidence=extraction_confidence,
                modality=self.modality,
            ),
            content_hash=content_hash_value,
            metadata=metadata or {},
        )

    def _build_menu_item(
        self,
        *,
        source: SourceCandidate,
        section: str | None,
        item_name: str,
        description: str | None,
        price: float | None,
        raw_text: str,
        extraction_confidence: float,
        content_hash_value: str | None,
    ) -> MenuItemDraft:
        return MenuItemDraft(
            source_type=source.source_type,
            modality=self.modality,
            source_url=source.source_url,
            source_snippet=source.source_snippet,
            section=section,
            item_name=item_name,
            description=description,
            price=price,
            currency="USD",
            dietary_tags=detect_dietary_tags(f"{item_name} {description or ''} {raw_text}"),
            raw_text=raw_text,
            extraction_confidence=extraction_confidence,
            credibility_score=credibility_score(
                source_type=source.source_type,
                extraction_confidence=extraction_confidence,
                modality=self.modality,
            ),
            content_hash=content_hash_value,
        )

    def _lines_to_menu_items(
        self,
        *,
        source: SourceCandidate,
        lines: list[str],
        content_hash_value: str | None,
        default_confidence: float,
    ) -> list[MenuItemDraft]:
        def collapse_repeated_prefix(text: str) -> str:
            words = text.split()
            if len(words) < 4:
                return text
            max_window = min(6, len(words) // 2)
            for window in range(max_window, 0, -1):
                if words[:window] == words[window : 2 * window]:
                    collapsed = " ".join(words[window:]).strip()
                    if collapsed:
                        return collapsed
            return text

        menu_items: list[MenuItemDraft] = []
        section: str | None = None
        seen: set[tuple[str, float | None]] = set()

        for raw_line in lines:
            line = " ".join(raw_line.split()).strip(" -|")
            if len(line) < 3:
                continue
            if len(line) < 35 and line.endswith(":"):
                section = line.rstrip(":")
                continue
            if len(line) < 28 and line.isupper():
                section = line.title()
                continue

            price_match = PRICE_RE.search(line)
            if price_match is None:
                continue

            price_text = price_match.group(0)
            parsed_price = _safe_float(re.sub(r"[^\d.]", "", price_text))
            pre_price = line[: price_match.start()].strip(" -|")
            post_price = line[price_match.end() :].strip(" -|")

            if not pre_price:
                continue

            name = collapse_repeated_prefix(pre_price)
            if section:
                section_text = " ".join(section.split()).strip(" -|:")
                if section_text:
                    stripped = re.sub(rf"^{re.escape(section_text)}\s+", "", name, flags=re.IGNORECASE).strip(" -|:")
                    if stripped:
                        name = stripped
            name = collapse_repeated_prefix(name)
            description = post_price or None
            key = (normalize_text(name), parsed_price)
            if key in seen:
                continue
            seen.add(key)
            confidence = min(1.0, default_confidence + (0.1 if description else 0.0))
            menu_items.append(
                self._build_menu_item(
                    source=source,
                    section=section,
                    item_name=name[:220],
                    description=(description[:400] if description else None),
                    price=parsed_price,
                    raw_text=line[:800],
                    extraction_confidence=confidence,
                    content_hash_value=content_hash_value,
                )
            )
        return menu_items

    def _text_claims(
        self,
        *,
        source: SourceCandidate,
        text: str,
        content_hash_value: str | None,
    ) -> list[EvidenceClaim]:
        claims: list[EvidenceClaim] = []
        normalized = normalize_text(text)
        if not normalized:
            return claims

        claim_keywords = {
            "vegan": "Mentions vegan offerings",
            "vegetarian": "Mentions vegetarian offerings",
            "gluten": "Mentions gluten-conscious offerings",
            "organic": "Mentions organic sourcing",
            "halal": "Mentions halal offering",
            "kosher": "Mentions kosher offering",
            "delivery": "Mentions delivery operations",
            "pickup": "Mentions pickup operations",
            "takeout": "Mentions takeout operations",
            "patio": "Mentions patio or outdoor seating",
            "catering": "Mentions catering services",
            "breakfast": "Mentions breakfast service window",
            "lunch": "Mentions lunch service window",
            "dinner": "Mentions dinner service window",
        }
        for keyword, statement in claim_keywords.items():
            if keyword in normalized:
                claims.append(
                    self._build_claim(
                        source=source,
                        claim_text=statement,
                        extraction_confidence=0.62,
                        content_hash_value=content_hash_value,
                        metadata={"keyword": keyword},
                    )
                )

        return claims


class HtmlScraperAgent(BaseScraperAgent):
    modality = "html"

    def run(self, source: SourceCandidate, probe: HttpProbe | None = None) -> ScrapeResult:
        if probe is None:
            response, attempts = self.http_client.request("GET", source.source_url)
            status_code = response.status_code
            html = response.text
            raw_hash = content_hash(response.content)
        else:
            status_code = probe.status_code
            html = probe.text_sample
            raw_hash = content_hash(probe.bytes_sample)
            attempts = probe.attempts

        if BeautifulSoup is None:
            claims = [
                self._build_claim(
                    source=source,
                    claim_text="Skipped HTML parsing because BeautifulSoup is unavailable.",
                    extraction_confidence=0.1,
                    content_hash_value=raw_hash,
                )
            ]
            return ScrapeResult(
                modality=self.modality,
                source=source,
                status_code=status_code,
                attempts=attempts,
                content_hash=raw_hash,
                claims=claims,
                menu_items=[],
                raw_summary="HTML parser dependency unavailable",
            )

        soup = BeautifulSoup(html, "lxml")
        candidate_lines: list[str] = []

        for selector in ("h1", "h2", "h3", "li", "tr", "p"):
            for node in soup.select(selector):
                line = node.get_text(" ", strip=True)
                if line:
                    candidate_lines.append(line)

        menu_items = self._lines_to_menu_items(
            source=source,
            lines=candidate_lines,
            content_hash_value=raw_hash,
            default_confidence=0.68,
        )

        body_text = soup.get_text(" ", strip=True)
        claims = self._text_claims(source=source, text=body_text, content_hash_value=raw_hash)
        if menu_items:
            claims.append(
                self._build_claim(
                    source=source,
                    claim_text=f"Extracted {len(menu_items)} menu item(s) from static HTML.",
                    extraction_confidence=0.72,
                    content_hash_value=raw_hash,
                    metadata={"menu_items": len(menu_items)},
                )
            )

        return ScrapeResult(
            modality=self.modality,
            source=source,
            status_code=status_code,
            attempts=attempts,
            content_hash=raw_hash,
            claims=claims,
            menu_items=menu_items,
            raw_summary=f"Parsed HTML nodes={len(candidate_lines)}, menu_items={len(menu_items)}",
            metadata={"node_lines": len(candidate_lines)},
        )


class SpaScraperAgent(BaseScraperAgent):
    modality = "spa"

    async def _render_spa(self, url: str) -> tuple[str, int]:
        from playwright.async_api import async_playwright  # type: ignore[import-not-found]

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page(user_agent=DEFAULT_USER_AGENT)
            response = await page.goto(url, wait_until="networkidle", timeout=45_000)
            html = await page.content()
            status_code = response.status if response is not None else 200
            await browser.close()
            return html, status_code

    def run(self, source: SourceCandidate, probe: HttpProbe | None = None) -> ScrapeResult:
        attempts = 1
        raw_html = ""
        status_code = 200
        fallback_reason: str | None = None

        try:
            raw_html, status_code = asyncio.run(self._render_spa(source.source_url))
        except Exception as exc:  # pragma: no cover - depends on playwright binaries/runtime
            fallback_reason = f"Playwright SPA render failed; fallback to HTML parser ({exc})"
            html_fallback = HtmlScraperAgent(self.http_client).run(source=source, probe=None)
            html_fallback.modality = self.modality  # reuse extracted content but keep trace as SPA attempt
            html_fallback.raw_summary = fallback_reason
            html_fallback.metadata["fallback"] = "html"
            return html_fallback

        raw_hash = content_hash(raw_html)
        if BeautifulSoup is None:
            claims = [
                self._build_claim(
                    source=source,
                    claim_text="Rendered SPA but parser dependencies were unavailable.",
                    extraction_confidence=0.2,
                    content_hash_value=raw_hash,
                )
            ]
            return ScrapeResult(
                modality=self.modality,
                source=source,
                status_code=status_code,
                attempts=attempts,
                content_hash=raw_hash,
                claims=claims,
                menu_items=[],
                raw_summary="SPA rendered, parser unavailable",
            )

        soup = BeautifulSoup(raw_html, "lxml")
        lines = [node.get_text(" ", strip=True) for node in soup.select("h1,h2,h3,li,tr,p") if node.get_text(" ", strip=True)]
        menu_items = self._lines_to_menu_items(
            source=source,
            lines=lines,
            content_hash_value=raw_hash,
            default_confidence=0.74,
        )
        body_text = soup.get_text(" ", strip=True)
        claims = self._text_claims(source=source, text=body_text, content_hash_value=raw_hash)

        raw_probe_text_len = len(probe.text_sample) if probe is not None else 0
        rendered_len = len(body_text)
        if rendered_len > 0 and raw_probe_text_len > 0:
            ratio = rendered_len / max(1.0, raw_probe_text_len)
            if ratio >= 1.8:
                claims.append(
                    self._build_claim(
                        source=source,
                        claim_text="SPA rendering materially increased extracted text coverage.",
                        extraction_confidence=0.7,
                        content_hash_value=raw_hash,
                        metadata={"render_ratio": round(ratio, 3)},
                    )
                )

        if menu_items:
            claims.append(
                self._build_claim(
                    source=source,
                    claim_text=f"Extracted {len(menu_items)} menu item(s) after SPA rendering.",
                    extraction_confidence=0.76,
                    content_hash_value=raw_hash,
                )
            )

        return ScrapeResult(
            modality=self.modality,
            source=source,
            status_code=status_code,
            attempts=attempts,
            content_hash=raw_hash,
            claims=claims,
            menu_items=menu_items,
            raw_summary=f"Rendered SPA lines={len(lines)}, menu_items={len(menu_items)}",
            metadata={"lines": len(lines), "fallback_reason": fallback_reason},
        )


class PdfScraperAgent(BaseScraperAgent):
    modality = "pdf"

    def _extract_pdf_text(self, payload: bytes) -> tuple[str, str]:
        # Try PyMuPDF first.
        try:
            import fitz  # type: ignore[import-not-found]

            with fitz.open(stream=payload, filetype="pdf") as doc:
                texts = [page.get_text("text") for page in doc]
            text = "\n".join(texts).strip()
            if text:
                return text, "pymupdf"
        except Exception:
            pass

        # Fallback to pdfplumber.
        try:
            import pdfplumber  # type: ignore[import-not-found]

            with pdfplumber.open(io.BytesIO(payload)) as pdf:
                pages = [page.extract_text() or "" for page in pdf.pages]
            text = "\n".join(pages).strip()
            if text:
                return text, "pdfplumber"
        except Exception:
            pass

        # Final fallback: OCR each page image if fitz and tesseract exist.
        try:
            import fitz  # type: ignore[import-not-found]
            import pytesseract  # type: ignore[import-not-found]
            from PIL import Image  # type: ignore[import-not-found]

            chunks: list[str] = []
            with fitz.open(stream=payload, filetype="pdf") as doc:
                for page in doc:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    image = Image.open(io.BytesIO(pix.tobytes("png")))
                    chunk = pytesseract.image_to_string(image)
                    if chunk:
                        chunks.append(chunk)
            return "\n".join(chunks).strip(), "ocr"
        except Exception:
            return "", "none"

    def run(self, source: SourceCandidate, probe: HttpProbe | None = None) -> ScrapeResult:
        response, attempts = self.http_client.request("GET", source.source_url)
        payload = response.content
        raw_hash = content_hash(payload)

        extracted_text, method = self._extract_pdf_text(payload)
        claims = self._text_claims(source=source, text=extracted_text, content_hash_value=raw_hash)
        lines = [line.strip() for line in extracted_text.splitlines() if line.strip()]
        menu_items = self._lines_to_menu_items(
            source=source,
            lines=lines,
            content_hash_value=raw_hash,
            default_confidence=0.66 if method == "ocr" else 0.73,
        )
        if menu_items:
            claims.append(
                self._build_claim(
                    source=source,
                    claim_text=f"Extracted {len(menu_items)} menu item(s) from PDF using {method}.",
                    extraction_confidence=0.7 if method != "ocr" else 0.58,
                    content_hash_value=raw_hash,
                    metadata={"extraction_method": method},
                )
            )
        elif extracted_text:
            claims.append(
                self._build_claim(
                    source=source,
                    claim_text=f"PDF text extracted with {method} but no confident menu line pattern was found.",
                    extraction_confidence=0.45,
                    content_hash_value=raw_hash,
                    metadata={"extraction_method": method},
                )
            )

        return ScrapeResult(
            modality=self.modality,
            source=source,
            status_code=response.status_code,
            attempts=attempts,
            content_hash=raw_hash,
            claims=claims,
            menu_items=menu_items,
            raw_summary=f"PDF parse method={method}, text_chars={len(extracted_text)}, menu_items={len(menu_items)}",
            metadata={"method": method, "text_chars": len(extracted_text)},
        )


class OcrImageScraperAgent(BaseScraperAgent):
    modality = "image"

    def _tesseract_text(self, payload: bytes) -> tuple[str, str]:
        try:
            import pytesseract  # type: ignore[import-not-found]
            from PIL import Image  # type: ignore[import-not-found]

            image = Image.open(io.BytesIO(payload))
            return pytesseract.image_to_string(image), "tesseract"
        except Exception:
            return "", "none"

    def _vision_fallback(self, payload: bytes) -> tuple[str, str]:
        endpoint = os.getenv("OPENCLAW_VISION_ENDPOINT", "").strip()
        api_key = os.getenv("OPENCLAW_VISION_API_KEY", "").strip()
        if not endpoint or not api_key:
            return "", "none"

        try:
            response, _attempts = self.http_client.request(
                "POST",
                endpoint,
                headers={"Authorization": f"Bearer {api_key}"},
                json_body={"image_base64": payload.hex()},
            )
            body = response.json()
            if isinstance(body, dict):
                text = str(body.get("text", "")).strip()
                if text:
                    return text, "vision_api"
        except Exception:
            return "", "none"
        return "", "none"

    def run(self, source: SourceCandidate, probe: HttpProbe | None = None) -> ScrapeResult:
        response, attempts = self.http_client.request("GET", source.source_url)
        payload = response.content
        raw_hash = content_hash(payload)

        extracted_text, method = self._tesseract_text(payload)
        if not extracted_text:
            extracted_text, method = self._vision_fallback(payload)

        claims = self._text_claims(source=source, text=extracted_text, content_hash_value=raw_hash)
        lines = [line.strip() for line in extracted_text.splitlines() if line.strip()]
        menu_items = self._lines_to_menu_items(
            source=source,
            lines=lines,
            content_hash_value=raw_hash,
            default_confidence=0.54 if method == "vision_api" else 0.48,
        )

        chars = len(extracted_text)
        if chars > 45:
            claims.append(
                self._build_claim(
                    source=source,
                    claim_text=f"OCR produced {chars} characters of text from image.",
                    extraction_confidence=0.5 if method == "vision_api" else 0.45,
                    content_hash_value=raw_hash,
                    metadata={"ocr_method": method, "chars": chars},
                )
            )

        return ScrapeResult(
            modality=self.modality,
            source=source,
            status_code=response.status_code,
            attempts=attempts,
            content_hash=raw_hash,
            claims=claims,
            menu_items=menu_items,
            raw_summary=f"OCR method={method}, chars={chars}, menu_items={len(menu_items)}",
            metadata={"ocr_method": method, "chars": chars},
        )


class ApiScraperAgent(BaseScraperAgent):
    modality = "api"

    def _collect_strings(self, payload: Any) -> list[str]:
        text_chunks: list[str] = []

        def _walk(node: Any) -> None:
            if isinstance(node, str):
                if len(node.strip()) >= 2:
                    text_chunks.append(node.strip())
                return
            if isinstance(node, list):
                for item in node:
                    _walk(item)
                return
            if isinstance(node, dict):
                for key, value in node.items():
                    if isinstance(key, str) and key.lower() in {"name", "title", "description", "category", "item"}:
                        _walk(value)
                    else:
                        _walk(value)

        _walk(payload)
        return text_chunks

    def _extract_menu_objects(self, payload: Any) -> list[dict[str, Any]]:
        objects: list[dict[str, Any]] = []

        def _walk(node: Any) -> None:
            if isinstance(node, list):
                for item in node:
                    _walk(item)
                return
            if not isinstance(node, dict):
                return

            lowered_keys = {str(key).lower() for key in node.keys()}
            if {"name", "price"}.issubset(lowered_keys) or {"item", "price"}.issubset(lowered_keys):
                objects.append(node)
            for value in node.values():
                _walk(value)

        _walk(payload)
        return objects

    def run(self, source: SourceCandidate, probe: HttpProbe | None = None) -> ScrapeResult:
        response, attempts = self.http_client.request("GET", source.source_url)
        raw_hash = content_hash(response.content)
        claims: list[EvidenceClaim] = []
        menu_items: list[MenuItemDraft] = []

        try:
            payload = response.json()
        except ValueError:
            payload = {"text": response.text}

        menu_objects = self._extract_menu_objects(payload)
        for obj in menu_objects:
            name = str(obj.get("name") or obj.get("item") or "").strip()
            if not name:
                continue
            description = str(obj.get("description") or obj.get("details") or "").strip() or None
            price = _safe_float(obj.get("price"))
            raw_text = json.dumps(obj, ensure_ascii=True)
            menu_items.append(
                self._build_menu_item(
                    source=source,
                    section=str(obj.get("section") or "").strip() or None,
                    item_name=name[:220],
                    description=(description[:400] if description else None),
                    price=price,
                    raw_text=raw_text[:800],
                    extraction_confidence=0.78,
                    content_hash_value=raw_hash,
                )
            )

        joined_text = "\n".join(self._collect_strings(payload))
        claims.extend(self._text_claims(source=source, text=joined_text, content_hash_value=raw_hash))
        claims.append(
            self._build_claim(
                source=source,
                claim_text=f"Structured API response yielded {len(menu_items)} item candidate(s).",
                extraction_confidence=0.74,
                content_hash_value=raw_hash,
                metadata={"structured_items": len(menu_items)},
            )
        )

        return ScrapeResult(
            modality=self.modality,
            source=source,
            status_code=response.status_code,
            attempts=attempts,
            content_hash=raw_hash,
            claims=claims,
            menu_items=menu_items,
            raw_summary=f"API parse objects={len(menu_objects)}, menu_items={len(menu_items)}",
            metadata={"objects": len(menu_objects)},
        )


class SocialScraperAgent(BaseScraperAgent):
    modality = "social"

    def _public_facebook_payload(self, source_url: str) -> tuple[dict[str, Any], int] | None:
        token = os.getenv("FACEBOOK_GRAPH_API_TOKEN", "").strip()
        if not token:
            return None

        path_parts = [part for part in _url_path(source_url).split("/") if part]
        if not path_parts:
            return None
        handle = path_parts[0]
        endpoint = f"https://graph.facebook.com/v20.0/{handle}"
        response, attempts = self.http_client.request(
            "GET",
            endpoint,
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            payload = response.json()
        except ValueError:
            return None
        if not isinstance(payload, dict):
            return None
        return payload, attempts

    def _public_instagram_payload(self, source_url: str) -> tuple[dict[str, Any], int] | None:
        token = os.getenv("INSTAGRAM_GRAPH_TOKEN", "").strip()
        business_account_id = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID", "").strip()
        if not token or not business_account_id:
            return None

        path_parts = [part for part in _url_path(source_url).split("/") if part]
        if not path_parts:
            return None
        username = path_parts[0]
        endpoint = (
            f"https://graph.facebook.com/v20.0/{business_account_id}"
            f"?fields=business_discovery.username({username}){{username,biography,website,name}}"
        )
        response, attempts = self.http_client.request(
            "GET",
            endpoint,
            headers={"Authorization": f"Bearer {token}"},
        )
        try:
            payload = response.json()
        except ValueError:
            return None
        if not isinstance(payload, dict):
            return None
        return payload, attempts

    def run(self, source: SourceCandidate, probe: HttpProbe | None = None) -> ScrapeResult:
        host = _host_from_url(source.source_url)
        claims: list[EvidenceClaim] = []
        menu_items: list[MenuItemDraft] = []
        raw_hash: str | None = None
        attempts = 0
        status_code = 0
        payload: dict[str, Any] | None = None
        provider = "none"

        if host.endswith("facebook.com"):
            result = self._public_facebook_payload(source.source_url)
            if result:
                payload, attempts = result
                provider = "facebook_graph_api"
                status_code = 200
        elif host.endswith("instagram.com"):
            result = self._public_instagram_payload(source.source_url)
            if result:
                payload, attempts = result
                provider = "instagram_graph_api"
                status_code = 200

        if payload is None:
            claims.append(
                self._build_claim(
                    source=source,
                    claim_text=(
                        "Skipped social scraping because no authorized business-account API token was configured."
                    ),
                    extraction_confidence=0.05,
                    content_hash_value=None,
                    metadata={"policy": "public-api-only"},
                )
            )
            return ScrapeResult(
                modality=self.modality,
                source=source,
                status_code=status_code,
                attempts=attempts,
                content_hash=None,
                claims=claims,
                menu_items=menu_items,
                raw_summary="Social extraction skipped: public API credentials missing.",
                metadata={"provider": provider, "policy": "public-api-only"},
            )

        payload_text = json.dumps(payload, sort_keys=True, ensure_ascii=True)
        raw_hash = content_hash(payload_text)
        candidate_text = payload_text
        claims.extend(self._text_claims(source=source, text=candidate_text, content_hash_value=raw_hash))
        claims.append(
            self._build_claim(
                source=source,
                claim_text=f"Ingested public social business metadata via {provider}.",
                extraction_confidence=0.42,
                content_hash_value=raw_hash,
                metadata={"provider": provider},
            )
        )

        return ScrapeResult(
            modality=self.modality,
            source=source,
            status_code=status_code or 200,
            attempts=max(1, attempts),
            content_hash=raw_hash,
            claims=claims,
            menu_items=menu_items,
            raw_summary=f"Social public-api extraction provider={provider}",
            metadata={"provider": provider},
        )


def build_scraper_registry(http_client: RetryingHttpClient) -> dict[str, BaseScraperAgent]:
    return {
        "html": HtmlScraperAgent(http_client=http_client),
        "spa": SpaScraperAgent(http_client=http_client),
        "pdf": PdfScraperAgent(http_client=http_client),
        "image": OcrImageScraperAgent(http_client=http_client),
        "api": ApiScraperAgent(http_client=http_client),
        "social": SocialScraperAgent(http_client=http_client),
    }


def ensure_docker_sandbox(allow_host_execution: bool) -> None:
    in_docker = Path("/.dockerenv").exists() or os.getenv("OPENCLAW_DOCKER_SANDBOX", "").strip() == "1"
    if not in_docker and not allow_host_execution:
        raise RuntimeError(
            "Sandbox policy violation: OpenClaw agents must run in Docker. "
            "Re-run inside Docker or pass --allow-host-execution for explicit override."
        )
