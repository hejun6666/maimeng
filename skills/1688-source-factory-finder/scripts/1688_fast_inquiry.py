#!/usr/bin/env python3
"""Fast, safe CDP helper for 1688 supplier inquiry workflows.

This helper is intentionally conservative. Read-only commands are the default;
anything that could send a message requires an explicit allow flag.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, NamedTuple


DEFAULT_CDP_URL = "http://127.0.0.1:9222"


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")


class TabInfo(NamedTuple):
    id: str
    title: str
    url: str
    kind: str


class CleanupDecision(NamedTuple):
    tab: TabInfo
    action: str
    reason: str


class InquiryAction(NamedTuple):
    supplier_index: int
    shop_name: str
    product_url: str
    action: str
    text: str = ""
    will_send: bool = False


class CdpCommand(NamedTuple):
    id: int
    method: str
    params: dict[str, Any] | None = None


def normalize_cdp_url(raw: str | None) -> str:
    value = (raw or "").strip()
    if not value:
        return DEFAULT_CDP_URL
    if value.isdigit():
        value = f"127.0.0.1:{value}"
    if not value.startswith(("http://", "https://")):
        value = f"http://{value}"

    parsed = urllib.parse.urlsplit(value)
    if not parsed.netloc:
        raise ValueError(f"Invalid CDP URL: {raw}")
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, "", "", "")).rstrip("/")


def classify_url(url: str) -> str:
    raw_url = (url or "").strip()
    parsed = urllib.parse.urlsplit(raw_url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()
    full = raw_url.lower()
    if not host:
        return "other"
    if host == "air.1688.com" and ("im" in path or "def_cbu_web_im" in full):
        return "chat"
    if host == "detail.1688.com" or ("1688.com" in host and "/offer/" in path):
        return "product"
    if host == "s.1688.com" or "offer_search" in full or "search" in host:
        return "search"
    if host.endswith(".1688.com") and host not in {"www.1688.com", "air.1688.com"}:
        return "shop"
    if host == "1688.com" or host.endswith(".1688.com"):
        return "1688"
    return "other"


def tab_from_target(target: dict[str, Any]) -> TabInfo:
    url = str(target.get("url") or "")
    return TabInfo(
        id=str(target.get("id") or ""),
        title=str(target.get("title") or ""),
        url=url,
        kind=classify_url(url),
    )


def fetch_cdp_targets(cdp_url: str, timeout: float = 5.0) -> list[dict[str, Any]]:
    endpoint = f"{normalize_cdp_url(cdp_url)}/json/list"
    with urllib.request.urlopen(endpoint, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, list):
        raise ValueError("CDP /json/list did not return a list.")
    return [item for item in payload if isinstance(item, dict)]


def fetch_cdp_tabs(cdp_url: str, timeout: float = 5.0) -> list[TabInfo]:
    tabs: list[TabInfo] = []
    for target in fetch_cdp_targets(cdp_url, timeout=timeout):
        if target.get("type") != "page":
            continue
        tab = tab_from_target(target)
        if tab.id and tab.url:
            tabs.append(tab)
    return tabs


def close_cdp_tab(cdp_url: str, tab_id: str, timeout: float = 5.0) -> str:
    safe_id = urllib.parse.quote(tab_id, safe="")
    endpoint = f"{normalize_cdp_url(cdp_url)}/json/close/{safe_id}"
    with urllib.request.urlopen(endpoint, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def open_cdp_tab(cdp_url: str, url: str, timeout: float = 5.0) -> dict[str, Any]:
    endpoint = f"{normalize_cdp_url(cdp_url)}/json/new?{urllib.parse.quote(url, safe='')}"
    request = urllib.request.Request(endpoint, method="PUT")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("CDP /json/new did not return an object.")
    return payload


def activate_cdp_tab(cdp_url: str, tab_id: str, timeout: float = 5.0) -> str:
    safe_id = urllib.parse.quote(tab_id, safe="")
    endpoint = f"{normalize_cdp_url(cdp_url)}/json/activate/{safe_id}"
    with urllib.request.urlopen(endpoint, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def build_chat_url(seller_login_id: str, offer_id: str | int) -> str:
    login = str(seller_login_id).strip()
    offer = str(offer_id).strip()
    if not login:
        raise ValueError("seller_login_id is required.")
    if not offer:
        raise ValueError("offer_id is required.")
    source = {
        "offerId": int(offer) if offer.isdigit() else offer,
        "extra": {},
        "source": "od",
        "sourceType": "pcOD",
        "targetLoginId": login,
    }
    query = {
        "touid": f"cnalichn{login}",
        "siteid": "cnalichn",
        "status": "1",
        "portalId": "",
        "gid": "",
        "offerId": offer,
        "itemsId": "",
        "sourceValue": json.dumps(source, ensure_ascii=False, separators=(",", ":")),
    }
    return "https://air.1688.com/app/ocms-fusion-components-1688/def_cbu_web_im/index.html?" + urllib.parse.urlencode(query) + "#/"


def should_switch_keyword_strategy(body_text: str, expected_terms: list[str]) -> bool:
    text = normalize_space(body_text)
    if not text:
        return True
    hard_empty_markers = ("哎呦喂，这里空空如也", "没有相关商品", "拖动下方滑块完成验证")
    if any(marker in text for marker in hard_empty_markers):
        return True
    meaningful_terms = [term for term in expected_terms if term.strip()]
    if meaningful_terms and not any(term in text for term in meaningful_terms):
        return True
    return False


def encode_1688_keyword(keyword: str) -> str:
    normalized = normalize_space(keyword)
    if not normalized:
        raise ValueError("keyword is required.")
    return urllib.parse.quote_from_bytes(normalized.encode("gb18030"), safe="")


def build_1688_search_url(keyword: str) -> str:
    return f"https://s.1688.com/selloffer/offer_search.htm?keywords={encode_1688_keyword(keyword)}"


def normalize_space(value: str) -> str:
    return " ".join((value or "").split())


def build_cleanup_plan(tabs: list[TabInfo]) -> list[CleanupDecision]:
    seen_chat = False
    seen_search = False
    decisions: list[CleanupDecision] = []

    for tab in tabs:
        if tab.kind == "chat":
            if not seen_chat:
                seen_chat = True
                decisions.append(CleanupDecision(tab, "keep", "keep the active 1688 chat page"))
            else:
                decisions.append(CleanupDecision(tab, "close", "duplicate 1688 chat page"))
        elif tab.kind == "search":
            if not seen_search:
                seen_search = True
                decisions.append(CleanupDecision(tab, "keep", "keep one search/results page"))
            else:
                decisions.append(CleanupDecision(tab, "close", "duplicate 1688 search/results page"))
        elif tab.kind in {"product", "shop"}:
            decisions.append(CleanupDecision(tab, "close", "stale supplier/product tab after send pass"))
        else:
            decisions.append(CleanupDecision(tab, "keep", "not a stale 1688 supplier/product tab"))

    return decisions


def load_candidates(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        data = data.get("suppliers", data.get("candidates", []))
    if not isinstance(data, list):
        raise ValueError("Input JSON must be a list or an object with suppliers/candidates.")
    candidates: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Each candidate must be a JSON object.")
        candidates.append(item)
    return candidates


def candidate_value(candidate: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = candidate.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def build_inquiry_text(product_name: str = "", default_quantity: str = "") -> str:
    subject = f"这款{product_name}" if product_name else "这款"
    quantity_part = f"这次先按{default_quantity}报价，" if default_quantity else ""
    return (
        f"你好，{subject}有现货吗？{quantity_part}"
        "麻烦发一下起订量、含税阶梯价和交期。"
        "另外想确认下你们是工厂直供还是经销？"
        "如果打样的话，打样费、打样货期，以及后续下大货是否可退样品费，也麻烦一起说下。"
    )


def build_inquiry_plan(
    candidates: list[dict[str, Any]],
    default_quantity: str = "",
    allow_send: bool = False,
) -> list[InquiryAction]:
    actions: list[InquiryAction] = []
    for index, candidate in enumerate(candidates, start=1):
        shop_name = candidate_value(candidate, "shop_name", "supplier", "supplier_name", "店铺名", "供应商")
        product_url = candidate_value(candidate, "product_url", "url", "link", "商品链接", "链接")
        product_name = candidate_value(candidate, "product_name", "name", "title", "商品名", "产品品名")
        inquiry_text = build_inquiry_text(product_name, default_quantity)
        actions.extend(
            [
                InquiryAction(index, shop_name, product_url, "open_product", product_url, False),
                InquiryAction(
                    index,
                    shop_name,
                    product_url,
                    "send_product_context",
                    "先点击聊天输入框上方的商品卡片/链接发送按钮；没有卡片时发送商品链接。",
                    allow_send,
                ),
                InquiryAction(index, shop_name, product_url, "send_inquiry_text", inquiry_text, allow_send),
                InquiryAction(index, shop_name, product_url, "mark_pending_reply", "记录为已发询价/待回复。", False),
            ]
        )
    return actions


def namedtuple_to_dict(value: Any) -> Any:
    if isinstance(value, tuple) and hasattr(value, "_asdict"):
        return {key: namedtuple_to_dict(item) for key, item in value._asdict().items()}
    if isinstance(value, dict):
        return {key: namedtuple_to_dict(item) for key, item in value.items()}
    if isinstance(value, list):
        return [namedtuple_to_dict(item) for item in value]
    return value


def print_payload(payload: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(namedtuple_to_dict(payload), ensure_ascii=False, indent=2))
        return
    if isinstance(payload, list):
        for item in payload:
            print(item)
    else:
        print(payload)


async def cdp_call(ws: Any, command_id: int, method: str, params: dict[str, Any] | None = None, timeout: float = 10.0) -> dict[str, Any]:
    message: dict[str, Any] = {"id": command_id, "method": method}
    if params is not None:
        message["params"] = params
    await ws.send(json.dumps(message))
    end = time.time() + timeout
    while time.time() < end:
        raw = await asyncio.wait_for(ws.recv(), timeout=max(0.1, end - time.time()))
        data = json.loads(raw)
        if data.get("id") == command_id:
            return data
    raise TimeoutError(method)


async def navigate_cdp_target(target: dict[str, Any], url: str, timeout: float = 10.0) -> dict[str, Any]:
    try:
        import websockets
    except Exception as exc:  # pragma: no cover - depends on local runtime
        raise RuntimeError("Python package 'websockets' is required to reuse an existing chat tab.") from exc

    async with websockets.connect(target["webSocketDebuggerUrl"], max_size=30_000_000) as ws:
        await cdp_call(ws, 1, "Page.enable", timeout=timeout)
        return await cdp_call(ws, 2, "Page.navigate", {"url": url}, timeout=timeout)


def find_chat_target(cdp_url: str, offer_id: str = "", seller_login_id: str = "", timeout: float = 5.0) -> dict[str, Any]:
    targets = fetch_cdp_targets(cdp_url, timeout=timeout)
    chats = [target for target in targets if "def_cbu_web_im" in str(target.get("url", ""))]
    if offer_id:
        match = next((target for target in chats if str(offer_id) in str(target.get("url", ""))), None)
        if match:
            return match
    if seller_login_id:
        encoded_login = urllib.parse.quote(seller_login_id)
        match = next((target for target in chats if encoded_login in str(target.get("url", "")) or seller_login_id in str(target.get("url", ""))), None)
        if match:
            return match
    if chats:
        return chats[0]
    raise RuntimeError("No 1688 chat page found over CDP.")


def open_or_reuse_chat_tab(cdp_url: str, url: str, reuse_existing_chat: bool = True, timeout: float = 5.0) -> dict[str, Any]:
    normalized_cdp_url = normalize_cdp_url(cdp_url)
    if reuse_existing_chat:
        try:
            target = find_chat_target(normalized_cdp_url, timeout=timeout)
        except RuntimeError:
            target = None
        if target is not None:
            navigation = asyncio.run(navigate_cdp_target(target, url, timeout=timeout))
            activate_cdp_tab(normalized_cdp_url, target["id"], timeout=timeout)
            return {"mode": "reuse-existing-chat", "chat_url": url, "target": target, "navigation": navigation}

    target = open_cdp_tab(normalized_cdp_url, url, timeout=timeout)
    return {"mode": "new-tab", "chat_url": url, "target": target}


def chat_core_state_script() -> str:
    return r"""JSON.stringify((() => {
      const terms = ['\u53d1\u9001\u94fe\u63a5', '\u53d1\u9001', '\u8bf7\u8f93\u5165\u6d88\u606f', 'Enter'];
      const frame = document.querySelector('iframe[src*="def_cbu_web_im_core"]');
      let doc;
      try {
        doc = frame && (frame.contentDocument || frame.contentWindow.document);
      } catch (error) {
        return { ok: false, reason: 'core_iframe_inaccessible', frameSrc: frame && frame.src };
      }
      if (!doc) return { ok: false, reason: 'core_iframe_not_found' };
      const visible = (el) => {
        const rect = el.getBoundingClientRect();
        const style = doc.defaultView.getComputedStyle(el);
        return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
      };
      const textOf = (el) => (el.innerText || el.textContent || el.placeholder || '').replace(/\s+/g, ' ').trim();
      const body = (doc.body && doc.body.innerText || '').replace(/\s+/g, ' ').trim();
      const productLinkButtons = [...doc.querySelectorAll('button,a,div,span')]
        .filter(visible)
        .map((el) => ({ text: textOf(el), tag: el.tagName }))
        .filter((item) => item.text === '\u53d1\u9001\u94fe\u63a5');
      const composer = [...doc.querySelectorAll('textarea,input,[contenteditable="true"]')]
        .filter(visible)
        .filter((el) => el.getAttribute('contenteditable') === 'true' || el.tagName === 'TEXTAREA' || el.tagName === 'INPUT')
        .sort((a, b) => b.getBoundingClientRect().top - a.getBoundingClientRect().top)[0];
      const sendButtons = [...doc.querySelectorAll('button,[role="button"],div,span')]
        .filter(visible)
        .map((el) => ({ text: textOf(el), tag: el.tagName }))
        .filter((item) => item.text === '\u53d1\u9001');
      return {
        ok: true,
        frameSrc: frame.src,
        body: body.slice(0, 2000),
        hasProductLinkButton: productLinkButtons.length > 0,
        hasComposer: Boolean(composer),
        hasSendButton: sendButtons.length > 0,
        productLinkButtons,
        sendButtons
      };
    })())"""


def send_chat_message_script(message: str, send_product_link: bool, expected_seller_login_id: str = "") -> str:
    payload = json.dumps(
        {
            "message": message,
            "sendProductLink": send_product_link,
            "expectedSellerLoginId": expected_seller_login_id,
        },
        ensure_ascii=False,
    )
    return f"""JSON.stringify((() => {{
      const args = {payload};
      const frame = document.querySelector('iframe[src*="def_cbu_web_im_core"]');
      let doc;
      try {{
        doc = frame && (frame.contentDocument || frame.contentWindow.document);
      }} catch (error) {{
        return {{ ok: false, reason: 'core_iframe_inaccessible', frameSrc: frame && frame.src }};
      }}
      if (!doc) return {{ ok: false, reason: 'core_iframe_not_found' }};
      const visible = (el) => {{
        const rect = el.getBoundingClientRect();
        const style = doc.defaultView.getComputedStyle(el);
        return rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
      }};
      const textOf = (el) => (el.innerText || el.textContent || el.placeholder || '').replace(/\\s+/g, ' ').trim();
      const compact = (value) => (value || '').replace(/\\s+/g, '');
      const bodyText = textOf(doc.body || doc.documentElement);
      const compactBody = compact(bodyText);
      if (args.expectedSellerLoginId) {{
        const activeMarkers = [
          compact(args.expectedSellerLoginId + ' 进店'),
          compact(args.expectedSellerLoginId + ' 进厂')
        ];
        if (!activeMarkers.some((marker) => compactBody.includes(marker))) {{
          return {{
            ok: false,
            reason: 'active_contact_mismatch',
            expectedSellerLoginId: args.expectedSellerLoginId,
            body: bodyText.slice(0, 800)
          }};
        }}
      }}
      const compactMessage = compact(args.message);
      if (compactMessage.length >= 20 && compactBody.includes(compactMessage)) {{
        return {{ ok: false, reason: 'duplicate_recent_message', productLinkClicked: false }};
      }}
      const clickablePriority = (el) => {{
        if (el.tagName === 'BUTTON') return 0;
        if (el.getAttribute('role') === 'button') return 1;
        if (el.tagName === 'A') return 2;
        return 3;
      }};
      let productLinkClicked = false;
      if (args.sendProductLink) {{
        const productLinkButton = [...doc.querySelectorAll('button,[role="button"],a,div,span')]
          .filter(visible)
          .filter((el) => textOf(el) === '\\u53d1\\u9001\\u94fe\\u63a5')
          .sort((a, b) => clickablePriority(a) - clickablePriority(b))[0];
        if (!productLinkButton) {{
          return {{ ok: false, reason: 'product_link_button_not_found', productLinkClicked }};
        }}
        productLinkButton.click();
        productLinkClicked = true;
      }}
      const composer = [...doc.querySelectorAll('textarea,input,[contenteditable="true"]')]
        .filter(visible)
        .filter((el) => el.getAttribute('contenteditable') === 'true' || el.tagName === 'TEXTAREA' || el.tagName === 'INPUT')
        .sort((a, b) => b.getBoundingClientRect().top - a.getBoundingClientRect().top)[0];
      if (!composer) return {{ ok: false, reason: 'composer_not_found', productLinkClicked }};
      composer.focus();
      if (composer.tagName === 'TEXTAREA' || composer.tagName === 'INPUT') {{
        composer.value = args.message;
      }} else {{
        composer.textContent = args.message;
      }}
      composer.dispatchEvent(new InputEvent('input', {{ bubbles: true, inputType: 'insertText', data: args.message }}));
      const sendCandidates = [...doc.querySelectorAll('button,[role="button"],div,span')]
        .filter(visible)
        .filter((el) => textOf(el) === '\\u53d1\\u9001');
      sendCandidates.sort((a, b) => clickablePriority(a) - clickablePriority(b));
      const sendButton = sendCandidates[0];
      if (!sendButton) return {{ ok: false, reason: 'send_button_not_found', productLinkClicked }};
      sendButton.click();
      return {{ ok: true, reason: 'clicked_send_button', productLinkClicked }};
    }})())"""


async def evaluate_chat_script(cdp_url: str, expression: str, offer_id: str = "", seller_login_id: str = "", timeout: float = 10.0) -> dict[str, Any]:
    try:
        import websockets
    except Exception as exc:  # pragma: no cover - depends on local runtime
        raise RuntimeError("Python package 'websockets' is required for raw CDP chat automation.") from exc

    target = find_chat_target(cdp_url, offer_id=offer_id, seller_login_id=seller_login_id, timeout=timeout)
    async with websockets.connect(target["webSocketDebuggerUrl"], max_size=30_000_000) as ws:
        await cdp_call(ws, 1, "Runtime.enable", timeout=timeout)
        result = await cdp_call(
            ws,
            2,
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": True},
            timeout=timeout,
        )
    value = result.get("result", {}).get("result", {}).get("value")
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            parsed = {"value": value}
    else:
        parsed = {"raw": result}
    return {"chat_url": target.get("url", ""), **parsed}


def run_tabs(args: argparse.Namespace) -> int:
    tabs = fetch_cdp_tabs(args.cdp_url, timeout=args.timeout)
    if args.json:
        print_payload({"tabs": tabs}, True)
        return 0
    for index, tab in enumerate(tabs, start=1):
        print(f"{index}. [{tab.kind}] {tab.title} :: {tab.url}")
    return 0


def run_benchmark(args: argparse.Namespace) -> int:
    cdp_url = normalize_cdp_url(args.cdp_url)
    started = time.perf_counter()
    tabs = fetch_cdp_tabs(cdp_url, timeout=args.timeout)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    payload = {
        "cdp_url": cdp_url,
        "direct_cdp_tab_list_ms": elapsed_ms,
        "tab_count": len(tabs),
        "1688_tab_count": sum(1 for tab in tabs if tab.kind != "other"),
    }
    print_payload(payload, args.json)
    return 0


def run_cleanup_plan(args: argparse.Namespace) -> int:
    cdp_url = normalize_cdp_url(args.cdp_url)
    tabs = fetch_cdp_tabs(cdp_url, timeout=args.timeout)
    plan = build_cleanup_plan(tabs)
    applied: list[str] = []
    if args.apply:
        for decision in plan:
            if decision.action == "close":
                close_cdp_tab(cdp_url, decision.tab.id, timeout=args.timeout)
                applied.append(decision.tab.id)

    payload = {"mode": "apply" if args.apply else "plan", "decisions": plan, "closed_tab_ids": applied}
    if args.json:
        print_payload(payload, True)
        return 0
    for decision in plan:
        marker = "关闭" if decision.action == "close" else "保留"
        print(f"{marker}: [{decision.tab.kind}] {decision.tab.title} :: {decision.reason}")
    if args.apply:
        print(f"已关闭 {len(applied)} 个 1688 多余标签页。")
    else:
        print("这是清理计划；需要真正关闭时再加 --apply。")
    return 0


def run_dry_run_send_plan(args: argparse.Namespace) -> int:
    candidates = load_candidates(args.input)
    actions = build_inquiry_plan(candidates, default_quantity=args.default_quantity, allow_send=False)
    payload = {"mode": "dry-run", "actions": actions}
    if args.json:
        print_payload(payload, True)
        return 0
    for action in actions:
        print(f"{action.supplier_index}. {action.shop_name} | {action.action} | {action.text}")
    print("干跑模式：不会点击网页，也不会发送 1688 消息。")
    return 0


async def send_current_chat_message(
    cdp_url: str,
    message: str,
    send_product_link: bool = True,
    offer_id: str = "",
    seller_login_id: str = "",
    timeout: float = 10.0,
) -> dict[str, Any]:
    return await evaluate_chat_script(
        cdp_url,
        send_chat_message_script(message, send_product_link, expected_seller_login_id=seller_login_id),
        offer_id=offer_id,
        seller_login_id=seller_login_id,
        timeout=timeout,
    )


def read_message_arg(args: argparse.Namespace) -> str:
    if getattr(args, "message_file", None):
        return Path(args.message_file).read_text(encoding="utf-8-sig").strip()
    return (getattr(args, "message", "") or "").strip()


def run_chat_url(args: argparse.Namespace) -> int:
    url = build_chat_url(args.seller_login_id, args.offer_id)
    print_payload({"chat_url": url}, args.json)
    return 0


def run_search_url(args: argparse.Namespace) -> int:
    url = build_1688_search_url(args.keyword)
    print_payload({"keyword": normalize_space(args.keyword), "search_url": url}, args.json)
    return 0


def run_open_chat(args: argparse.Namespace) -> int:
    url = build_chat_url(args.seller_login_id, args.offer_id)
    payload = open_or_reuse_chat_tab(args.cdp_url, url, reuse_existing_chat=not args.new_tab, timeout=args.timeout)
    print_payload(payload, args.json)
    return 0


def run_chat_state(args: argparse.Namespace) -> int:
    state = asyncio.run(
        evaluate_chat_script(
            args.cdp_url,
            chat_core_state_script(),
            offer_id=args.offer_id,
            seller_login_id=args.seller_login_id,
            timeout=args.timeout,
        )
    )
    print_payload(state, args.json)
    return 0


def run_send_current_chat(args: argparse.Namespace) -> int:
    if not args.allow_send:
        print("拒绝发送：这个命令会真实点击 1688 发送按钮，必须显式添加 --allow-send。", file=sys.stderr)
        return 2
    if not args.seller_login_id:
        print("拒绝发送：真实发送必须提供 --seller-login-id，用来确认当前聊天对象没有错。", file=sys.stderr)
        return 2
    message = read_message_arg(args)
    if not message:
        print("拒绝发送：必须提供 --message 或 --message-file。", file=sys.stderr)
        return 2
    result = asyncio.run(
        send_current_chat_message(
            args.cdp_url,
            message,
            send_product_link=not args.no_product_link,
            offer_id=args.offer_id,
            seller_login_id=args.seller_login_id,
            timeout=args.timeout,
        )
    )
    print_payload(result, args.json)
    return 0 if result.get("ok") else 1


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fast CDP helper for 1688 inquiry workflows.")
    parser.add_argument("--cdp-url", default=DEFAULT_CDP_URL, help="Chrome/Edge remote debugging URL or port.")
    parser.add_argument("--timeout", type=float, default=5.0, help="CDP HTTP timeout in seconds.")

    subparsers = parser.add_subparsers(dest="command", required=True)

    tabs_parser = subparsers.add_parser("tabs", help="List browser tabs through direct CDP.")
    tabs_parser.add_argument("--json", action="store_true", help="Print JSON.")
    tabs_parser.set_defaults(func=run_tabs)

    benchmark_parser = subparsers.add_parser("benchmark", help="Measure direct CDP tab-list speed.")
    benchmark_parser.add_argument("--json", action="store_true", help="Print JSON.")
    benchmark_parser.set_defaults(func=run_benchmark)

    cleanup_parser = subparsers.add_parser("cleanup-plan", help="Plan safe cleanup of stale 1688 tabs.")
    cleanup_parser.add_argument("--apply", action="store_true", help="Actually close only tabs marked close.")
    cleanup_parser.add_argument("--json", action="store_true", help="Print JSON.")
    cleanup_parser.set_defaults(func=run_cleanup_plan)

    dry_parser = subparsers.add_parser("dry-run-send-plan", help="Build a supplier send plan without touching the browser.")
    dry_parser.add_argument("--input", required=True, type=Path, help="Candidate JSON list or suppliers/candidates object.")
    dry_parser.add_argument("--default-quantity", default="", help="Quantity to include in the inquiry text, such as 100套.")
    dry_parser.add_argument("--json", action="store_true", help="Print JSON.")
    dry_parser.set_defaults(func=run_dry_run_send_plan)

    chat_url_parser = subparsers.add_parser("chat-url", help="Build the 1688 Web IM URL from seller login id and offer id.")
    chat_url_parser.add_argument("--seller-login-id", required=True, help="Seller login id, such as 匠心客科教工厂.")
    chat_url_parser.add_argument("--offer-id", required=True, help="1688 offer id.")
    chat_url_parser.add_argument("--json", action="store_true", help="Print JSON.")
    chat_url_parser.set_defaults(func=run_chat_url)

    search_url_parser = subparsers.add_parser("search-url", help="Build a 1688 keyword search URL without mojibake.")
    search_url_parser.add_argument("--keyword", required=True, help="Chinese 1688 search keyword.")
    search_url_parser.add_argument("--json", action="store_true", help="Print JSON.")
    search_url_parser.set_defaults(func=run_search_url)

    open_chat_parser = subparsers.add_parser("open-chat", help="Open a 1688 Web IM URL through direct CDP.")
    open_chat_parser.add_argument("--seller-login-id", required=True, help="Seller login id.")
    open_chat_parser.add_argument("--offer-id", required=True, help="1688 offer id.")
    open_chat_parser.add_argument("--new-tab", action="store_true", help="Force opening a new chat tab instead of reusing an existing 1688 chat tab.")
    open_chat_parser.add_argument("--json", action="store_true", help="Print JSON.")
    open_chat_parser.set_defaults(func=run_open_chat)

    chat_state_parser = subparsers.add_parser("chat-state", help="Read the real chat composer state from def_cbu_web_im_core iframe.")
    chat_state_parser.add_argument("--seller-login-id", default="", help="Optional seller login id filter.")
    chat_state_parser.add_argument("--offer-id", default="", help="Optional offer id filter.")
    chat_state_parser.add_argument("--json", action="store_true", help="Print JSON.")
    chat_state_parser.set_defaults(func=run_chat_state)

    send_parser = subparsers.add_parser("send-current-chat", help="Send one message in the current 1688 chat page.")
    send_parser.add_argument("--message", default="", help="Message text to send. Prefer --message-file for Chinese text on Windows.")
    send_parser.add_argument("--message-file", type=Path, help="UTF-8 text file containing the message to send.")
    send_parser.add_argument("--allow-send", action="store_true", help="Required: actually click the 1688 send button.")
    send_parser.add_argument("--seller-login-id", default="", help="Optional seller login id filter.")
    send_parser.add_argument("--offer-id", default="", help="Optional offer id filter.")
    send_parser.add_argument("--no-product-link", action="store_true", help="Do not click the product card/link send button first.")
    send_parser.add_argument("--json", action="store_true", help="Print JSON.")
    send_parser.set_defaults(func=run_send_current_chat)

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        return int(args.func(args))
    except Exception as exc:
        print(f"1688 fast helper failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
