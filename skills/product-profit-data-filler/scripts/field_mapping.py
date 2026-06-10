"""Field role mapping helpers for Feishu Bitable product-profit sheets."""

SYNONYMS = {
    "product_image": [
        "图片",
        "产品图片",
        "主图",
        "image",
        "Image",
        "商品图",
        "鍥剧墖",
        "浜у搧鍥剧墖",
        "涓诲浘",
        "鍟嗗搧鍥?",
    ],
    "product_attribute": [
        "产品属性",
        "属性",
        "规格参数",
        "产品尺寸",
        "尺寸重量",
        "产品信息",
        "浜у搧灞炴€?",
        "灞炴€?",
        "瑙勬牸鍙傛暟",
        "浜у搧灏哄",
        "灏哄閲嶉噺",
        "浜у搧淇℃伅",
    ],
    "package_dimensions": [
        "包装尺寸",
        "包裝尺寸",
        "外箱尺寸",
        "长宽高",
        "Package dimensions",
        "鍖呰灏哄",
        "鍖呰９灏哄",
        "澶栫灏哄",
        "闀垮楂?",
    ],
    "package_weight": [
        "包装重量",
        "包裝重量",
        "重量",
        "毛重",
        "Package weight",
        "鍖呰閲嶉噺",
        "鍖呰９閲嶉噺",
        "閲嶉噺",
        "姣涢噸",
    ],
    "purchase_price_gbp": [
        "采购价",
        "采购成本",
        "采购成本价",
        "英国采购价",
        "GBP采购价",
        "閲囪喘浠?",
        "閲囪喘鎴愭湰",
        "閲囪喘鎴愭湰浠?",
        "鑻卞浗閲囪喘浠?",
        "GBP閲囪喘浠?",
    ],
    "purchase_price_cny": [
        "1688价",
        "1688价格",
        "1688售价",
        "人民币采购价",
        "CNY采购价",
        "1688浠?",
        "1688浠锋牸",
        "1688鍞环",
        "浜烘皯甯侀噰璐环",
        "CNY閲囪喘浠?",
    ],
    "selling_price_gbp": [
        "售价",
        "英国售价",
        "竞对售价",
        "Amazon售价",
        "Amazon UK售价",
        "鍞环",
        "鑻卞浗鍞环",
        "绔炲鍞环",
        "Amazon鍞环",
        "Amazon UK鍞环",
    ],
    "amazon_url": [
        "亚马逊链接",
        "Amazon链接",
        "Amazon UK链接",
        "竞对链接",
        "浜氶┈閫婇摼鎺?",
        "Amazon閾炬帴",
        "Amazon UK閾炬帴",
        "绔炲閾炬帴",
    ],
    "supplier_url": [
        "1688链接",
        "1688商品链接",
        "采购链接",
        "1688閾炬帴",
        "1688鍟嗗搧閾炬帴",
        "閲囪喘閾炬帴",
    ],
    "evidence": [
        "备注",
        "来源",
        "数据来源",
        "证据",
        "跟进备注",
        "澶囨敞",
        "鏉ユ簮",
        "鏁版嵁鏉ユ簮",
        "璇佹嵁",
        "璺熻繘澶囨敞",
    ],
    "status": [
        "状态",
        "进度",
        "处理状态",
        "鐘舵€?",
        "杩涘害",
        "澶勭悊鐘舵€?",
    ],
}


def normalize_name(name):
    return str(name or "").strip().lower().replace(" ", "")


def build_field_map(fields):
    by_name = {normalize_name(field.get("field_name")): field for field in fields}
    result = {}
    for role, names in SYNONYMS.items():
        for name in names:
            found = by_name.get(normalize_name(name))
            if found:
                result[role] = found
                break
    return result
