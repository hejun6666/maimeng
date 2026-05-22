#!/usr/bin/env python3
"""Self-test for the Amazon listing auto-copywriter helper scripts."""

from amazon_collect_brief import (
    extract_bsr_ranks,
    extract_bought_count,
    normalize_marketplace,
    parse_listing_html,
    parse_search_results,
    rank_candidates,
    relevance_terms_from_brief,
    resolve_search_queries,
    target_categories_from_brief,
)


def test_marketplace_normalization():
    assert normalize_marketplace("US")["domain"] == "amazon.com"
    assert normalize_marketplace("ca")["domain"] == "amazon.ca"
    assert normalize_marketplace("UK")["domain"] == "amazon.co.uk"
    assert normalize_marketplace("amazon.de")["domain"] == "amazon.de"
    assert normalize_marketplace(None)["code"] == "US"


def test_chinese_marketplace_normalization():
    assert normalize_marketplace("美国站")["domain"] == "amazon.com"
    assert normalize_marketplace("加拿大站")["domain"] == "amazon.ca"
    assert normalize_marketplace("英国站")["domain"] == "amazon.co.uk"
    assert normalize_marketplace("德国站")["domain"] == "amazon.de"
    assert normalize_marketplace("Amazon 德国")["domain"] == "amazon.de"


def test_bought_count_parsing():
    assert extract_bought_count("1K+ bought in past month") == 1000
    assert extract_bought_count("500+ bought in past month") == 500
    assert extract_bought_count("1.000+ Mal im letzten Monat gekauft") == 1000
    assert extract_bought_count("No badge here") is None


def test_bsr_rank_parsing():
    html = """
    <tr><th>Best Sellers Rank</th>
      <td>#396 in Baby (See Top 100 in Baby)<br>#2 in Baby Playards</td>
    </tr>
    """
    ranks = extract_bsr_ranks(html)
    assert ranks == [
        {"rank": 396, "category": "Baby"},
        {"rank": 2, "category": "Baby Playards"},
    ]
    german = extract_bsr_ranks("Amazon Bestseller-Rang: Nr. 1 in Textmarker")
    assert german == [{"rank": 1, "category": "Textmarker"}]


def test_german_listing_signal_parsing():
    html = """
    <span id="productTitle">Textmarker Set Pastellfarben</span>
    <span>4,6 von 5 Sternen</span>
    <span id="acrCustomerReviewText">1.234 Sternebewertungen</span>
    <span class="a-price-whole">8</span><span class="a-price-fraction">99</span>
    <span>1.000+ Mal im letzten Monat gekauft</span>
    <tr><th>Amazon Bestseller-Rang</th><td>Nr. 1 in Textmarker</td></tr>
    """
    listing = parse_listing_html(html, "B0TEXTMARK", "https://www.amazon.de/dp/B0TEXTMARK")
    assert listing["rating"] == 4.6
    assert listing["reviews"] == 1234
    assert listing["price"] == "8.99"
    assert listing["boughtInPastMonth"] == 1000
    assert listing["bestSellerRanks"] == [{"rank": 1, "category": "Textmarker"}]


def test_model_supplied_research_inputs_take_priority():
    brief = {
        "marketplace": "DE",
        "product": "荧光笔",
        "researchQueries": ["Textmarker", "Leuchtmarker", "Textmarker", "highlighter pens"],
        "relevanceTerms": ["textmarker", "leuchtmarker", "highlighter"],
        "targetCategories": ["Textmarker", "Marker & Textmarker"],
    }
    assert resolve_search_queries(brief) == ["Textmarker", "Leuchtmarker", "highlighter pens"]
    assert relevance_terms_from_brief(brief) == ["textmarker", "leuchtmarker", "highlighter"]
    assert target_categories_from_brief(brief) == ["Textmarker", "Marker & Textmarker"]


def test_search_result_parsing():
    html = """
    <div data-component-type="s-search-result" data-asin="B0ABC12345">
      <h2><a href="/Example-Product/dp/B0ABC12345"><span>Foldable Baby Playpen with Mat</span></a></h2>
      <span>1K+ bought in past month</span>
      <span class="a-icon-alt">4.6 out of 5 stars</span>
      <span class="a-size-base s-underline-text">128</span>
    </div>
    """
    results = parse_search_results(html, "amazon.com")
    assert results[0]["asin"] == "B0ABC12345"
    assert results[0]["boughtInPastMonth"] == 1000
    assert "Baby Playpen" in results[0]["title"]


def test_listing_parsing_and_ranking():
    html = """
    <span id="productTitle">Foldable Baby Playpen with Mat, 50 x 50 Inch</span>
    <div id="feature-bullets">
      <span class="a-list-item">Large play area for crawling and standing practice.</span>
      <span class="a-list-item">Foldable frame for storage and travel.</span>
      <span class="a-list-item">Breathable mesh sides keep visibility clear.</span>
      <span class="a-list-item">Includes soft mat and four pull rings.</span>
      <span class="a-list-item">Works for living rooms, patios, and playrooms.</span>
    </div>
    <span class="a-price-whole">129</span><span class="a-price-fraction">99</span>
    <span>4.5 out of 5 stars</span>
    <span id="acrCustomerReviewText">240 ratings</span>
    <span>500+ bought in past month</span>
    <tr><th>Best Sellers Rank</th>
      <td>#396 in Baby (See Top 100 in Baby)<br>#2 in Baby Playards</td>
    </tr>
    """
    listing = parse_listing_html(html, "B0ABC12345", "https://www.amazon.com/dp/B0ABC12345")
    assert listing["bulletCount"] == 5
    assert listing["boughtInPastMonth"] == 500
    assert listing["bestSellerRanks"][1]["rank"] == 2
    assert listing["bestSellerRanks"][1]["category"] == "Baby Playards"
    ranked = rank_candidates(
        [listing],
        relevance_terms=["baby", "playpen", "foldable", "mat"],
        target_categories=["Baby Playards"],
        desired_count=1,
    )
    assert ranked[0]["selectionScore"] > 0
    assert ranked[0]["bestSellerRankScore"] > 0


def test_bsr_and_bought_drive_competitor_selection():
    strong_category = {
        "asin": "B0STRONG001",
        "title": "Aesthetic Highlighter Pens Chisel Tip Assorted Colors",
        "boughtInPastMonth": 10000,
        "bestSellerRanks": [{"rank": 2, "category": "Liquid Highlighters"}],
        "rating": 4.6,
        "reviews": 800,
        "bulletCount": 5,
        "price": "8.99",
        "imageCount": 8,
    }
    review_heavy = {
        "asin": "B0REVIEWS01",
        "title": "Generic Office Marker Pens",
        "boughtInPastMonth": None,
        "bestSellerRanks": [{"rank": 1200, "category": "Office Products"}],
        "rating": 4.8,
        "reviews": 50000,
        "bulletCount": 5,
        "price": "5.99",
        "imageCount": 8,
    }
    ranked = rank_candidates(
        [review_heavy, strong_category],
        relevance_terms=["highlighter", "marker"],
        target_categories=["Liquid Highlighters"],
        desired_count=2,
    )
    assert ranked[0]["asin"] == "B0STRONG001"


def test_relevance_guardrail_blocks_wrong_category_winner():
    irrelevant_bestseller = {
        "asin": "B0DOGTOY001",
        "title": "Dog Chew Toy for Aggressive Chewers",
        "query": "highlighter pens",
        "boughtInPastMonth": 20000,
        "hasBoughtSignal": True,
        "bestSellerRanks": [{"rank": 1, "category": "Pet Supplies"}],
        "rating": 4.8,
        "reviews": 50000,
        "bulletCount": 5,
        "price": "9.99",
        "imageCount": 8,
    }
    relevant_listing = {
        "asin": "B0HIGHLIGHT",
        "title": "Chisel Tip Highlighter Pens Assorted Colors",
        "query": "highlighter pens",
        "boughtInPastMonth": None,
        "hasBoughtSignal": False,
        "bestSellerRanks": [],
        "rating": 4.5,
        "reviews": 500,
        "bulletCount": 5,
        "price": "6.99",
        "imageCount": 8,
    }
    ranked = rank_candidates(
        [irrelevant_bestseller, relevant_listing],
        relevance_terms=["highlighter", "chisel tip"],
        target_categories=["Liquid Highlighters"],
        desired_count=2,
    )
    assert [item["asin"] for item in ranked] == ["B0HIGHLIGHT"]


def test_fetch_url_passes_accept_language_to_scrapling(monkeypatch=None):
    import amazon_collect_brief as module

    calls = []
    original = module.try_scrapling

    def fake_try_scrapling(url, mode="fetcher", accept_language="en-US,en;q=0.9"):
        calls.append((url, mode, accept_language))
        return module.FetchResult(url=url, html="<html>ok</html>", fetcher="fake")

    try:
        module.try_scrapling = fake_try_scrapling
        result = module.fetch_url(
            "https://www.amazon.de/s?k=Textmarker",
            accept_language="de-DE,de;q=0.9,en;q=0.7",
        )
    finally:
        module.try_scrapling = original

    assert result.fetcher == "fake"
    assert calls[0][2] == "de-DE,de;q=0.9,en;q=0.7"


def main():
    test_marketplace_normalization()
    test_chinese_marketplace_normalization()
    test_bought_count_parsing()
    test_bsr_rank_parsing()
    test_german_listing_signal_parsing()
    test_model_supplied_research_inputs_take_priority()
    test_search_result_parsing()
    test_listing_parsing_and_ranking()
    test_bsr_and_bought_drive_competitor_selection()
    test_relevance_guardrail_blocks_wrong_category_winner()
    test_fetch_url_passes_accept_language_to_scrapling()
    print("self_test: OK")


if __name__ == "__main__":
    main()
