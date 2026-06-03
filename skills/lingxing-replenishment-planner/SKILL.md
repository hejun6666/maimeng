---
name: lingxing-replenishment-planner
description: Use when Codex needs to analyze Lingxing ERP SKU replenishment, batch Listing filtered SKU replenishment, factory order quantity, Amazon FBA/AWD stock coverage, weekly restocking, 领星ERP补货, SKU库存, 批量补货建议, 工厂下单, or cross-border ecommerce inventory planning for company users.
---

# Lingxing Replenishment Planner

## Overview

Use this skill to help company users decide which Amazon SKUs need replenishment, how much to replenish per cycle, and how many units to order from the factory. Treat Lingxing ERP as the raw data source. For daily work, prefer batch mode from `销售 > Listing` current filtered results. Single-SKU mode is only for ad hoc checks.

Do not frame the task as only for "operations". The user may be from purchasing, supply chain, product, management, or another ecommerce role.

## Entry Modes

### Batch Mode: Listing Current Filter

Use this when the user wants all SKU recommendations, current filtered results, all online SKUs, or says entering SKUs one by one is too slow.

- The user filters in `销售 > Listing` first.
- `销售 > Listing` decides which SKUs to analyze.
- Do not ask the user to paste SKU lists.
- Read or export the current Listing filtered result set, then enrich those SKUs from `仓库 > FBA库存明细`.
- Output an Excel-ready table/CSV, not long paragraphs for every SKU.

Recommended prompt:

```text
请先在 Codex 打开的领星网页进入销售 > Listing 并筛好范围。
批量分析销售 > Listing 当前筛选结果里的所有 SKU，生成补货建议表。
```

### Single-SKU Mode

Use this only when the user names one SKU/MSKU/ASIN or asks to inspect one product.

## Workflow

1. Collect the minimum business context:
   - Batch mode required context: the current `销售 > Listing` filtered page, or a clear instruction to use all currently visible/filtered Listing rows.
   - Single-SKU mode required context: SKU/MSKU/ASIN.
   - Optional: site/store only when the same SKU appears in multiple site/store rows and the correct row is ambiguous.
   - Use the current system date for the current month. Do not ask the user to enter the current month. Only use a planning month when the user voluntarily says they are planning for a future month.
   - If the user already provided promoted/main-push status, sales stability, product season, production days, freight wait, or shipping days, use those values.
   - Do not ask for a large parameter sheet up front. First read Lingxing by SKU, then ask only the one or two missing decisions that materially affect the calculation.
   - Never make the normal user fill current month, site/store, replenishment frequency, inbound delay, safety stock, stock ceiling, target stock days, MOQ, case pack, purchase-order inclusion, stockout, clearance, new-product status, promotion, ad changes, or similar fields before ERP extraction.
   - If the user gives only a SKU, start single-SKU web-page extraction immediately instead of asking clarifying questions.
   - If the user asks for batch/current filtered results, start from the current Listing page instead of asking for SKUs.

2. Read Lingxing data from the Lingxing web page opened in Codex:
   - The user should log in and operate inside the Lingxing page opened by Codex. Do not ask the user to paste passwords or account cookies into chat.
   - Use the Codex browser/browser-use tool for browser work: open Lingxing pages inside Codex, inspect state, search the SKU, scroll tables, screenshot evidence, and extract visible text.
   - If the browser tool is unavailable or automated extraction needs deterministic parsing, use `scripts/lingxing_capture.py` only as a technical fallback. Do not ask non-technical users to run this helper.
   - If automated extraction misses fields, continue with Codex web-page inspection of the same pages.
   - Never invent ERP numbers. If access or permissions block extraction, report the blocker and the exact field still needed.

3. Use the core Lingxing pages:
   - `销售 > Listing`: batch entry page and sales source. Capture MSKU/FNSKU, status, ASIN, title, today/yesterday sales, `7|14|30天销量`, category/rank if useful, owner, and visible site/store context.
   - `仓库 > FBA库存明细`: inventory enrichment page. For the Listing SKU set, match FBA total inventory, FBA sellable, and AWD available + inbound total.
   - In batch mode, try the Listing export/download button first. If export is unavailable, read the DOM/table rows across pages or visible virtual-scroll rows with the Codex browser tool.
   - Do not open purchase-order pages in the first-version flow unless the user explicitly asks to consider existing purchase orders.

4. Calculate with `scripts/replenishment_calculator.py`:
   - For single SKU, build one JSON object using extracted ERP fields and user-provided assumptions.
   - For batch mode, build a JSON array. Each item should include at least `sku`, `title`, `site`, `sales_30`, `fba_total`, `fba_sellable`, and `awd_available_inbound_total` when available.
   - Run the calculator for deterministic numbers.
   - Use the output as calculation evidence, then write a Chinese decision report.

5. Output in Chinese, with this structure:
   - For batch mode: summary counts, top urgent SKUs, Excel-ready CSV/table, and only blockers that affect rows.
   - For single-SKU mode: core conclusion, Lingxing data, calculation, factory order suggestion, weekly reference, risk notes, and blockers.
   - Manual confirmations are only for fields that block the result, such as multiple matching SKU rows or missing ERP sales/inventory data.

## Commands

Technical fallback helper to capture Lingxing visible data when the browser tool is not available or when deterministic parsing is useful. This is for Codex/maintainers, not for ordinary colleagues to run manually:

```bash
python scripts/lingxing_capture.py --sku "FL-DE12GB-A" --out capture.json
```

Calculate replenishment from JSON:

```bash
python scripts/replenishment_calculator.py --input replenishment-input.json --format text
```

Calculate batch replenishment from a JSON array and output CSV:

```bash
python scripts/replenishment_calculator.py --input batch-replenishment-input.json --format csv > batch-replenishment-output.csv
```

One-command rough-estimate example without web-page extraction:

```bash
python scripts/replenishment_calculator.py --sku "FL-DE12GB-A" --sales-30 70 --fba-total 100 --awd-total 0 --is-promoted false --sales-stability stable --production-days 15 --freight-prep-days 3 --transit-days 37 --format text
```

## Planning Parameters And Formulas

Read `references/replenishment-parameters.md` when deciding which values should come from the user, which values come from Lingxing, and how to calculate from them.

First-version formula frame:

- Overseas inventory for long-range coverage: `FBA总库存 + AWD可用+在途库存合计`.
- Immediate sellable risk should separately mention `FBA可售`.
- Use 30-day sales as the base sales reference, and use 7/14-day sales only as trend context.
- Use the production/shipping numbers from the chat if provided; otherwise mark the calculation as rough.

## Lingxing Field Guide

Read `references/lingxing-fields.md` when extracting ERP data or mapping raw labels to calculator fields.

Minimum fields for a normal SKU:

- `sales_30`: from `销售 > Listing > 7|14|30天销量`.
- `fba_total`: from `仓库 > FBA库存明细 > FBA总库存`.
- `awd_available_inbound_total`: from `仓库 > FBA库存明细 > AWD可用+在途库存合计`.
- `fba_sellable`: from `仓库 > FBA库存明细 > FBA可售`, when available.

## User Prompt Examples

Recommended batch default:

```text
请先在 Codex 打开的领星网页进入销售 > Listing 并筛好范围。
批量分析销售 > Listing 当前筛选结果里的所有 SKU，生成补货建议表。
```

Single-SKU check:

```text
使用领星 SKU 补货下单助手，分析 SKU：FL-DE12GB-A。
请从领星 ERP 读取库存和销量，判断是否需要补货、每周补货参考量，以及现在给工厂下多少订单。
```

Optional additions:

Only add these when the user already knows them. Do not ask the user to fill this as a form.

```text
这个 SKU 不是主推款，销量比较稳定。
生产大概15天，货代等3天，普船海运约37天。
```

For peak season:

```text
使用领星 SKU 补货下单助手，分析 SKU：xxx。
现在是12月，这个是主推款，按旺季备货逻辑算。
```
