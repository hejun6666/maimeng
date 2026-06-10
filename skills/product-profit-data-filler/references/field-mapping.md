# Field Mapping

Map Feishu Bitable fields by exact name first, then synonym. Normalize names by trimming whitespace, lowercasing English, and ignoring spaces.

- product_image: 图片, 产品图片, 主图, image, Image, 商品图
- product_attribute: 产品属性, 属性, 规格参数, 产品尺寸, 尺寸重量, 产品信息
- purchase_price_gbp: 采购价, 采购成本, 采购成本价, 英国采购价, GBP采购价
- purchase_price_cny: 1688价, 1688价格, 1688售价, 人民币采购价, CNY采购价
- package_dimensions: 包装尺寸, 包裹尺寸, 外箱尺寸, 长宽高, Package dimensions
- package_weight: 包装重量, 包裹重量, 重量, 毛重, Package weight
- selling_price_gbp: 售价, 英国售价, 竞对售价, Amazon售价, Amazon UK售价
- amazon_url: 亚马逊链接, Amazon链接, Amazon UK链接, 竞对链接
- supplier_url: 1688链接, 1688商品链接, 采购链接
- evidence: 备注, 来源, 数据来源, 证据, 跟进备注
- status: 状态, 进度, 处理状态

## Write Rules

- Do not create fields by default.
- Do not overwrite formulas or calculated fields.
- Fill only missing target values unless the user explicitly asks to refresh all values.
- If both CNY and GBP purchase fields exist, fill both.
- If only `采购价` exists in this UK workflow, fill GBP value by default.
- If source/evidence fields do not exist, write evidence to `outputs/evidence.jsonl`.

## Bitable Value Types

Use field metadata before writing. Text fields can receive strings. Number fields should receive numbers. URL fields may require structured URL values. Attachment fields must not receive a local path directly.
