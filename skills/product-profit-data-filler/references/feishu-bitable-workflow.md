# Feishu Bitable Workflow

Use Feishu Bitable as the source of rows, images, and writeback targets. Use the Feishu OpenAPI through the bundled scripts now; use browser automation only when a user explicitly needs help locating the Bitable link or checking the visible table after API writeback.

## Credentials

- Read `FEISHU_APP_ID` and `FEISHU_APP_SECRET` from environment variables or a local `.env` file.
- Never paste secrets into skill files, git commits, issue comments, screenshots, or chat summaries.
- Stop if either credential is missing, invalid, or not authorized for the Bitable app.

## Link Parsing

- Accept Base/Bitable links that contain `/base/<app_token>`.
- Read `table` or `table_id` query parameters when present.
- Read `view` or `view_id` query parameters when present. When a coworker shares a filtered view, keep record listing scoped to that view.
- Stop if the link cannot produce an app token.

## Probe First

Before scraping, downloading images, or writing data, run:

```powershell
python scripts/feishu_bitable.py probe --url "<bitable-url>" --out outputs/probe.json
```

The probe must confirm:

- App token can be parsed.
- Tenant access token can be issued from `FEISHU_APP_ID` and `FEISHU_APP_SECRET`.
- Table metadata can be listed.
- Field metadata can be listed.
- Records can be listed.
- At least one target row has a readable product image attachment.

## Record Planning

Build the row plan with:

```powershell
python scripts/feishu_bitable.py plan --url "<bitable-url>" --out outputs/plan.json
```

- Select only records that have a product image and at least one blank target field in the linked table/view scope.
- Default batch size is 20 records.
- Preserve existing row values unless the user asks for refresh/overwrite.
- Preserve formulas and calculated fields.

## Image Download

Download planned row images with:

```powershell
python scripts/feishu_bitable.py download-images --url "<bitable-url>" --plan outputs/plan.json --out-dir outputs/images
```

- Extract Feishu file tokens from product image attachment fields.
- Download images through Feishu Drive media APIs.
- Store downloaded files under local `outputs/images/`.
- Stop if images cannot be downloaded because of permission, token shape, or file expiry.

## Batch Build

After collecting each row's 1688 and Amazon UK extraction JSON files, build update payloads, evidence, and resume state with:

```powershell
python scripts/run_batch.py --url "<bitable-url>" --plan outputs/plan.json --image-dir outputs/images --batch-size 20 --out-updates outputs/updates.json --evidence outputs/evidence.jsonl
```

This step normalizes package values, converts 1688 CNY price to GBP purchase cost, chooses the Amazon UK selling price from collected competitor data, and writes `outputs/updates.json`.

## Writeback

Write accepted updates back to Feishu with:

```powershell
python scripts/feishu_bitable.py update-records --url "<bitable-url>" --updates outputs/updates.json --batch-size 20
```

- Build the write payload from mapped field names, not guessed column positions.
- Write only mapped target fields that are currently blank in the original record.
- Use number values for number fields and text values for text fields.
- Do not create fields, delete records, reorder columns, or change schema.
- Do not write formula, lookup, created/modified metadata, or other readonly fields.
- Save evidence externally when no evidence/remarks field exists.
