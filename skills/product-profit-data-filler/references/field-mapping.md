# Field Mapping

Map Feishu Bitable fields by exact name first, then synonym. Normalize names by trimming whitespace, lowercasing English, and ignoring spaces.

## Supported Field Roles

- product_image: 图片, 产品图片, 主图, 商品图, 商品图片, 产品图, 产品主图, image, Image
- product_attribute: 产品属性, 属性, 规格参数, 产品尺寸, 尺寸重量, 产品信息, 产品参数, 规格, 型号
- purchase_price_gbp: 采购价, 采购成本, 采购成本价, 英国采购价, GBP采购价, 英镑采购价, 采购价GBP, 采购成本GBP
- purchase_price_cny: 1688价, 1688价格, 1688售价, 人民币采购价, CNY采购价, 采购价CNY, 采购成本CNY, 1688采购价
- package_dimensions: 包装尺寸, 包裹尺寸, 外箱尺寸, 长宽高, 包装长宽高, 箱规, 外箱规格, 尺寸, Package dimensions
- package_weight: 包装重量, 包裹重量, 重量, 毛重, 单件重量, 物流重量, 发货重量, Package weight
- selling_price_gbp: 售价, 英国售价, 竞对售价, Amazon售价, Amazon UK售价, 英镑售价, 销售价, 销售价格
- amazon_url: 亚马逊链接, Amazon链接, Amazon UK链接, 竞对链接, 英国站链接
- supplier_url: 1688链接, 1688商品链接, 采购链接, 供应商链接, 货源链接
- evidence: 备注, 来源, 数据来源, 证据, 跟进备注, 处理备注, 说明
- status: 状态, 进度, 处理状态, 处理进度

## Write Rules

- Do not create fields by default.
- Do not overwrite formulas or calculated fields.
- Fill only missing target values unless the user explicitly asks to refresh all values.
- If both CNY and GBP purchase fields exist, fill both.
- If only `采购价` exists in this UK workflow, fill GBP value by default.
- If source/evidence fields do not exist, write evidence to `outputs/evidence.jsonl`.

## Bitable Value Types

Use field metadata before writing. Text fields can receive strings. Number fields should receive numbers. URL fields may require structured URL values. Attachment fields must not receive a local path directly.
