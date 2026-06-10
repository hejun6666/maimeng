---
name: 1688-source-factory-finder
description: Use when Codex needs to help a company user find, screen, or inquire with 1688/Ali1688 suppliers and likely source factories from a product image, keyword, 1688 product link, or current 1688 web page; covers 1688源头厂家, 供应商筛选, 工厂直供, 识图搜厂, 阿里巴巴采购, MOQ, 起订量, 阶梯价, 交期, and逐家询价.
---

# 1688 Source Factory Finder

Help non-technical purchasing colleagues find likely source factories on the 1688 web site, inquire with suppliers one by one, and summarize results into the company's procurement follow-up table. Treat this as a guided purchasing workflow, not a bulk messaging tool.

## Default User Experience

Use plain Chinese. Do not ask the user to understand browser automation, CDP, profiles, selectors, command lines, scripts, or Excel internals.

Start with:

```text
你现在手里有什么？可以发产品图片、产品关键词、1688商品链接，或者先打开1688网页给我看。
```

Then guide one action at a time:

- Ask the user to use the 1688 web site, preferably in Chrome or Edge.
- Ask the user to log in manually in the visible browser if login is needed.
- If the user has a product benchmark link or product image that should appear in the company table, keep it and reuse it for each supplier row. Do not block the workflow if it is missing.
- Never ask for 1688 account passwords, SMS codes, QR approvals, cookies, tokens, or private browser profile data in chat.
- Explain before taking each major step: search, screen, sending inquiry, reply follow-up, summary export.

## Operating Model

Use web 1688 only. In this skill, `browser-use` means the open-source Browser Use project/CLI (`browser-use` command). It does not mean Codex's built-in Browser plugin, Codex in-app browser, or a generic browser tool.

Use the open-source `browser-use` CLI as the primary automation path for the user's own visible Chrome or Edge 1688 web session. Do not limit the workflow to Chrome if Edge is available and logged in.

When open-source `browser-use` is connected but its `state`, screenshot, or eval steps are too slow for repeated 1688 tab/contact work, use `scripts/1688_fast_inquiry.py` as the direct CDP/Playwright speed helper. Treat it as an operator tool, not something normal users need to understand. Its safe default commands list tabs, benchmark CDP, plan stale-tab cleanup, and generate dry-run send plans. Any helper path that can send a real 1688 message must require that the user has asked Codex to inquire/send messages, plus the script's `--allow-send` flag; do not pause just to ask the user to approve the default wording.

For keyword search URLs, use `scripts/1688_fast_inquiry.py search-url --keyword "关键词"` or type the keyword into the visible 1688 search box. Do not hand-build the `keywords=` query with normal UTF-8 URL encoding. 1688 search may decode `keywords=` as GBK/GB18030; the wrong encoding makes the search box show mojibake and produces irrelevant results.

For 1688 Web IM, do not trust only the outer chat page text. The real contact list, product-card `发送链接`, composer, and send button may live inside the `def_cbu_web_im_core` iframe. Use the helper's `chat-url`, `open-chat`, and `chat-state` commands before concluding that chat is unavailable. On Windows, avoid PowerShell one-liners that pipe inline Chinese Python or JavaScript; use helper commands, UTF-8 JSON files, Unicode escapes, or `--message-file`.

Before any real send, verify the active chat contact, not just the outer Web IM URL. The 1688 URL can point to one supplier while the iframe is still showing an older active conversation. `send-current-chat` must include both `--seller-login-id` and `--offer-id`; if it returns `active_contact_mismatch`, do not send. Close/reopen the chat page or manually switch to the right contact, then re-run `chat-state`.

For difficult customer-service replies, use `scripts/inquiry_reply_rules.py` as the deterministic reply decision helper. It encodes the risky cases that Codex previously mishandled: short incomplete replies, external-contact requests, quantity/spec questions, quotation images, missing real replies, and order/payment prompts. Use it to decide the next status and follow-up action before summarizing or exporting.

If the run ends early because supplier replies are still pending, or if the thread needs a later check to continue the same inquiry, attach a `heartbeat` automation to the current thread instead of treating the task as finished. For one product, do not create a daily `cron` by default: the goal is to get enough usable supplier data once, not to scan forever. Use `cron` only when the user explicitly asks for an independent recurring sourcing/monitoring job across products or dates. Do not use `cron` as a workaround for an unfinished live thread.

If browser control is unavailable, downgrade to semi-automatic mode:

- Tell the user exactly which 1688 page to open or button to click.
- Ask the user to paste visible supplier details or screenshots only when automation cannot read them.
- Still screen suppliers, write inquiry drafts, and create the comparison output.

Read `references/1688-web-workflow.md` before browser work or when deciding how to open/search 1688.

## Workflow

Customer-service inquiry is mandatory for the default workflow. 筛选候选供应商不等于完成询价. When the user asks to "询价", "问7-9家", "逐家询价", or uses the default prompt, Codex must continue from candidate screening into 1688 customer-service inquiry. Do not export a final procurement table before inquiry messages are sent.

If Codex can only screen suppliers and cannot open customer service or send messages, stop and report the blocker. In that case, label any file as a candidate screening draft, not a completed supplier inquiry/procurement table.

1. Identify the input route:
   - Product image: use 1688 image search.
   - Keyword: search 1688 by keyword.
   - 1688 product link: inspect that item, the shop, same/similar items, and related shops.
   - Current 1688 page: continue from visible search results, product page, shop page, or inquiry chat.

2. Search for candidates:
   - Keep the inquiry goal at 7-9 suppliers per run. 7-9 suppliers is the default balance between useful comparison and browser workload.
   - Build a 候选池 from search-result cards first, ideally 12-18 candidates, using fast page extraction when possible instead of opening every product detail page.
   - Screen the 候选池 down to 7-9 suppliers before opening customer service.
   - Fewer than 7 is acceptable when results are weak, repetitive, or automation is blocked.
   - Do not spend the run on pages that are clearly unrelated, duplicate, or low quality.

3. Screen candidates before messaging:
   - Prefer likely source factories over simple low price.
   - Use source-factory signals, reseller risk signals, and evidence rules from `references/supplier-evaluation.md`.
   - Do not claim a supplier is definitely a source factory unless the page or reply proves it. Use wording such as "更像源头厂" or "需要进一步确认".
   - Screening output is only a candidate list. It is not the final deliverable when the task includes inquiry.

4. Use the default inquiry strategy without asking for wording approval:
   - When the user asks Codex to find factories and inquire, ask 7-9 suppliers, or directly says to send, that request is the start authorization for the default inquiry wording. Do not stop to ask "话术可以吗" or "确认开始吗".
   - Before sending, only ask the user in Codex chat for missing business decisions that materially change the quote and cannot be inferred from the product page, such as required size, color, model, package, or a target quantity with no page MOQ/context. Do not ask for wording approval.
   - Default quantity rule: prefer the user's provided quantity. If no quantity was provided, use the page MOQ / page起订量 as the first quote quantity when visible. If neither exists, ask the supplier to quote by their normal MOQ without inventing a target purchase quantity.
   - Use this default wording style: first send the product card/link, then ask whether it is in stock, the tax-included price or clearly labeled untaxed price, MOQ, lead time, whether they are the factory/source supplier, sample fee, sample lead time, and whether the sample fee can be refunded after a bulk order.
   - Continue supplier by supplier until the target count is handled, the user stops the task, or a mandatory stop condition appears.
   - If replies are still pending and the run would otherwise stop early, attach a heartbeat before pausing so the thread can resume later. Keep this finite: use short reply-check rounds for the current product, then close non-responders instead of waiting forever.

5. Send product context before inquiry text:
   - 先发送商品卡片/商品链接，再发送询价话术.
   - When entering 1688 customer service from a product page, the chat interface often shows the product card/link with a send button just above the input box. Click that product-card/link send control directly so the supplier knows which item is being discussed.
   - Do not spend repeated `state`/screenshot cycles searching for this control when it is visibly above the input box. Send the product context, then immediately send the inquiry text.
   - If the product card/link prompt is not available, paste or send the direct product URL before the inquiry message when it is safe to do so.
   - If the product-card `发送链接` button disappears after opening customer service, do not send a bare inquiry. Send the direct product URL first, then send the inquiry text, and mark that product context was sent as a URL fallback.
   - Do not send a bare inquiry message without product context unless the user explicitly says the supplier already knows which product is being discussed.

6. Run inquiries one by one like a human, but keep the browser light:
   - 逐家模拟人工操作, but avoid unnecessary waiting, repeated page-wide inspection, and tab buildup.
   - Use two passes: a send pass and a reply collection pass.
   - Send pass: open one selected supplier, check only what is needed, open or reuse customer service, send the product context, send the adapted inquiry, verify it appears in chat, record `已发询价/待回复`, then move to the next supplier.
   - Reply collection pass: after the 7-9 suppliers have been asked, revisit the same chat page/contact list to collect real replies, follow up on missing fields, and update the export data.
   - Do not batch-send, rapid-fire messages, or use 1688 one-click bulk inquiry features.
   - Do not stop for confirmation before every supplier.
   - Open or inspect one supplier at a time.
   - Re-check whether the supplier still looks worth asking before sending.
   - Slightly adapt the message using the product name, visible specification, or shop context.
   - Do not paste the exact same message mechanically to every supplier.
   - Do not send to the same supplier repeatedly.
   - Do not repeat the same inquiry or full missing-field follow-up in the same chat. Before sending a follow-up, check recent chat history. If the same supplier has already been asked for 含税报价、起订量、交期、样品费、打样货期, do not paste the same paragraph again; wait for the reply or ask only the specific newly missing field.
   - Keep a per-supplier status: `待发送`, `已发商品`, `已发询价`, `待回复`, `已回复但缺字段`, `已追问`, `需用户确认规格`, `需用户确认数量`, `已拿到报价`, `要求外部联系`, `暂不跟进`.
   - Reuse the existing 1688 chat page when possible. Do not keep opening new chat windows or tabs for every supplier; if a new product/detail tab was needed only to enter chat, close that extra tab after the inquiry is sent.
   - Keep browser memory under control: prefer one search/results tab and one chat tab/page, switch contacts inside the chat page, and close stale supplier/product tabs as the run proceeds.
   - Treat tab cleanup as mandatory, not optional: run `scripts/1688_fast_inquiry.py cleanup-plan --apply` before the send pass, after each supplier send if extra 1688 tabs appeared, before reply collection, and before final/in-progress export. Keep at most one 1688 search/results tab plus one 1688 chat tab unless the user explicitly asks to inspect a product page.

7. Wait for real customer-service replies and chase missing fields:
   - After sending the product context and inquiry text, wait for a real new customer-service message before extracting MOQ, tax-included price, sample fee, sample lead time, direct-factory answer, or lead time.
   - Do not treat product-page price, shop page text, or existing page information as a customer-service reply.
   - Do not end the task just because the first inquiry message was sent. The goal is to obtain the needed purchasing fields or clearly mark what is still missing.
   - An incomplete reply such as "在", "有货", "稍等", "好的", "放心下单", or "可以拍" is not enough. Continue waiting or send a polite follow-up asking for the missing fields.
   - If the supplier asks to send contact details privately, add WeChat, call by phone, or have a salesperson contact the buyer, do not stop and do not provide contact details. Reply politely: `我们先在1688这边沟通和报价就可以，麻烦请直接在1688这里发就可以，谢谢。`
   - If the supplier asks "要多少", first use the user-provided quantity. If the current workflow already used a default such as 100套, reply `先按100套报价`. If no quantity was provided, use the page MOQ / page起订量 when visible. If neither is available, ask them to quote by their normal MOQ. Stop for user input only when quantity genuinely changes the business decision and there is no page MOQ or prior default.
   - If the supplier asks for exact size, color, model, packaging, customization, drawing, logo, destination, or other spec, first check whether the product card/link already makes the item clear. If it does, reply `就按刚才这个链接里的款式` and keep asking for the missing quote fields. Stop and ask the user only when the supplier must choose among multiple sizes, colors, models, sets, customizations, or drawings that cannot be inferred from the product card/link.
   - If the supplier sends a 报价图片, price table image, screenshot, PDF preview, or spreadsheet image, open or screenshot it and extract price/MOQ/lead-time/sample details visually. If it cannot be read, ask the user for a clearer image rather than marking the supplier as no useful reply.
   - Treat right-side shop profile data as factory-screening evidence only. It can support "工厂/深度验厂/员工人数/厂房面积" judgement, but it does not replace customer-service confirmed quote fields.
   - Do not click `立即下单`, `加入采购车`, `一键询价`, `立即铺货`, payment, deposit, order, or contract controls while following up.
   - No reply means `待回复`. In that case, leave MOQ/报价/交期 as `待回复` or mark page-only information clearly as `页面展示，未客服确认`.
   - Do not end the task immediately after sending the final inquiry. Make at least one reply-check pass over sent chats, then export actual replies and mark no-reply suppliers as `待回复`.
   - Non-responding suppliers should not block the whole product forever. After the configured heartbeat/check rounds, mark them `超时未回复/暂不跟进`, keep `未回复` in the quote/MOQ/lead-time cells, and finish the comparison with the suppliers that provided usable data.

8. Stop on supplier replies that require real business decisions:
   - If customer service asks for destination, exact spec, customization, drawings, company details, payment terms, formal order details, or another decision that cannot be inferred from the product page and confirmed strategy, stop and ask the user.
   - Do not stop only because the supplier asks for WeChat, phone, or private contact. Politely keep the conversation on 1688.
   - Do not stop only because the supplier asks for quantity when a user-provided quantity, default quantity, or page MOQ can answer it.
   - Do not invent purchasing quantity, address, company background, phone, payment terms, or commitments.

9. Summarize and export:
   - First answer in chat with counts, best candidates, weak candidates, actually sent/not-sent status, and next actions.
   - Then export the company procurement follow-up file with `scripts/factory_inquiry_export.py` only after inquiry messages have actually been sent, or after the user explicitly asks for a screening-only candidate table.
   - Do not export or present a final supplier table while rows are still `待回复`, `待客服确认`, `已追问`, `回查异常`, or `缺字段`. In that case continue reply collection, or export only an explicitly named `in-progress` / `draft` file with `--allow-in-progress`.
   - In the main `报价含税价`, `起订量`, and `交期` columns, put only customer-service-confirmed values. Page-only values such as `页面显示194元` or `页面显示1件起批` belong in `备注`, not in the main quote/MOQ columns.
   - If customer service only gives `未税价`, `不含税`, or `开票加13%`, keep it in the main price column only when it is clearly labeled as `未税报价（非含税价，开票/税点见原话）`. Do not silently convert it into a confirmed tax-included price.
   - If the chat page shows `尚未选择联系人`, that is a chat-switch failure, not a supplier reply. Retry opening/switching to the intended `sellerLoginId`; if still blocked, mark that supplier `回查异常/待回复`, continue other suppliers, and never export a final table from that state.
   - If the user returns later and says "帮我整理1688回复", re-open the relevant 1688 chats and extract MOQ, tax-included price, sample fee, sample lead time, whether sample fee is refundable after bulk order, lead time, direct-factory answer, and follow-up advice.
   - After the task is finished and the user does not need the browser left open, close open-source browser-use sessions with `browser-use close --all`. Do not rely on the user clicking the window X as cleanup, because the browser-use daemon/session may keep the window alive or reopen it on the next command.

## Browser Cleanup

At the end of a normal run, close open-source browser-use sessions:

```bash
browser-use close --all
```

Skip cleanup only when the user explicitly asks to keep the 1688 page open for manual checking or when Codex is waiting for supplier replies in the same session. If cleanup is skipped, tell the user that the browser-use window may stay open until the session is closed.

## Default Inquiry Message

Use a medium-length first message. Adapt the product name naturally:

```text
你好，这款{产品名或规格}有现货吗？我想了解一下起订量、含税阶梯价和交期。另外想确认下你们是工厂直供还是经销？如果打样的话，打样费、打样货期，以及后续下大货是否可退样品费，也麻烦一起说下。
```

If the product name is unknown, use:

```text
你好，这款有现货吗？我想了解一下起订量、含税阶梯价和交期。另外想确认下你们是工厂直供还是经销？如果打样的话，打样费、打样货期，以及后续下大货是否可退样品费，也麻烦一起说下。
```

Do not add phone numbers, addresses, company names, target quantities, shipping destinations, or payment promises unless the user provided them for this supplier workflow.

## Default Follow-Up Messages

For an incomplete reply:

```text
好的，麻烦再发一下这款的含税报价、起订量、交期、样品费和打样货期；如果有阶梯价也一起发下，谢谢。
```

For private contact requests:

```text
我们先在1688这边沟通和报价就可以，麻烦请直接在1688这里发就可以，谢谢。
```

For quantity requests when a page MOQ is visible:

```text
先按页面起订量报价就可以，麻烦发一下含税价、交期和样品相关费用。
```

For quantity requests when the strategy already uses 100 units:

```text
先按100套报价，麻烦发一下含税价、交期和样品相关费用。
```

For spec questions when the current product link/card is clear:

```text
就按刚才这个链接里的款式，麻烦发一下含税价、起订量、交期、样品费和打样货期。
```

## Mandatory Stop Conditions

Stop immediately and ask the user when any of these appear:

- CAPTCHA, slider verification, QR verification, login failure, or account risk prompt.
- Any platform warning that suggests frequent messaging, abnormal behavior, or account limitation.
- The page asks for account password, SMS code, payment, deposit, order submission, contract signing, or identity verification.
- Customer service asks a business question beyond the default first inquiry.
- A message would expose sensitive company or personal information.
- The next click could place an order, pay money, bind a phone, add an external contact, or submit a formal quote request with commitments.
- The page structure is unclear enough that Codex cannot tell whether it is sending, ordering, deleting, or changing account state.

Never bypass verification or coach the user to evade platform restrictions.

## Export

Do not use search-result URLs as final supplier/product links. Open the supplier's product page, shop page, or 1688 chat context and record that direct link. A URL like `s.1688.com/selloffer/offer_search` is only a search results page and must not be placed in the final `链接` column.

Use the bundled exporter for deterministic table output:

```bash
python scripts/factory_inquiry_export.py --input suppliers.json --output 1688-suppliers.xlsx
```

This command is for completed inquiry records. If any row is still waiting for reply, missing fields, or has chat回查异常, do not use a final-looking filename. Use:

```bash
python scripts/factory_inquiry_export.py --input suppliers.json --output 1688-suppliers-in-progress.xlsx --allow-in-progress
```

CSV is also supported:

```bash
python scripts/factory_inquiry_export.py --input suppliers.json --output 1688-suppliers.csv
```

The input can be a JSON list or an object with a `suppliers` list. Export only the screenshot columns from the company procurement table:

- `product_image`: 产品图片.
- `product_name`: 产品品名.
- `benchmark_url`: 产品对标链接.
- `shop_name`: 供应商.
- `tax_included_price`: 报价含税价.
- `moq`: 起订量.
- `lead_time`: 交期.
- `product_url`: 链接.
- `remarks`: 备注, including ex-factory price, sample fee, sample lead time, sample-fee refund condition, packaging/customization notes, and reply summary.
- `sample_owner`: 样品负责人.
- `progress`: 进度.

Do not add extra AI support columns to the Excel/CSV. Source-factory judgement, reply summary, and follow-up advice can go into `remarks` or stay in the chat summary, but the exported file should contain only the screenshot columns.

Do not put page-only price/MOQ in the main quote columns. If the supplier has not confirmed price/MOQ/lead time in chat, set the main column to `待客服确认` or `待回复`, and put page-only information in `remarks`.

## Output Style

For normal users, keep the chat summary short and practical:

- 已筛选/已询价数量.
- 已发送商品链接/商品卡片数量.
- 已收到真实客服回复数量.
- 最值得跟进的 3 家.
- 暂不建议的原因.
- 哪些还没回复.
- Excel 文件路径 or CSV 文件路径, using only the screenshot columns.
- 需要用户补充的最小信息.

Do not present long technical logs. If automation failed, explain the blocker in ordinary language and give the next smallest user action.

## Prompt Examples

```text
我有一张产品图，帮我找1688源头厂家，问7-9家左右。
```

```text
帮我找婴儿围栏的1688厂家，直接按默认话术一家一家问，不用先问我确认话术。
```

```text
我已经打开1688搜索页了，你帮我筛像源头厂的供应商。
```

```text
帮我整理昨天1688客服回复，看看哪几家值得继续问。
```
