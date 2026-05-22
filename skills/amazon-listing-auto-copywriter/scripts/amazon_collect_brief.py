#!/usr/bin/env python3
"""Collect public Amazon competitor data for listing copy generation.

This script uses free public page signals only. Scrapling is optional but
recommended; the script falls back to Python's standard library fetcher.
"""

from __future__ import annotations

import json
import math
import os
import random
import re
import sys
import time
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus, urljoin
from urllib.request import Request, urlopen


MARKETPLACES = {
    "US": {"code": "US", "domain": "amazon.com", "currency": "USD", "language": "en-US", "acceptLanguage": "en-US,en;q=0.9"},
    "CA": {"code": "CA", "domain": "amazon.ca", "currency": "CAD", "language": "en-CA", "acceptLanguage": "en-CA,en;q=0.9"},
    "UK": {"code": "UK", "domain": "amazon.co.uk", "currency": "GBP", "language": "en-GB", "acceptLanguage": "en-GB,en;q=0.9"},
    "DE": {"code": "DE", "domain": "amazon.de", "currency": "EUR", "language": "de-DE", "acceptLanguage": "de-DE,de;q=0.9,en;q=0.7"},
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
]

STOP_WORDS = {
    "and", "with", "for", "the", "a", "an", "of", "to", "in", "on", "by",
    "from", "new", "pack", "set", "pcs", "piece", "pieces", "black", "white",
}


@dataclass
class FetchResult:
    url: str
    html: str
    fetcher: str
    status: int | None = None
    error: str | None = None


def normalize_marketplace(value: str | None) -> dict[str, str]:
    if not value:
        return MARKETPLACES["US"]
    v = str(value).strip().upper()
    if v in MARKETPLACES:
        return MARKETPLACES[v]
    lower = str(value).lower()
    if "amazon.ca" in lower or lower == "ca" or "canada" in lower:
        return MARKETPLACES["CA"]
    if "amazon.co.uk" in lower or lower in {"uk", "gb", "united kingdom", "britain"}:
        return MARKETPLACES["UK"]
    if "amazon.de" in lower or lower in {"de", "germany", "deutschland"}:
        return MARKETPLACES["DE"]
    return MARKETPLACES["US"]


def clean_text(value: str | None) -> str:
    if not value:
        return ""
    value = re.sub(r"<script.*?</script>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<style.*?</style>", " ", value, flags=re.I | re.S)
    value = re.sub(r"<[^>]+>", " ", value)
    value = unescape(value)
    value = value.replace("\u200c", "").replace("\u200b", "").replace("\ufeff", "")
    value = re.sub(r"\s+", " ", value).strip()
    return value


def parse_count_number(value: str) -> float:
    raw = value.strip()
    if "," in raw and "." in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif "." in raw and re.search(r"\.\d{3}(?:\D|$)", raw):
        raw = raw.replace(".", "")
    else:
        raw = raw.replace(",", "")
    return float(raw)


def extract_bought_count(text: str | None) -> int | None:
    if not text:
        return None
    text = clean_text(text)
    patterns = [
        r"([\d,.]+)\s*([KkMm]?)\+?\s+bought\s+in\s+past\s+month",
        r"([\d,.]+)\s*([KkMm]?)\+?\s+Mal\s+im\s+letzten\s+Monat\s+gekauft",
        r"im\s+letzten\s+Monat\s+([\d,.]+)\s*([KkMm]?)\+?\s+Mal\s+gekauft",
    ]
    match = None
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            break
    if not match:
        return None
    value = parse_count_number(match.group(1))
    suffix = match.group(2).lower()
    if suffix == "k":
        value *= 1000
    elif suffix == "m":
        value *= 1_000_000
    return int(value)


def extract_bsr_ranks(text: str | None) -> list[dict[str, Any]]:
    if not text:
        return []
    text = clean_text(text).replace("\xa0", " ")
    ranks: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    pattern = r"#\s*([\d,]+)\s+in\s+([^#()]{2,90}?)(?=\s*(?:\(|#|$|ASIN|Customer Reviews|Date First Available|Product Dimensions))"
    for match in re.finditer(pattern, text, flags=re.I):
        rank = int(match.group(1).replace(",", ""))
        category = re.sub(r"\s+", " ", match.group(2)).strip(" -:;,.")
        if not category or category.lower().startswith("see top"):
            continue
        key = (rank, category.lower())
        if key in seen:
            continue
        seen.add(key)
        ranks.append({"rank": rank, "category": category})
    german_pattern = r"Nr\.?\s*([\d.]+)\s+in\s+([^#()]{2,90}?)(?=\s*(?:\(|Nr\.?|$|ASIN|Kundenrezensionen|Im Angebot|Produktabmessungen))"
    for match in re.finditer(german_pattern, text, flags=re.I):
        rank = int(match.group(1).replace(".", ""))
        category = re.sub(r"\s+", " ", match.group(2)).strip(" -:;,.")
        if not category or category.lower().startswith("siehe top"):
            continue
        key = (rank, category.lower())
        if key in seen:
            continue
        seen.add(key)
        ranks.append({"rank": rank, "category": category})
    return ranks


def extract_rating(text: str | None) -> float | None:
    if not text:
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s+out\s+of\s+5\s+stars", clean_text(text), re.I)
    return float(match.group(1)) if match else None


def extract_review_count(text: str | None) -> int | None:
    if not text:
        return None
    text = clean_text(text)
    patterns = [
        r"([\d,]+)\s+(?:ratings|reviews)",
        r"id=\"acrCustomerReviewText\"[^>]*>\s*([\d,]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return int(match.group(1).replace(",", ""))
    return None


def money_from_html(html: str) -> str:
    whole = re.search(r'class="a-price-whole">\s*([\d,]+)', html)
    frac = re.search(r'class="a-price-fraction">\s*(\d{2})', html)
    if whole:
        cents = frac.group(1) if frac else "00"
        return f"{whole.group(1).replace(',', '')}.{cents}"
    offscreen = re.search(r'class="a-offscreen">\s*([$A-Z]*\s?[\d,.]+)', html)
    return clean_text(offscreen.group(1)) if offscreen else ""


def asin_from_url(url: str) -> str | None:
    match = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})", url)
    return match.group(1) if match else None


def product_terms_from_brief(brief: dict[str, Any]) -> list[str]:
    parts: list[str] = []
    for key in ("product", "category", "productType", "audience"):
        value = brief.get(key)
        if isinstance(value, str):
            parts.append(value)
    for key in ("features", "scenarios", "materials", "accessories", "keywords"):
        value = brief.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif isinstance(value, str):
            parts.append(value)
    words = re.findall(r"[a-zA-Z0-9]+", " ".join(parts).lower())
    return [w for w in words if len(w) > 2 and w not in STOP_WORDS]


def normalize_list(value: Any) -> list[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
    elif isinstance(value, str):
        items = [part.strip() for part in re.split(r"[\n,;|]+", value) if part.strip()]
    else:
        items = []
    output: list[str] = []
    seen: set[str] = set()
    for item in items:
        key = re.sub(r"\s+", " ", item).strip().lower()
        if key and key not in seen:
            seen.add(key)
            output.append(re.sub(r"\s+", " ", item).strip())
    return output


def resolve_search_queries(brief: dict[str, Any], limit: int = 12) -> list[str]:
    for key in ("researchQueries", "searchQueries", "queries"):
        queries = normalize_list(brief.get(key))
        if queries:
            return queries[:limit]
    return generate_search_queries(brief, limit=limit)


def relevance_terms_from_brief(brief: dict[str, Any]) -> list[str]:
    terms = normalize_list(brief.get("relevanceTerms"))
    if terms:
        return [term.lower() for term in terms]
    return product_terms_from_brief(brief)


def target_categories_from_brief(brief: dict[str, Any]) -> list[str]:
    return normalize_list(brief.get("targetCategories"))


def generate_search_queries(brief: dict[str, Any], limit: int = 8) -> list[str]:
    product = str(brief.get("product") or brief.get("productType") or brief.get("category") or "").strip()
    features = [str(x).strip() for x in brief.get("features", []) if str(x).strip()]
    scenarios = [str(x).strip() for x in brief.get("scenarios", []) if str(x).strip()]
    accessories = [str(x).strip() for x in brief.get("accessories", []) if str(x).strip()]
    seed_terms = [str(x).strip() for x in brief.get("keywords", []) if str(x).strip()]

    queries: list[str] = []
    if product:
        queries.append(product)
    for term in seed_terms + features[:4] + accessories[:3] + scenarios[:3]:
        if product and term.lower() not in product.lower():
            queries.append(f"{product} {term}")
    if product:
        queries.extend([
            f"best {product}",
            f"{product} for {brief.get('audience')}" if brief.get("audience") else "",
        ])
    seen = set()
    output = []
    for query in queries:
        q = re.sub(r"\s+", " ", query).strip()
        if q and q.lower() not in seen:
            seen.add(q.lower())
            output.append(q)
    return output[:limit]


def try_scrapling(url: str, mode: str = "fetcher") -> FetchResult | None:
    try:
        from scrapling.fetchers import DynamicFetcher, Fetcher, StealthyFetcher  # type: ignore
    except Exception:
        return None

    try:
        if mode == "stealth":
            page = StealthyFetcher.fetch(url, headless=True, timeout=30000)
        elif mode == "dynamic":
            page = DynamicFetcher.fetch(url, headless=True, timeout=30000)
        else:
            page = Fetcher.get(url, timeout=30)
        body = getattr(page, "body", b"")
        if isinstance(body, bytes):
            html = body.decode(getattr(page, "encoding", None) or "utf-8", errors="ignore")
        else:
            html = str(page)
        status = getattr(page, "status", None)
        if html:
            return FetchResult(url=url, html=html, fetcher=f"scrapling:{mode}", status=status)
    except Exception as exc:
        return FetchResult(url=url, html="", fetcher=f"scrapling:{mode}", error=str(exc))
    return None


def fetch_url(
    url: str,
    cache_dir: Path | None = None,
    force: bool = False,
    accept_language: str = "en-US,en;q=0.9",
) -> FetchResult:
    cache_key = re.sub(r"[^a-zA-Z0-9]+", "_", url)[:180] + ".html"
    if cache_dir:
        cache_dir.mkdir(parents=True, exist_ok=True)
        cached = cache_dir / cache_key
        if cached.exists() and not force:
            return FetchResult(url=url, html=cached.read_text(encoding="utf-8", errors="ignore"), fetcher="cache")

    for mode in ("fetcher", "dynamic", "stealth"):
        result = try_scrapling(url, mode)
        if result and result.html and not is_blocked_page(result.html):
            if cache_dir:
                (cache_dir / cache_key).write_text(result.html, encoding="utf-8")
            return result

    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": accept_language,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
            result = FetchResult(url=url, html=html, fetcher="urllib", status=getattr(resp, "status", None))
            if cache_dir and html and not is_blocked_page(html):
                (cache_dir / cache_key).write_text(html, encoding="utf-8")
            return result
    except (HTTPError, URLError, TimeoutError) as exc:
        return FetchResult(url=url, html="", fetcher="urllib", error=str(exc))


def is_blocked_page(html: str) -> bool:
    text = html.lower()
    markers = [
        "enter the characters you see below",
        "type the characters you see in this image",
        "captcha",
        "sorry, we just need to make sure you're not a robot",
    ]
    return any(marker in text for marker in markers)


def parse_search_results(html: str, domain: str) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    asin_matches = list(re.finditer(r'data-asin="([A-Z0-9]{10})"', html))
    block_starts = [m.start() for m in re.finditer(r'data-component-type="s-search-result"', html)]
    blocks: list[tuple[str, str]] = []
    for index, match in enumerate(asin_matches):
        asin = match.group(1)
        prior_starts = [pos for pos in block_starts if pos <= match.start()]
        start = prior_starts[-1] if prior_starts else max(0, match.start() - 2500)
        next_starts = [pos for pos in block_starts if pos > match.start()]
        end = next_starts[0] if next_starts else min(len(html), match.end() + 9000)
        blocks.append((html[start:end], asin))

    seen: set[str] = set()
    for block, asin in blocks:
        if not asin or asin in seen:
            continue
        seen.add(asin)
        title = ""
        title_match = re.search(r"<h2[\s\S]*?<span[^>]*>([\s\S]*?)</span>", block, re.I)
        if title_match:
            title = clean_text(title_match.group(1))
        href = ""
        href_match = re.search(r'<a[^>]+href="([^"]*(?:/dp/|/gp/product/)[A-Z0-9]{10}[^"]*)"', block, re.I)
        if href_match:
            href = urljoin(f"https://www.{domain}", unescape(href_match.group(1)))
        else:
            href = f"https://www.{domain}/dp/{asin}"
        rating = extract_rating(block)
        bought = extract_bought_count(block)
        reviews = extract_review_count(block)
        results.append({
            "asin": asin,
            "title": title,
            "url": href,
            "rating": rating,
            "reviews": reviews,
            "boughtInPastMonth": bought,
            "source": "search",
        })
    return results


def parse_listing_html(html: str, asin: str, url: str) -> dict[str, Any]:
    canonical_asin = asin_from_url(url) or asin
    title = ""
    title_match = re.search(r'id="productTitle"[^>]*>([\s\S]*?)</span>', html, re.I)
    if title_match:
        title = clean_text(title_match.group(1))
    if not title:
        og_title = re.search(r'<meta[^>]+property="og:title"[^>]+content="([^"]+)"', html, re.I)
        if og_title:
            title = clean_text(og_title.group(1))

    bullets: list[str] = []
    bullet_section = re.search(r'id="feature-bullets"([\s\S]*?)(?:id="|</ul>\s*</div>)', html, re.I)
    if bullet_section:
        raw_bullets = re.findall(r'<span[^>]+class="a-list-item"[^>]*>([\s\S]*?)</span>', bullet_section.group(1), re.I)
        bullets = [clean_text(b) for b in raw_bullets]
        bullets = [b for b in bullets if len(b) > 8 and "make sure that you are posting" not in b.lower()]

    description = ""
    desc_match = re.search(r'id="productDescription"[^>]*>([\s\S]*?)</div>', html, re.I)
    if desc_match:
        description = clean_text(desc_match.group(1))

    bought = extract_bought_count(html)
    rating = extract_rating(html)
    reviews = extract_review_count(html)
    images = len(set(re.findall(r'https://m\.media-amazon\.com/images/I/[^"\']+', html)))
    price = money_from_html(html)
    bsr_ranks = extract_bsr_ranks(html)
    brand = ""
    brand_match = re.search(r'id="bylineInfo"[^>]*>([\s\S]*?)</a>', html, re.I)
    if brand_match:
        brand = clean_text(brand_match.group(1)).replace("Visit the ", "").replace(" Store", "")

    return {
        "asin": canonical_asin,
        "url": url,
        "title": title,
        "brand": brand,
        "bullets": bullets[:8],
        "bulletCount": len(bullets),
        "description": description[:1500],
        "price": price,
        "rating": rating,
        "reviews": reviews,
        "imageCount": images,
        "boughtInPastMonth": bought,
        "hasBoughtSignal": bought is not None,
        "bestSellerRanks": bsr_ranks,
        "hasBestSellerRank": bool(bsr_ranks),
    }


def tokenize_for_match(text: str) -> set[str]:
    words = set(re.findall(r"[a-zA-Z0-9]+", text.lower()))
    lowered = text.lower()
    for term in re.split(r"[\n,;|]+", lowered):
        term = re.sub(r"\s+", " ", term).strip()
        if term:
            words.add(term)
    return words


def score_relevance(title: str, relevance_terms: list[str]) -> float:
    if not title or not relevance_terms:
        return 0.0
    title_lower = title.lower()
    title_words = tokenize_for_match(title)
    terms = [term.lower() for term in relevance_terms]
    matches = 0
    for term in terms:
        term_words = set(re.findall(r"[a-zA-Z0-9]+", term))
        if term in title_lower or (term_words and term_words <= title_words):
            matches += 1
    return matches / max(len(terms), 1)


def score_bsr_ranks(
    ranks: list[dict[str, Any]],
    relevance_terms: list[str],
    target_categories: list[str] | None = None,
) -> float:
    if not ranks:
        return 0.0
    best = 0.0
    target_categories = target_categories or []
    terms = [term.lower() for term in relevance_terms]
    targets = [target.lower() for target in target_categories]
    for item in ranks:
        rank = item.get("rank") or 0
        if rank <= 0:
            continue
        category = str(item.get("category", "")).lower()
        category_words = tokenize_for_match(category)
        target_match = any(target and target in category for target in targets)
        term_matches = 0
        for term in terms:
            term_words = set(re.findall(r"[a-zA-Z0-9]+", term))
            if term in category or (term_words and term_words <= category_words):
                term_matches += 1
        category_relevance = term_matches / max(len(terms), 1) if terms else 0.0
        specificity = min(len(category_words) / 3, 1.0)
        rank_score = max(0.0, 1.0 - (math.log10(rank) / 5))
        if target_match:
            category_weight = 1.0
        else:
            category_weight = 0.45 + category_relevance * 0.25 + specificity * 0.15
        weighted = rank_score * min(category_weight, 1.0)
        best = max(best, weighted)
    return min(best, 1.0)


def rank_candidates(
    candidates: list[dict[str, Any]],
    relevance_terms: list[str],
    target_categories: list[str] | None = None,
    desired_count: int = 5,
) -> list[dict[str, Any]]:
    ranked: list[dict[str, Any]] = []
    target_categories = target_categories or []
    for item in candidates:
        relevance = score_relevance(item.get("title", ""), relevance_terms)
        bought = item.get("boughtInPastMonth") or 0
        bought_score = min(math.log10(bought + 1) / 4, 1.0)
        rating = item.get("rating") or 0
        rating_score = max(0.0, min(rating / 5, 1.0))
        reviews = item.get("reviews") or 0
        review_score = min(math.log10(reviews + 1) / 4, 1.0)
        bsr_score = score_bsr_ranks(item.get("bestSellerRanks", []), relevance_terms, target_categories)
        completeness = 0.0
        if item.get("title"):
            completeness += 0.25
        if item.get("bulletCount", 0) >= 3:
            completeness += 0.35
        if item.get("price"):
            completeness += 0.10
        if item.get("rating"):
            completeness += 0.10
        if item.get("imageCount", 0) > 0:
            completeness += 0.10
        if item.get("description"):
            completeness += 0.10
        score = (
            bsr_score * 0.35
            + bought_score * 0.30
            + relevance * 0.12
            + ((rating_score + review_score) / 2) * 0.10
            + completeness * 0.10
            + (0.03 if item.get("hasBoughtSignal") else 0.0)
        )
        copy = dict(item)
        copy["selectionScore"] = round(score, 4)
        copy["relevanceScore"] = round(relevance, 4)
        copy["bestSellerRankScore"] = round(bsr_score, 4)
        ranked.append(copy)

    ranked.sort(
        key=lambda x: (
            x.get("selectionScore", 0),
            x.get("hasBoughtSignal", False),
            x.get("bestSellerRankScore", 0),
            x.get("boughtInPastMonth") or 0,
            x.get("reviews") or 0,
        ),
        reverse=True,
    )
    diverse: list[dict[str, Any]] = []
    seen_asins: set[str] = set()
    seen_titles: set[str] = set()
    seen_urls: set[str] = set()
    for item in ranked:
        asin = item.get("asin")
        title_key = re.sub(r"[^a-z0-9]+", " ", str(item.get("title", "")).lower()).strip()[:120]
        url_key = re.sub(r"[?&].*$", "", str(item.get("url", "")).lower())
        if asin in seen_asins or title_key in seen_titles or url_key in seen_urls:
            continue
        seen_asins.add(asin)
        seen_titles.add(title_key)
        seen_urls.add(url_key)
        diverse.append(item)
        if len(diverse) >= desired_count:
            return diverse
    return diverse


def collect_competitors(brief: dict[str, Any]) -> dict[str, Any]:
    marketplace = normalize_marketplace(brief.get("marketplace"))
    domain = marketplace["domain"]
    accept_language = marketplace.get("acceptLanguage", "en-US,en;q=0.9")
    relevance_terms = relevance_terms_from_brief(brief)
    target_categories = target_categories_from_brief(brief)
    queries = resolve_search_queries(brief)
    detail_limit = int(brief.get("detailPageLimit") or 32)
    cache_dir = Path(__file__).resolve().parent.parent / ".cache"
    candidate_map: dict[str, dict[str, Any]] = {}
    fetch_log: list[dict[str, Any]] = []

    for query in queries:
        search_url = f"https://www.{domain}/s?k={quote_plus(query)}"
        result = fetch_url(search_url, cache_dir / "search", accept_language=accept_language)
        fetch_log.append({"url": search_url, "fetcher": result.fetcher, "status": result.status, "error": result.error})
        if result.html and not is_blocked_page(result.html):
            for candidate in parse_search_results(result.html, domain):
                candidate.setdefault("query", query)
                candidate_map.setdefault(candidate["asin"], candidate)
        time.sleep(0.7)

    candidates = list(candidate_map.values())
    candidates.sort(key=lambda item: (item.get("boughtInPastMonth") or 0, item.get("reviews") or 0), reverse=True)
    listings: list[dict[str, Any]] = []
    for candidate in candidates[:detail_limit]:
        asin = candidate["asin"]
        urls = [
            candidate.get("url") or f"https://www.{domain}/dp/{asin}",
            f"https://www.{domain}/dp/{asin}",
            f"https://www.{domain}/gp/product/{asin}",
            f"https://www.{domain}/dp/{asin}?th=1",
        ]
        listing = None
        for url in dict.fromkeys(urls):
            result = fetch_url(url, cache_dir / "listing", accept_language=accept_language)
            fetch_log.append({"url": url, "fetcher": result.fetcher, "status": result.status, "error": result.error})
            if result.html and not is_blocked_page(result.html):
                parsed = parse_listing_html(result.html, asin, url)
                if parsed.get("title") or parsed.get("bulletCount", 0) > 0:
                    listing = {**candidate, **parsed}
                    for field in ("title", "rating", "reviews", "boughtInPastMonth"):
                        if not listing.get(field) and candidate.get(field):
                            listing[field] = candidate[field]
                    listing["hasBoughtSignal"] = listing.get("boughtInPastMonth") is not None
                    break
            time.sleep(0.7)
        if listing:
            listings.append(listing)
        if len(listings) >= detail_limit:
            break

    selected = rank_candidates(listings, relevance_terms, target_categories, 5)
    return {
        "marketplace": marketplace,
        "productBrief": brief,
        "searchQueries": queries,
        "querySource": "model_supplied" if normalize_list(brief.get("researchQueries") or brief.get("searchQueries") or brief.get("queries")) else "fallback_generated",
        "relevanceTerms": relevance_terms,
        "targetCategories": target_categories,
        "effectiveCompetitorCount": len(selected),
        "competitors": selected,
        "candidateCount": len(candidates),
        "fetchLog": fetch_log,
        "status": "ready" if len(selected) >= 5 else "insufficient_competitors",
        "notes": [
            "boughtInPastMonth is an Amazon front-end public sales heat signal, not exact monthly sales.",
            "bestSellerRanks are Amazon front-end category rank signals. Specific subcategory ranks should be weighted heavily when selecting competitors.",
            "Competitor-derived claims are opportunities, not confirmed product facts.",
        ],
    }


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if len(sys.argv) < 2:
        raw = sys.stdin.read().strip()
        if not raw:
            print("Usage: amazon_collect_brief.py '<product brief JSON>'", file=sys.stderr)
            print("   or: echo '<product brief JSON>' | amazon_collect_brief.py", file=sys.stderr)
            sys.exit(1)
    else:
        raw = sys.argv[1]
    try:
        brief = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        sys.exit(1)
    result = collect_competitors(brief)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["status"] != "ready":
        sys.exit(2)


if __name__ == "__main__":
    main()
