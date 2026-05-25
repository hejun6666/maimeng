# Free Public Data Collection Strategy

## Success Standard

The research phase succeeds only when at least 5 effective competitors are retained.

An effective competitor should have:

- title
- ASIN or Amazon URL
- at least 3 bullets or a usable product description
- relevance to the user's product
- at least one supporting signal such as bought-past-month, Best Sellers Rank, rating, reviews, price, or image count

## Model-Led Search Inputs

Codex must provide the market-understanding inputs before this script runs:

- `researchQueries`: station-local Amazon search terms. These should come from the model's understanding of the product, marketplace, buyer language, and local terminology.
- `relevanceTerms`: short terms used by the script to filter obvious mismatches and score relevance.
- `targetCategories`: likely BSR subcategories. Matching subcategory ranks should be weighted heavily.

The script's generated queries are fallback only. The script should act as a crawler and ranker, not as the layer that decides what German, British, or category-specific buyers search for.

For DE, provide both German and English queries. For UK, use light British localisation where natural.

## Competitor Selection Rule

Prefer products with both Amazon front-end `bought in past month` signals and strong `Best Sellers Rank` / BSR signals. Specific subcategory ranks that match the user's product, such as `#2 in Baby Playards`, should carry more weight than broad category ranks such as `#396 in Baby`.

If fewer than 5 competitors have both signals, supplement with highly relevant, high-review, high-rating, image-rich, complete listings. Label which products have public monthly-bought signals, which have BSR signals, and which were selected mainly for listing completeness.

Use relevance as a hard guardrail against wrong products before ranking. A candidate should pass through when its title or BSR category matches `relevanceTerms` or `targetCategories`. Do not let an unrelated product win only because it has strong BSR or bought-past-month signals. Among relevant products, do not let weak title keyword overlap outrank strong matching-category BSR and bought-past-month signals.

Do not describe `bought in past month` as exact monthly sales. Call it `Amazon front-end public sales heat` or `Amazon displayed bought-past-month signal`.

Do not describe BSR as exact sales. Call it `Amazon front-end category rank signal` or `Best Sellers Rank signal`.

## Fetching Ladder

Use the lightest approach that works:

1. HTTP fetch with realistic headers.
2. Scrapling `Fetcher`.
3. Scrapling `DynamicFetcher` for JS-rendered pages.
4. Scrapling `StealthyFetcher` for pages with harder front-end protections.
5. Alternate URL forms: `/dp/<ASIN>`, `/gp/product/<ASIN>`, `?th=1`, desktop and mobile headers.
6. Expanded search terms if candidate count is insufficient.

Do not solve CAPTCHAs, bypass authentication, or use high-volume scraping. Cache results and add short delays.

## Scrapling Notes

Scrapling fetchers can be imported with:

```python
from scrapling.fetchers import Fetcher, DynamicFetcher, StealthyFetcher
```

Use `Fetcher.get(...)` or `StealthyFetcher.fetch(...)` depending on the route. Keep the helper script resilient by falling back to Python standard-library fetching when Scrapling is unavailable, while reporting that installing Scrapling improves robustness.
