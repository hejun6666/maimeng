# 1688 Data Rules

Use 1688 only as the purchase and packaging data source. Do not use 1688 prices as the Amazon UK selling price.

## Search

- Start from the row product image.
- Use browser automation only if image upload/search requires it.
- Keep result candidates with high visual similarity, same product function, and credible sales/transaction signals.
- Prefer candidates with visible specs, packaging/logistics data, or rich detail pages.
- Keep the selected supplier URL for evidence and writeback when a mapped field exists.

## Candidate Scoring

Score candidates using:

- Visual similarity to row image.
- Same product category/function.
- Sales/transaction/review signals.
- Price availability.
- Package dimensions/weight availability.
- Whether variants match the row image.

Do not choose a different product only because it has complete data.

## Extraction

Extract:

- 1688 CNY price.
- SKU/default variant price when variants are available.
- Package dimensions.
- Package weight.
- Product attributes.
- Product URL.

If only product dimensions are visible, do not silently treat them as package dimensions. Mark as product size in attributes/evidence.

## Confidence Rules

- High confidence: same product type, same visual design, compatible variant, visible price, and visible package dimensions or weight.
- Medium confidence: same product type and visible price, but package data comes from detail text or logistics hints.
- Low confidence: similar category but uncertain size, variant, or material.
- Stop before writeback when all candidates are low confidence.

## Package Rules

- Normalize millimeters to centimeters.
- Normalize grams to kilograms.
- Keep dimensions in `L x W x H cm` order when source order is clear.
- If source order is unclear, preserve the observed order and mention the uncertainty in evidence.

## Conversion

For UK workflow:

```text
purchase_price_gbp = 1688_price_cny / 9.17
```

Round to two decimals unless the target table uses another format.
