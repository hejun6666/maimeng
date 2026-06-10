# 1688 Web Workflow

Use this reference when opening, searching, or inspecting 1688 web pages.

`browser-use` in this skill means the open-source Browser Use project/CLI and the `browser-use` command. Do not interpret it as Codex's built-in Browser plugin, Codex in-app browser, or a generic web browsing feature.

## Browser Choice

Use the user's logged-in web browser session when possible.

Preferred order:

1. A visible Chrome or Edge 1688 session controlled by the open-source `browser-use` CLI.
2. A visible Chrome or Edge session opened through `uvx --python 3.11 browser-use` if the global `browser-use` command is missing.
3. Direct CDP connection to the user's already logged-in Chrome or Edge as a technical fallback, especially when browser-use page scans are too slow.
4. Manual guidance if browser automation is unavailable.

Do not require Chrome when Edge is the user's normal 1688 browser.

## Opening 1688

For installed browser-use:

```bash
browser-use --headed open "https://www.1688.com"
```

Without a global install:

```bash
uvx --python 3.11 browser-use --headed open "https://www.1688.com"
```

If login is required, ask the user to log in in the visible page and reply `已登录`. Do not request credentials in chat.

## Search Routes

### Product Image

Use 1688 image search when the user provides a product image. If the image search entry is not visible, ask the user to open the 1688 page where the camera/search-by-image button is visible, then continue from the results page.

For unfamiliar toy/product names from English packaging or Amazon images, do not burn the run trying many translated keywords. Make at most two keyword attempts. If the results are empty, irrelevant, or show "没有相关商品"/"这里空空如也", switch away from keyword search to image search, pasted image search, a known direct 1688 product link, or an external search for an exact 1688 offer. Record that the keyword route failed rather than spending minutes on more synonyms.

### Keyword

Search by the user's keyword. Keep the keyword close to the product language buyers use on 1688, such as `婴儿围栏`, `儿童游戏围栏`, or the product's Chinese category name.

Do not hand-build `keywords=` with normal UTF-8 URL encoding. 1688 keyword search can treat URL keywords as GBK/GB18030; a UTF-8-built URL can put mojibake in the search box and return nonsense results. Use the helper:

```bash
python scripts/1688_fast_inquiry.py search-url --keyword "双头马克笔套装" --json
```

Then open the returned `search_url`, or type/paste the Chinese keyword into the visible 1688 search box and submit it from the page.

If a page shows unrelated categories, no expected product terms, or only recommendation filler after two keyword attempts, stop that route. Use `scripts/1688_fast_inquiry.py` logic such as `should_switch_keyword_strategy` in helper tests as the standard: two keyword attempts, then switch away from keyword search.

### Product Link

Inspect:

- Product title, visible price, MOQ, specs, and shop name.
- Shop profile, factory or reseller signals.
- Same/similar products and related shop products if available.

### Current Page

If the user already has a search results page or product page open, continue from that page. Do not restart the search unless the current page is clearly wrong.

## Efficiency and Browser Memory

The default run should ask 7-9 suppliers, not 15. More suppliers can be done in a second batch after the first batch is sent and replies are collected.

Work in batches:

1. Build a candidate pool from the search results page. Prefer `browser-use eval` or visible search-result cards to collect product links, titles, shop names, prices, and factory signals. Do not open every search result just to screen it.
2. Select 7-9 suppliers from that candidate pool.
3. Use a send pass: send the product card/link and inquiry text to the 7-9 suppliers one by one, then mark them `待回复`.
4. Use a reply collection pass: return to the message/contact list, read replies, follow up on missing fields, and update the table.

Reuse one chat page whenever possible. Keep at most one search/results page and one chat page active. Do not open a new chat window for every supplier, and close stale product/detail tabs after sending. If 1688 opens a new chat tab, use it for the current supplier, then return to the same chat page/contact list rather than accumulating windows.

Tab cleanup is a required checkpoint, not a nice-to-have. Run `scripts/1688_fast_inquiry.py cleanup-plan --apply` before the send pass, after each supplier if extra 1688 tabs appeared, before the reply collection pass, and before export. This cleanup only closes stale 1688 product/shop pages plus duplicate 1688 search/chat pages; it must not close unrelated Feishu, ERP, or user work tabs.

If the user needs to choose product information such as target quantity, size, color, model, or packaging, ask in Codex chat. Do not burn browser time trying to infer business choices from unrelated 1688 pages.

## Fast CDP Helper

When open-source `browser-use` is connected but repeated `state`, screenshot, or eval calls are slowing the run down, use the local helper:

```bash
python scripts/1688_fast_inquiry.py tabs
python scripts/1688_fast_inquiry.py benchmark
python scripts/1688_fast_inquiry.py cleanup-plan
python scripts/1688_fast_inquiry.py search-url --keyword "双头马克笔套装" --json
python scripts/1688_fast_inquiry.py dry-run-send-plan --input candidates.json --default-quantity 100套
python scripts/1688_fast_inquiry.py chat-url --seller-login-id 匠心客科教工厂 --offer-id 633516066121
python scripts/1688_fast_inquiry.py open-chat --seller-login-id 匠心客科教工厂 --offer-id 633516066121
python scripts/1688_fast_inquiry.py chat-state --seller-login-id 匠心客科教工厂 --offer-id 633516066121
```

Use it for high-frequency mechanical work: tab listing, speed checks, stale 1688 product/detail tab cleanup plans, and dry-run supplier send plans. This keeps the run to one search/results page and one chat page instead of letting product/chat tabs pile up.

`open-chat` reuses an existing 1688 chat tab by default and navigates it to the intended supplier. Use `--new-tab` only for a deliberate debugging exception.

`cleanup-plan` is a plan only unless `--apply` is added. During real runs, use `--apply` at the cleanup checkpoints above. It should close stale 1688 product/detail duplicates, not unrelated Feishu, ERP, or other work tabs.

The helper includes a guarded `send-current-chat` path for maintainer testing. Codex may use it only when the user has asked Codex to inquire/send messages; do not pause just to ask the user to approve the default wording. Real sending also requires the script's `--allow-send` flag and the exact `--seller-login-id`; do not rely on `--offer-id` alone. Prefer `dry-run-send-plan` and `chat-state` first, then send one supplier at a time.

If the current run ends with supplier replies still pending or the thread needs a later check to continue the same inquiry, attach a `heartbeat` automation to the thread rather than marking the job finished. For one product, do not create a daily `cron` by default; the goal is to get enough usable supplier data once, then stop. Use `cron` only for standalone recurring sourcing/monitoring jobs that the user explicitly asks for, not as a substitute for an unfinished live thread.

On Windows, Do not pipe inline Chinese Python or JavaScript through PowerShell for 1688 work. Chinese keywords can turn into `????`, causing irrelevant searches and wasted time. Use checked-in helper scripts, Unicode escapes inside JavaScript snippets, JSON files, or `--message-file` for Chinese inquiry text.

## Candidate Screening Is Not Inquiry

Do not stop at a supplier screening table when the user asked to inquire or ask suppliers. Screening results are only candidates.

Before final export, open each selected supplier's product page, shop page, or customer-service entry. Do not put 1688 search-result URLs in the final `链接` column. Links like `https://s.1688.com/selloffer/offer_search...` or `s.1688.com/selloffer/offer_search` mean Codex is still on a search page, not on a confirmed supplier/product record.

If customer service cannot be opened or sending is blocked, stop and say the inquiry step is blocked. Export only a clearly named candidate draft if the user asks for it.

If inquiry has started but rows are still `待回复`, `待客服确认`, `已追问`, `回查异常`, or `缺字段`, do not export a final-looking `.xlsx`. Continue the reply collection pass, or export only an explicitly named `in-progress` / `draft` file with `--allow-in-progress`. Page-only values must stay in remarks; `报价含税价`, `起订量`, and `交期` should contain customer-service-confirmed values only. If the supplier only gives `未税价`, `不含税`, or says invoice/tax is added separately, keep the quote in the price column only when it is clearly labeled as `未税报价（非含税价，开票/税点见原话）`.

If the chat page says `尚未选择联系人`, do not treat the page as read or the inquiry as complete. Retry opening the direct Web IM URL for the intended `sellerLoginId` or switch the contact inside the one reused chat page. If it still fails, mark only that supplier as `回查异常/待回复`, continue the reply collection pass for the other suppliers, and export only an `in-progress` file if the user needs a snapshot.

If replies are still pending and the run would otherwise stop early, schedule a heartbeat before pausing so the thread can resume later. Keep the heartbeat finite for the current product: after the configured reply-check rounds, mark non-responders as `超时未回复/暂不跟进`, put `未回复` in quote/MOQ/lead-time cells, and finish the comparison with the suppliers that provided usable data.

## Messaging Behavior

Send only from the user's logged-in account and only inside the visible 1688 web page.

Before sending the inquiry text, check for the 1688 product card/link prompt in the chat window. The product card/link send button above the input box is usually the fastest path. If the interface shows a selected product card, product link, or "发送" control for the current product, send that product context first. This is mandatory because otherwise the supplier may not know which product the inquiry is about.

Do not repeatedly run expensive page-wide `state` or screenshot commands when the send button is visibly above the input box. Click the visible product context send control, then immediately send the inquiry text.

1688 Web IM may render the real contact list, product card, `发送链接`, composer, and `发送` button inside the `def_cbu_web_im_core` iframe. The outer page may only show "下载插件 / 唤起客户端 / 聊天设置 / 下载客户端". Do not conclude that there is no chat input until `chat-state` or an equivalent iframe inspection has checked `def_cbu_web_im_core`. If clicking `客服` opens a temporary `blob:https://detail.1688.com/...` page or fails to switch contacts, extract `sellerLoginId` / `offerLoginId` and `offerId` from the product page, then use `open-chat` to build the direct Web IM URL.

When sending Chinese text from the helper, write the message to a UTF-8 file and use:

```bash
python scripts/1688_fast_inquiry.py send-current-chat --seller-login-id 匠心客科教工厂 --offer-id 633516066121 --message-file message.txt --allow-send
```

Do not put long Chinese inquiry text directly into a PowerShell one-liner.

Before sending, confirm `chat-state` shows the intended supplier as the active conversation. The outer Web IM URL is not enough: 1688 can keep an older active chat inside `def_cbu_web_im_core`. If `send-current-chat` returns `active_contact_mismatch`, stop and switch contacts or close/reopen the chat page before trying again.

Before the first send, use the default inquiry strategy without asking the user to approve the wording:

- Supplier count and selection logic.
- Send the product card/link prompt first, then the default inquiry text.
- Default quantity rule: use user-provided quantity first; otherwise use page MOQ / page起订量 if visible; otherwise ask the supplier to quote by their normal MOQ.
- Follow-up rules: chase incomplete replies, keep contact on 1688, and stop only for real business decisions or safety risks.

Do not stop for start approval or per-supplier approval. Run one supplier at a time:

1. Open the supplier's product page or exact product context.
2. Open customer service from that product context.
3. Send the product card/link prompt first if visible; otherwise send the direct product URL when safe.
4. Send the inquiry message.
5. Verify the chat shows both the product context and inquiry text.
6. Wait for a real new customer-service message before treating any MOQ, price, lead time, or sample detail as a reply; in other words, wait for a real new customer-service message from the supplier, not just existing page content.
7. If the reply is incomplete, send the smallest polite follow-up needed to get the missing fields.
8. Record status and move to the next supplier.

Do not batch-send, bulk-inquire, use one-click inquiry, or fire messages rapidly. The workflow should simulate a human buyer: one supplier, one product context, one inquiry, one reply/follow-up loop, then the next supplier.

Do not repeat the same inquiry or full missing-field follow-up in one supplier chat. Before sending a follow-up, scan recent outgoing messages in the active conversation. If the buyer already asked for 含税报价、起订量、交期、样品费、打样货期, do not paste that same paragraph again; wait, or ask only the exact missing item after a real supplier reply.

This does not mean waiting for a complete quote before moving on. In the send pass, once the product context and inquiry text are sent and verified, record the supplier as `待回复` and continue to the next supplier. In the reply collection pass, revisit the same contact list to collect replies and follow up.

To avoid memory problems, reuse one chat page and switch contacts inside it. Rule: do not open a new chat window for every supplier. Close extra product/detail tabs after their inquiry is sent.

Do not extract product-page price, shop text, old chat text, or other existing page information as a customer-service reply. If no new supplier reply arrives during the run, mark the supplier as `待回复`. 页面已有信息不能冒充客服回复.

When exporting, keep that same distinction: product-page price or page MOQ may be recorded in `备注`, but not in the main `报价含税价` or `起订量` columns unless customer service confirmed it.

## Reply Handling

Treat replies as a loop, not as a one-shot send.

For ambiguous or high-risk replies, apply `scripts/inquiry_reply_rules.py` before deciding whether to wait, follow up, ask the user, or stop. The expected statuses include:

- `已回复但缺字段`: short replies such as "在/有货/稍等/好的/放心下单" are not enough; send the missing-field follow-up.
- `要求外部联系`: if the supplier asks for WeChat, phone, or private contact, keep the conversation on 1688 and do not ask the user for contact details.
- `已追问`: if the supplier asks for quantity or spec and the current strategy/product card gives enough context, reply with that context.
- `需用户确认数量` or `需用户确认规格`: ask the user in Codex chat only when there is no default quantity, page MOQ, or clear product context.
- `需识别报价图`: quotation images, price-table screenshots, PDFs, and spreadsheet previews must be opened or screenshot/OCR checked.
- `待回复`: old page text, product-page price, or shop profile data does not count as a new customer-service reply.
- `安全暂停`: stop for payment, deposit, order submission, contract, account-risk, or verification prompts.

- "在", "有货", "稍等", "好的", "可以拍", "放心下单", and similar short answers are incomplete. Continue waiting or ask for price, MOQ, lead time, sample fee, and sample lead time.
- If the supplier asks for contact details privately, phone, WeChat, or says a salesperson will contact the buyer, do not provide contact details and do not stop. Reply: `我们先在1688这边沟通和报价就可以，麻烦请直接在1688这里发就可以，谢谢。`
- If the supplier asks for quantity, use the user's quantity first. If the current strategy already says 100套, reply `先按100套报价`. If missing, use the page MOQ / page起订量. If neither is available, ask them to quote by their normal MOQ. Stop for the user only if quantity is a real business decision that cannot be inferred.
- If the supplier asks for exact size, color, model, package, logo, drawing, destination, or customization information, first check the same product link/card already sent in chat. If the same product link is clear, reply `就按刚才这个链接里的款式` and continue asking for quote fields. Stop and ask the user only if the supplier must choose among multiple specs that cannot be inferred from the product card/link.
- If the supplier sends a quotation image, price table image, PDF preview, screenshot, or spreadsheet image, open it or screenshot it and extract the visible price/MOQ/lead-time/sample details. If unreadable, ask for a clearer image or the key numbers in text.
- Right-side shop profile data is factory-screening evidence only. It can support factory judgement, but it cannot replace customer-service confirmed quote fields.
- Do not click order, payment, deposit, procurement cart, `立即下单`, `加采购车`, `一键询价`, or similar action buttons during inquiry follow-up.

## End-of-Task Cleanup

When the 1688 task is complete and the user does not need the browser left open, close browser-use sessions from the CLI:

```bash
browser-use close --all
```

Do not treat clicking the browser window X as reliable cleanup. The open-source browser-use daemon/session can remain active, and later commands may reopen a window.

## Automation Failure Handling

If open-source browser-use, CDP fallback, or page extraction fails:

- Tell the user the simple blocker, such as "我现在读不到这个页面".
- Ask for one small action, such as keeping the page open, logging in, switching to Chrome/Edge, or copying one visible supplier row.
- Continue in semi-automatic mode rather than abandoning the workflow.
