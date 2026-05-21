#!/usr/bin/env python3
"""Self-test for the Amazon listing auto-copywriter helper scripts."""

from amazon_collect_brief import (
    extract_bsr_ranks,
    extract_bought_count,
    normalize_marketplace,
    parse_listing_html,
    parse_search_results,
    rank_candidates,
)


def test_marketplace_normalization():
    assert normalize_marketplace("US")["domain"] == "amazon.com"
    assert normalize_marketplace("ca")["domain"] == "amazon.ca"
    assert normalize_marketplace(None)["code"] == "US"


def test_bought_count_parsing():
    assert extract_bought_count("1K+ bought in past month") == 1000
    assert extract_bought_count("500+ bought in past month") == 500
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
        product_terms=["baby", "playpen", "foldable", "mat"],
        desired_count=1,
    )
    assert ranked[0]["selectionScore"] > 0
    assert ranked[0]["bestSellerRankScore"] > 0


def main():
    test_marketplace_normalization()
    test_bought_count_parsing()
    test_bsr_rank_parsing()
    test_search_result_parsing()
    test_listing_parsing_and_ranking()
    print("self_test: OK")


if __name__ == "__main__":
    main()
