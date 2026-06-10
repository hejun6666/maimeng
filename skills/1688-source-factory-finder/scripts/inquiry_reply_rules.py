#!/usr/bin/env python3
"""Deterministic reply handling rules for 1688 inquiry chats."""

from __future__ import annotations

import re
from typing import NamedTuple


class ReplyContext(NamedTuple):
    user_quantity: str = ""
    default_quantity: str = ""
    page_moq: str = ""
    product_context_clear: bool = False
    has_quote_image: bool = False
    has_new_customer_reply: bool = True
    chat_history: str = ""


class ReplyDecision(NamedTuple):
    status: str
    action: str
    message: str = ""
    ask_user: bool = False
    stop_reason: str = ""


INCOMPLETE_FOLLOWUP = "好的，麻烦再发一下这款的含税报价、起订量、交期、样品费和打样货期；如果有阶梯价也一起发下，谢谢。"
KEEP_ON_1688 = "我们先在1688这边沟通和报价就可以，麻烦请直接在1688这里发就可以，谢谢。"
PAGE_MOQ_QUANTITY = "先按页面起订量报价就可以，麻烦发一下含税价、交期和样品相关费用。"
SPEC_FROM_CONTEXT = "就按刚才这个链接里的款式，麻烦发一下含税价、起订量、交期、样品费和打样货期。"


def normalize(text: str) -> str:
    return re.sub(r"\s+", "", (text or "").lower())


def has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term.lower() in text for term in terms)


def is_external_contact_request(text: str) -> bool:
    return has_any(text, ("微信", "加微", "wx", "电话", "手机号", "联系方式", "业务员联系", "私发", "私聊"))


def is_quantity_question(text: str) -> bool:
    return bool(re.search(r"(要|采购|下|订|买).{0,4}(多少|几|数量)", text)) or has_any(
        text, ("多少套", "多少件", "数量多少", "采购数量")
    )


def is_spec_question(text: str) -> bool:
    if not has_any(text, ("规格", "尺寸", "颜色", "型号", "款式", "包装", "logo", "图纸", "定制")):
        return False
    return has_any(text, ("哪个", "哪款", "什么", "确认", "要", "发", "提供"))


def is_quote_image(text: str, context: ReplyContext) -> bool:
    return context.has_quote_image or (has_any(text, ("报价图", "报价单", "表格", "图片")) and has_any(text, ("报价", "价格", "看下")))


def is_safety_stop(text: str) -> bool:
    return has_any(text, ("付款", "支付", "付定金", "打款", "拍下", "先拍", "提交订单", "签合同", "合同"))


def is_complete_quote(text: str) -> bool:
    has_price = has_any(text, ("含税", "报价", "阶梯价", "元"))
    has_moq = has_any(text, ("起订", "起批", "moq", "件起", "套起"))
    has_lead_time = has_any(text, ("交期", "货期", "现货", "天"))
    return has_price and has_moq and has_lead_time


def is_incomplete_reply(text: str) -> bool:
    short_reply = has_any(text, ("在", "有货", "稍等", "好的", "可以拍", "放心下单"))
    return short_reply and not is_complete_quote(text)


def already_asked_full_quote_fields(context: ReplyContext) -> bool:
    history = normalize(context.chat_history)
    if not history:
        return False
    required_terms = ("含税", "起订", "交期", "样品费", "打样货期")
    return all(term in history for term in required_terms)


def duplicate_followup_decision() -> ReplyDecision:
    return ReplyDecision(
        status="已回复但缺字段",
        action="avoid_duplicate_followup",
        message="",
        stop_reason="已经追问过完整报价字段，避免同一会话重复整段追问；先等回复或只追问新增缺项。",
    )


def quantity_reply(context: ReplyContext) -> ReplyDecision:
    quantity = context.user_quantity or context.default_quantity
    if quantity:
        return ReplyDecision(
            status="已追问",
            action="reply_quantity",
            message=f"先按{quantity}报价，麻烦发一下含税价、交期和样品相关费用。",
        )
    if context.page_moq:
        return ReplyDecision(status="已追问", action="reply_quantity", message=PAGE_MOQ_QUANTITY)
    return ReplyDecision(
        status="需用户确认数量",
        action="ask_user",
        message="供应商在问数量，但当前没有用户数量、默认数量或页面起订量，需要用户确认数量。",
        ask_user=True,
    )


def spec_reply(context: ReplyContext) -> ReplyDecision:
    if context.product_context_clear:
        return ReplyDecision(status="已追问", action="reply_spec_from_context", message=SPEC_FROM_CONTEXT)
    return ReplyDecision(
        status="需用户确认规格",
        action="ask_user",
        message="供应商在问规格/尺寸/颜色/型号，当前商品链接无法唯一判断，需要用户确认规格。",
        ask_user=True,
    )


def decide_reply(reply_text: str, context: ReplyContext | None = None) -> ReplyDecision:
    context = context or ReplyContext()
    text = normalize(reply_text)

    if not context.has_new_customer_reply:
        return ReplyDecision(status="待回复", action="wait")
    if is_safety_stop(text):
        return ReplyDecision(status="安全暂停", action="stop", ask_user=True, stop_reason="供应商回复涉及下单或付款。")
    if is_external_contact_request(text):
        return ReplyDecision(status="要求外部联系", action="reply_keep_on_1688", message=KEEP_ON_1688)
    if is_quote_image(text, context):
        return ReplyDecision(status="需识别报价图", action="extract_visual_quote", message="打开报价图片并截图/OCR/人工识别，不能当作无有效回复。")
    if is_quantity_question(text):
        return quantity_reply(context)
    if is_spec_question(text):
        return spec_reply(context)
    if is_complete_quote(text):
        return ReplyDecision(status="已拿到报价", action="record_quote")
    if is_incomplete_reply(text):
        if already_asked_full_quote_fields(context):
            return duplicate_followup_decision()
        return ReplyDecision(status="已回复但缺字段", action="follow_up", message=INCOMPLETE_FOLLOWUP)
    if already_asked_full_quote_fields(context):
        return duplicate_followup_decision()
    return ReplyDecision(status="已回复但缺字段", action="follow_up", message=INCOMPLETE_FOLLOWUP)


__all__ = ["ReplyContext", "ReplyDecision", "decide_reply"]
