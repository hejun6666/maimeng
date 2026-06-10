# Feishu Bitable Workflow

Use Feishu Bitable as the source of rows, images, and writeback targets. Use the Feishu OpenAPI through scripts first; use browser automation only when a user explicitly needs help locating the Bitable link or checking the visible table after API writeback.

## Credentials

- Read `FEISHU_APP_ID` and `FEISHU_APP_SECRET` from environment variables or a local `.env` file.
- Never paste secrets into skill files, git commits, issue comments, screenshots, or chat summaries.
- Stop if either credential is missing, invalid, or not authorized for the Bitable app.

## Link Parsing

- Accept Base/Bitable links that contain `/base/<app_token>`.
- Read `table` or `table_id` query parameters when present.
- Read `view` or `view_id` query parameters when present, but do not require a view for API access.
- Stop if the link cannot produce an app token.

## Probe First

Before scraping, downloading images, or writing data, run:

```powershell
python "$env:USERPROFILE\.codex\skills\product-profit-data-filler\scripts\feishu_bitable.py" probe --url "<bitable-url>"
```

The probe must confirm:

- App token can be parsed.
- Tenant access token can be issued from `FEISHU_APP_ID` and `FEISHU_APP_SECRET`.
- Table metadata can be listed.
- Field metadata can be listed.
- Records can be listed.
- At least one target row has a readable product image attachment.

## Record Planning

- Select only records that have a product image and at least one blank target field.
- Default batch size is 20 records.
- Preserve existing row values unless the user asks for refresh/overwrite.
- Preserve formulas and calculated fields.

## Image Download

- Extract Feishu file tokens from product image attachment fields.
- Download images through Feishu Drive media APIs.
- Store downloaded files under local `outputs/images/`.
- Stop if images cannot be downloaded because of permission, token shape, or file expiry.

## Writeback

- Build the write payload from mapped field names, not guessed column positions.
- Write only mapped target fields.
- Use number values for number fields and text values for text fields.
- Do not create fields, delete records, reorder columns, or change schema.
- Save evidence externally when no evidence/remarks field exists.
