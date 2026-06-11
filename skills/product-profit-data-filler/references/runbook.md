# Runbook

This skill is for Feishu Bitable / 飞书多维表格, not generic Feishu Sheets. Build and run it as an API-first table filler with browser fallback only for visual web tasks.

## Source Conversation Decisions

- The coworker has a Feishu Bitable selection/profit table.
- The coworker should use this skill by typing the Bitable link and Feishu App ID/App Secret in the Codex input box, or by asking Codex to use a local `.env`.
- Product rows mostly start from product images.
- The task may involve 100+ rows.
- The coworker needs purchase price, package dimensions, package weight, product attribute data, and Amazon UK selling price.
- 1688 price is the purchase-price source.
- UK exchange rate is fixed at `9.17`; fill GBP purchase cost as `CNY / 9.17` unless the target field clearly expects CNY.
- Amazon is the UK site only.
- Amazon selling price should be selected from credible similar competitor prices, usually the middle observed price.

## Coworker Input Template

When the coworker starts a run, they can paste this into Codex:

```text
请用 product-profit-data-filler 处理这个飞书多维表格。
飞书多维表格链接：<粘贴链接>
Feishu App ID：<粘贴 App ID>
Feishu App Secret：<粘贴 App Secret>
先识别字段和需要补齐的行，再开始批量补数据。
```

If the coworker pastes the secret in chat, immediately move it into local `.env` for the run and never repeat it in replies, logs, screenshots, evidence files, or final summaries.

## Full Run

1. Create or reuse a local `.env` file outside git. If the coworker pasted credentials in the Codex input box, Codex creates this file for them:

```text
FEISHU_APP_ID=<paste Feishu App ID here>
FEISHU_APP_SECRET=<paste Feishu App Secret here>
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

This normalizes package values, converts 1688 CNY prices to GBP, writes `outputs/updates.json`, rewrites `outputs/evidence.jsonl` for the current run, and saves `outputs/run-state.json` after each record.

6. Write back in batches:

```powershell
python scripts/feishu_bitable.py update-records --url "<bitable-url>" --updates outputs/updates.json --batch-size 20
```

## Batch Behavior

- `run_batch.py` default batch size: 20 planned records. Pass `--batch-size 20` explicitly in production runs.
- `feishu_bitable.py update-records` default batch size: 100 Feishu records. Pass `--batch-size 20` when you want the same 20-row writeback batches as the runner.
- Continue other rows when one row fails.
- Save `outputs/run-state.json` after each row and batch.
- Write/rewrite `outputs/evidence.jsonl` with record_id, image path, 1688 URL, Amazon UK URLs, extracted values, confidence, and errors.

## No Secrets In Output

Never put App Secret, access tokens, cookies, or browser profile details into:

- Git files.
- Evidence files.
- Final chat summaries.
- Screenshots.
- Logs shown to non-technical coworkers.

## User-Facing Progress

Say:

```text
我已经识别到图片字段、采购价字段、包装尺寸重量字段和英国售价字段。共有 26 行需要补数据，我会按 20 行一批处理；遇到登录、验证码或无法判断同款时再停下来问你。
```

Do not say:

```text
我需要你看一下 API token / selector / field_id / JSON schema。
```
