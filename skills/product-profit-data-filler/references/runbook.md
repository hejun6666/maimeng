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
   - Save extraction JSON beside the downloaded images as `<safe_record_id>.1688.json` and `<safe_record_id>.amazon.json`.

5. Build Feishu update payloads, evidence, and resume state:

```powershell
python scripts/run_batch.py --url "<bitable-url>" --plan outputs/plan.json --image-dir outputs/images --batch-size 20 --out-updates outputs/updates.json --evidence outputs/evidence.jsonl
```

This normalizes package values, converts 1688 CNY prices to GBP, writes `outputs/updates.json`, appends `outputs/evidence.jsonl`, and saves `outputs/run-state.json` after each record.

6. Write back in batches:

```powershell
python scripts/feishu_bitable.py update-records --url "<bitable-url>" --updates outputs/updates.json --batch-size 20
```

## Batch Behavior

- `run_batch.py` default batch size: 20 planned records. Pass `--batch-size 20` explicitly in production runs.
- `feishu_bitable.py update-records` default batch size: 100 Feishu records. Pass `--batch-size 20` when you want the same 20-row write-back batches as the runner.
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
