---
name: product-profit-data-filler
description: Fill Feishu Bitable selection/profit tables from product images by extracting row images, searching 1688 for similar high-sales products, collecting purchase price/package dimensions/weight, and choosing an Amazon UK selling price. Use when the user mentions 选品漏斗, 飞书多维表格, 批量抓产品信息, 图片搜同款, 包装尺寸重量, 产品属性, 1688采购价, Amazon UK, 英国站售价, 竞对售价, or 利润测算表.
---

# Product Profit Data Filler

Use Feishu Bitable / 飞书多维表格 as the table source. Help ecommerce coworkers fill selection/profit tables from product images. The normal input is a Feishu Bitable link plus Feishu App ID/App Secret. The output is the same Bitable updated with 1688 purchase cost, package dimensions, package weight, product attributes, and Amazon UK selling price.

Load `FEISHU_APP_ID` and `FEISHU_APP_SECRET` from environment or `.env`; never store secrets in git or chat summaries.

## Employee-Friendly Rule

Use plain Chinese for coworker-facing summaries. The coworker should not need to understand Feishu APIs, tokens, Scrapling, browser automation, selectors, or scripts. Never write App Secret into the skill, git, logs, screenshots, or chat summaries. Use `.env` or environment variables.

## Default Assumptions

- Table type: Feishu Bitable / 飞书多维表格.
- Amazon marketplace: UK only, `amazon.co.uk`.
- Selling price currency: GBP.
- 1688 purchase price source currency: CNY.
- UK exchange rate: `9.17` CNY/GBP, so GBP purchase cost = `1688 CNY price / 9.17`.
- Batch size: 20 records.

## Required First Step

Before any scraping or editing, run the Feishu Bitable probe once the Task 2 helper script is available. The later command will probe the Bitable URL, read table metadata, inspect fields, and confirm that product images are readable.

Until that script exists, do not claim live Feishu access has been verified. Stop if the probe cannot read table metadata, records, or product images.

## Workflow

1. Load Feishu credentials from `.env` or environment variables: `FEISHU_APP_ID`, `FEISHU_APP_SECRET`.
2. Probe the Feishu Bitable link and build the field map once the Task 2 Feishu helper exists.
3. Select rows with a product image and missing target data.
4. Download row images through Feishu Bitable attachment/media APIs.
5. For each row image, search 1688 for visually similar products. Use browser automation only for the image-upload/search-result step when needed.
6. Scrape selected 1688 product pages with deterministic scripts once later tasks add them. Extract CNY price, package dimensions, package weight, product attributes, and 1688 URL.
7. Get Amazon UK selling price from row-provided Amazon links first; otherwise search `amazon.co.uk` for similar products. Collect credible GBP prices and choose the middle observed price.
8. Normalize dimensions/weight and convert 1688 CNY price to GBP purchase cost with `9.17`.
9. Write back only mapped input fields. Preserve formulas and existing calculated columns.
10. Save batch state after each batch and continue other rows when one row fails.

## References

Read references before live runs:

- `references/feishu-bitable-workflow.md`
- `references/field-mapping.md`
- `references/1688-data-rules.md`
- `references/amazon-uk-price-rules.md`

## Field Mapping

Read [references/field-mapping.md](references/field-mapping.md). Do not add new fields by default. If a source/remarks field exists, write evidence there; otherwise write an external evidence file.

## Data Rules

- Read [references/1688-data-rules.md](references/1688-data-rules.md) before 1688 extraction.
- Read [references/amazon-uk-price-rules.md](references/amazon-uk-price-rules.md) before Amazon UK pricing.
- Later tasks add helper scripts for repeatable Amazon UK price selection and dimensions/weight normalization.

## Stop Conditions

Stop and ask the user when:

- Feishu credentials are missing, invalid, or not authorized for the Bitable.
- The Bitable link cannot be parsed as a Base/Bitable app.
- Product images cannot be downloaded from records.
- The target field map is ambiguous enough that writing may corrupt data.
- Login, CAPTCHA, slider verification, account risk, payment, order, or private account information appears.
- Search results are materially different products and no safe match exists.
- The next action would overwrite formulas, delete records, change table schema, place an order, or expose secrets.

## Final Summary

Keep final summaries short:

```text
这批处理完成：20 行，已补齐 16 行，4 行缺包装重量或没有高相似结果。采购价按 1688 人民币价除以 9.17 换算为 GBP；售价来自 Amazon UK 相似竞品中位价。已写回飞书多维表格，证据文件保存在 outputs/evidence.xlsx。
```
