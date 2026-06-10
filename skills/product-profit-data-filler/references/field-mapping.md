# Field Mapping

Map Feishu Bitable fields by exact name first, then synonym. Normalize names by trimming whitespace, lowercasing English, and ignoring spaces.

- product_image: 鍥剧墖, 浜у搧鍥剧墖, 涓诲浘, image, Image, 鍟嗗搧鍥?
- product_attribute: 浜у搧灞炴€? 灞炴€? 瑙勬牸鍙傛暟, 浜у搧灏哄, 灏哄閲嶉噺, 浜у搧淇℃伅
- purchase_price_gbp: 閲囪喘浠? 閲囪喘鎴愭湰, 閲囪喘鎴愭湰浠? 鑻卞浗閲囪喘浠? GBP閲囪喘浠?
- purchase_price_cny: 1688浠? 1688浠锋牸, 1688鍞环, 浜烘皯甯侀噰璐环, CNY閲囪喘浠?
- package_dimensions: 鍖呰灏哄, 鍖呰۹灏哄, 澶栫灏哄, 闀垮楂? Package dimensions
- package_weight: 鍖呰閲嶉噺, 鍖呰۹閲嶉噺, 閲嶉噺, 姣涢噸, Package weight
- selling_price_gbp: 鍞环, 鑻卞浗鍞环, 绔炲鍞环, Amazon鍞环, Amazon UK鍞环
- amazon_url: 浜氶┈閫婇摼鎺? Amazon閾炬帴, Amazon UK閾炬帴, 绔炲閾炬帴
- supplier_url: 1688閾炬帴, 1688鍟嗗搧閾炬帴, 閲囪喘閾炬帴
- evidence: 澶囨敞, 鏉ユ簮, 鏁版嵁鏉ユ簮, 璇佹嵁, 璺熻繘澶囨敞
- status: 鐘舵€? 杩涘害, 澶勭悊鐘舵€?

## Write Rules

- Do not create fields by default.
- Do not overwrite formulas or calculated fields.
- Fill only missing target values unless the user explicitly asks to refresh all values.
- If both CNY and GBP purchase fields exist, fill both.
- If only `閲囪喘浠?` exists in this UK workflow, fill GBP value by default.
- If source/evidence fields do not exist, write evidence to `outputs/evidence.jsonl`.

## Bitable Value Types

Use field metadata before writing. Text fields can receive strings. Number fields should receive numbers. URL fields may require structured URL values. Attachment fields must not receive a local path directly.
