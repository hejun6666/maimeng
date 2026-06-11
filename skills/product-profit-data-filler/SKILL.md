---
name: product-profit-data-filler
description: Use when Codex needs to help ecommerce coworkers fill Feishu Bitable selection/profit tables from product images, 1688 purchase/package data, Amazon UK competitor selling prices, 选品漏斗, 飞书多维表格, 批量抓产品信息, 图片搜同款, 包装尺寸重量, 产品属性, 英国站售价, or 利润测算表.
---

# Product Profit Data Filler

Help ecommerce coworkers fill Feishu Bitable / 飞书多维表格 selection and profit tables from product images. The coworker uses this skill by typing the Bitable link and Feishu App ID/App Secret in the Codex input box, or by asking Codex to use a local `.env` file. Codex should do the API work, browser fallback, evidence files, and writeback steps for them.

Never treat missing live credentials as an unfinished skill. If credentials are missing during use, ask the coworker for them in the current Codex conversation or ask them to provide a local `.env`; then continue.

## Employee-Friendly Rule

Use plain Chinese for coworker-facing messages. The coworker should not need to understand Feishu APIs, tokens, Scrapling, browser automation, selectors, or scripts.

If the coworker pastes App ID/App Secret in the input box, write them into a local `.env` file for the run, never echo the secret back, and never include it in git, logs, screenshots, evidence files, or final summaries.

## What To Ask For At Runtime

When the user invokes this skill and the information is not already present, ask for:

```text
请把这 3 个信息发我：
1. 飞书多维表格链接
2. Feishu App ID
3. Feishu App Secret
```

If they paste all three in one message, proceed without extra confirmation. Do not ask them to understand GitHub, Python, API tokens, table_id, selectors, or JSON.

## Default Assumptions

- Table type: Feishu Bitable / 飞书多维表格.
- Amazon marketplace: UK only, `amazon.co.uk`.
- Selling price currency: GBP.
- 1688 purchase price source currency: CNY.
- UK exchange rate: `9.17` CNY/GBP, so GBP purchase cost = `1688 CNY price / 9.17`.
- Batch size: 20 records.

## Required First Step

Before scraping, downloading images, or editing the table, run the Feishu Bitable probe with `scripts/feishu_bitable.py probe` as described in `references/runbook.md`. The probe reads table metadata, inspects fields, and confirms that product images are readable.

Do not claim live Feishu access has been verified unless the probe succeeds. Stop and explain plainly if the probe cannot read table metadata, records, or product images.

## Workflow

1. Collect or load the runtime inputs: Bitable link, `FEISHU_APP_ID`, and `FEISHU_APP_SECRET`.
2. If credentials were pasted in chat, store them in local `.env` and do not repeat the secret.
3. Probe the Feishu Bitable link, build the field map, plan rows, and download images with `scripts/feishu_bitable.py`.
4. Select rows with a product image and missing target data.
5. For each row image, search 1688 for visually similar products. Use browser automation only for the image-upload/search-result step when needed.
6. Scrape selected 1688 product pages with `scripts/scrape_1688_product.py`. Extract CNY price, package dimensions, package weight, product attributes, and 1688 URL.
7. Get Amazon UK selling price from row-provided Amazon links first; otherwise search `amazon.co.uk` for similar products. Use `scripts/scrape_amazon_uk_prices.py`, collect credible GBP prices, and choose the middle observed price.
8. Normalize dimensions/weight with `scripts/normalize_package_data.py`, choose collected competitor prices with `scripts/select_competitor_price.py`, and convert 1688 CNY price to GBP purchase cost with `9.17`.
9. Build update/evidence files with `scripts/run_batch.py`.
10. Write back only mapped blank input fields with `scripts/feishu_bitable.py update-records`. Preserve existing values, formulas, readonly fields, and calculated columns.
11. Save batch state after each record. Reruns continue from the next unprocessed planned row instead of repeating the first batch.

## References

Read references before live runs:

- `references/feishu-bitable-workflow.md`
- `references/field-mapping.md`
- `references/1688-data-rules.md`
- `references/amazon-uk-price-rules.md`
- `references/runbook.md`

## Field Mapping

Read `references/field-mapping.md`. Do not add new fields by default. If a source/remarks field exists, write evidence there; otherwise write an external evidence file.

## Data Rules

- Read `references/1688-data-rules.md` before 1688 extraction.
- Read `references/amazon-uk-price-rules.md` before Amazon UK pricing.
- Use `references/runbook.md` for the runnable script order and batch handoff steps.

## Stop Conditions

Stop and ask the user when:

- Feishu credentials are missing, invalid, or not authorized for the Bitable.
- The Bitable link cannot be parsed as a Base/Bitable app.
- Product images cannot be downloaded from records.
- The target field map is ambiguous enough that writing may corrupt data.
- The row is missing required extracted data such as packaging, attributes, supplier URL, or Amazon UK price; mark it as partial rather than complete.
- Login, CAPTCHA, slider verification, account risk, payment, order, or private account information appears.
- Search results are materially different products and no safe match exists.
- The next action would overwrite formulas, delete records, change table schema, place an order, or expose secrets.

## Final Summary

Keep final summaries short and practical:

```text
这批处理完成：共 20 行，已补齐 16 行，4 行缺包装重量或没有高相似结果。采购价按 1688 人民币价除以 9.17 换算为 GBP；售价来自 Amazon UK 相似竞品中位价。已写回飞书多维表格，证据文件保存在 outputs/evidence.jsonl。
```
