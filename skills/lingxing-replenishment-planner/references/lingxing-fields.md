# Lingxing Fields

## Browser Access

Use the Lingxing ERP page opened inside Codex. The user logs in on that page; do not ask for passwords, cookies, or hard-coded company account details in chat.

If automated browser control is unavailable, ask the user to keep the Lingxing page open inside Codex and provide only the specific missing export, screenshot, or field value that blocks the calculation. Do not route non-technical users into developer-only browser setup.

## Main Pages

### Warehouse: FBA Inventory Detail

URL path:

```text
/erp/msupply/fbaInventory
```

Chinese navigation:

```text
仓库 > FBA库存明细
```

Primary fields:

| Calculator field | Lingxing label | Notes |
| --- | --- | --- |
| `fba_total` | `FBA总库存` | Used in long-range overseas coverage. |
| `fba_sellable` | `FBA可售` | Used for immediate sellable pressure. |
| `awd_available_inbound_total` | `AWD可用+在途库存合计` | Horizontally scroll right to find it. |
| optional | `FBA实际在途`, `FBA标发在途`, `FBA入库中` | Show separately if useful. |

AWD fields may be far to the right of the table. Horizontally scroll the inventory table before deciding the field is missing.

### Sales: Listing

URL path:

```text
/erp/listing
```

Chinese navigation:

```text
销售 > Listing
```

Primary fields:

| Calculator field | Lingxing label | Notes |
| --- | --- | --- |
| `sku` | `MSKU/FNSKU` | Batch mode SKU scope comes from the current filtered Listing rows. |
| `asin` | `ASIN` | Report context. |
| `title` | `标题` | Report context. |
| `owner` | `负责人` | Report context. |
| `sales_7` | `7|14|30天销量`, first number | Trend check. |
| `sales_14` | `7|14|30天销量`, second number | Trend check. |
| `sales_30` | `7|14|30天销量`, third number | Default sales basis. |

Also capture store, country/site, fulfillment method, responsible person, and SKU title if visible. These are report context, not formula inputs.

Batch extraction priority:

1. Use the Listing export/download button for the current filtered result set.
2. If export is unavailable, read visible table rows and paginate or virtual-scroll until all current filtered rows are collected.
3. Use `MSKU/FNSKU` as the join key when enriching rows from `仓库 > FBA库存明细`.

## Extraction Checklist

For a normal batch run, collect from `销售 > Listing`:

- `MSKU/FNSKU`.
- `ASIN`.
- `标题`.
- `状态`.
- `7|14|30天销量`.
- `今日销量` and `昨日销量`, if visible.
- `负责人`, if visible.

Then enrich the same SKU set from `仓库 > FBA库存明细`:

- `FBA总库存`.
- `FBA可售`.
- `AWD可用+在途库存合计`.

After extraction, explicitly list missing fields before calculating. If only optional fields are missing, calculate with assumptions and mark them.
