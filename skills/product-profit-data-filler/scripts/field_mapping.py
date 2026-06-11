"""Field role mapping helpers for Feishu Bitable product-profit sheets."""

SYNONYMS = {
    "product_image": [
        "图片",
        "产品图片",
        "主图",
        "image",
        "Image",
        "商品图",
        "商品图片",
        "产品图",
        "产品主图",
    ],
    "product_attribute": [
        "产品属性",
        "属性",
        "规格参数",
        "产品尺寸",
        "尺寸重量",
        "产品信息",
        "产品参数",
        "规格",
        "型号",
    ],
    "package_dimensions": [
        "包装尺寸",
        "包裹尺寸",
        "外箱尺寸",
        "长宽高",
        "Package dimensions",
        "包装长宽高",
        "箱规",
        "外箱规格",
        "尺寸",
    ],
    "package_weight": [
        "包装重量",
        "包裹重量",
        "重量",
        "毛重",
        "Package weight",
        "单件重量",
        "物流重量",
        "发货重量",
    ],
    "purchase_price_gbp": [
        "采购价",
        "采购成本",
        "采购成本价",
        "英国采购价",
        "GBP采购价",
        "英镑采购价",
        "采购价GBP",
        "采购成本GBP",
    ],
    "purchase_price_cny": [
        "1688价",
        "1688价格",
        "1688售价",
        "人民币采购价",
        "CNY采购价",
        "采购价CNY",
        "采购成本CNY",
        "1688采购价",
    ],
    "selling_price_gbp": [
        "售价",
        "英国售价",
        "竞对售价",
        "Amazon售价",
        "Amazon UK售价",
        "英镑售价",
        "销售价",
        "销售价格",
    ],
    "amazon_url": [
        "亚马逊链接",
        "Amazon链接",
        "Amazon UK链接",
        "竞对链接",
        "英国站链接",
    ],
    "supplier_url": [
        "1688链接",
        "1688商品链接",
        "采购链接",
        "供应商链接",
        "货源链接",
    ],
    "evidence": [
        "备注",
        "来源",
        "数据来源",
        "证据",
        "跟进备注",
        "处理备注",
        "说明",
    ],
    "status": [
        "状态",
        "进度",
        "处理状态",
        "处理进度",
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
