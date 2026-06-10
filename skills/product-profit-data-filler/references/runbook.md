# Runbook

This skill is for Feishu Bitable / 多维表格, not generic Feishu Sheets. Build and run it as an API-first table filler with browser fallback only for visual web tasks.

## Source Conversation Decisions

- The coworker has a Feishu Bitable selection/profit table.
- Product rows mostly start from product images.
- The task may involve 100+ rows.
- The coworker needs purchase price, package dimensions, package weight, product attribute data, and Amazon UK selling price.
- 1688 price is the purchase-price source.
- UK exchange rate is fixed at `9.17`; fill GBP purchase cost as `CNY / 9.17` unless the target field clearly expects CNY.
- Amazon is the UK site only.
- Amazon selling price should be selected from credible similar competitor prices, usually the middle observed price.

## Full Run

1. Create or reuse a local `.env` file outside git:

```text
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
```

2. Probe:

```powershell
python scripts/feishu_bitable.py probe --url "<bitable-url>" --out outputs/probe.json
```

3. Plan rows and download images:

```powershell
python scripts/feishu_bitable.py plan --url "<bitable-url>" --out outputs/plan.json
python scripts/feishu_bitable.py download-images --url "<bitable-url>" --plan outputs/plan.json --out-dir outputs/images
```

4. For each planned row:
   - Search 1688 by image.
   - Scrape the selected 1688 product page.
   - Scrape or collect Amazon UK competitor prices.
   - Normalize package values.
   - Prepare a record update.

5. Write back in batches:

```powershell
python scripts/feishu_bitable.py update-records --url "<bitable-url>" --updates outputs/updates.json
```

## Batch Behavior

- Default batch size: 20 records.
- Continue other rows when one row fails.
- Save `outputs/run-state.json` after each row and batch.
- Save `outputs/evidence.jsonl` with record_id, image path, 1688 URL, Amazon UK URLs, extracted values, confidence, and errors.

## No Secrets in Output

Never put App Secret, access tokens, cookies, or browser profile details into:

- Git files.
- Evidence files.
- Final chat summaries.
- Screenshots.
- Logs shown to non-technical coworkers.

## User-Facing Progress

Say:

```text
我已经识别到图片字段、采购价字段、包装尺寸重量字段和英国售价字段。共有126行需要补数据，我会按20行一批处理；遇到登录、验证码或无法判断同款时再停下来问你。
```

Do not say:

```text
我需要你看一下 API token / selector / field_id / JSON schema。
```
