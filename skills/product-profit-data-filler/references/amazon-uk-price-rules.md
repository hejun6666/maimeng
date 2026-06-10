# Amazon UK Price Rules

Use only Amazon UK for selling price:

```text
https://www.amazon.co.uk
amazon.co.uk
```

## Source Priority

1. Amazon UK links already present in the row.
2. Amazon UK search by product title/image-derived keywords.
3. Other public UK competitor pages only if the user explicitly allows them.

## Valid Price Candidates

Accept prices from products that:

- Visually match the row product.
- Are available/new.
- Have credible rating/review/sales signals.
- Are not obvious bundle/size mismatches.

Avoid:

- Used/refurbished prices.
- Unavailable products.
- Coupon-only or lightning-deal-only prices.
- Sponsored results that are not clearly the same product.
- Non-UK marketplaces.

## Selection Rule

Collect credible observed GBP prices and choose the middle observed price. Do not invent a price that was not observed.

Example:

```text
16.99, 26.99, 28.99 => 26.99
```

If there is an even number of candidates, choose the observed price closest to the numeric median; if tied, choose the lower middle price to avoid over-optimistic profit calculations.

## Currency And Writeback

- Prices must be GBP.
- Strip the `拢` or `£` display symbol before numeric writeback.
- Keep the Amazon UK URL for evidence and writeback when a mapped field exists.
- Do not convert Amazon UK selling price with the 9.17 exchange rate; `9.17` applies only to converting 1688 CNY purchase price to GBP purchase cost.
