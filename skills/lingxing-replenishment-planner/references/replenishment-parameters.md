# Replenishment Parameters

## Core Goal

For a single SKU or a batch of Listing filtered SKUs, answer:

- Is overseas inventory enough under the user's assumptions?
- Should the company replenish now?
- If shipping weekly, how many units should be replenished as a reference?
- How many units should be ordered from the factory now?
- Which inputs still need human confirmation?

## What Comes From Lingxing

Use Lingxing ERP as the raw data source for objective SKU data:

- Batch SKU scope and recent sales, preferably 7/14/30 day sales from the current filtered result set in `销售 > Listing`.
- FBA inventory from `仓库 > FBA库存明细`.
- AWD available + inbound total from `仓库 > FBA库存明细`.
- Purchase/inbound quantities only when the user explicitly asks to consider existing orders.

Do not invent ERP numbers. If a field cannot be read, say exactly which field is missing.

## What Should Come From The User

Do not ask the user to fill a full parameter sheet before reading Lingxing. Start with SKU, then ask only when needed.

Required from the user:

- Batch mode: current `销售 > Listing` filtered result set.
- Single-SKU mode: SKU/MSKU/ASIN.

Optional, only when ambiguous or material:

- Whether the SKU is promoted/main-push.
- Product peak season/low season window.
- Whether sales are stable.
- Factory production days.
- Freight forwarder prep/wait days.
- Transport method and transport days.
- Site/store only if Lingxing returns multiple matching rows for the same SKU.

If the user already wrote these in the chat, use the chat values. Do not ask again.

Current month is not a user input. Use the current system date automatically. Only use a different planning month when the user voluntarily says they are planning for a future month.

For batch mode, do not ask the user to paste all SKUs. The SKU set should come from Listing's current filters or export.

## Rough Estimate Defaults

Only use defaults when the user asks for a first-pass estimate or does not know the value. Mark them as assumptions in the report.

Example defaults from the current business discussion:

- Factory production: 15 days.
- Freight forwarder prep/wait: 3 days.
- Normal ocean shipping: 37 days.
- Internal stock judgment uses the current company rough-cut thresholds, but do not ask normal users to enter inbound delay, safety stock, stock ceiling, target stock days, MOQ, case pack, purchase orders, stockout, clearance, new-product status, promotion, or ad changes in the first-version flow.

The user can override any of these in the chat.

## Formula Framework

Inventory:

```text
overseas_inventory = FBA总库存 + AWD可用+在途库存合计
```

Sales:

```text
base_daily_sales = recent_30_day_sales / 30
forecast_daily_sales = base_daily_sales * season_multiplier
```

Lead time:

```text
lead_time_days = production_days + freight_prep_days + transit_days
```

Coverage:

```text
current_stock_days = overseas_inventory / forecast_daily_sales
```

Order need:

```text
target_inventory = forecast_daily_sales * target_stock_days
raw_factory_order_qty = max(0, target_inventory - overseas_inventory)
```

## Example Season Multipliers

Use these only as an example/default when the user asks for rough seasonal planning and does not provide a product-specific multiplier:

| Month | Promoted/main-push SKU | Non-promoted SKU |
| --- | ---: | ---: |
| 10-11 | 2.0 | 1.5 |
| 12 | 4.0 | 2.0-2.5 |
| Other months | 1.0 | 1.0 |

If the user provides a product-specific season window or multiplier, use the user's value.

## Report Requirements

Separate facts, user inputs, and assumptions:

- `Lingxing data`: numbers read from ERP.
- `User inputs`: values provided in the chat.
- `Assumptions`: only defaults that help explain the result; do not present internal stock thresholds as fields the user should fill.
- `Calculation`: formulas and final numbers. For batch mode, use one row per SKU.
- `Manual confirmations`: only blockers such as multiple matching SKU rows or missing ERP sales/inventory data.
