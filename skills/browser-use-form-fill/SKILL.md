---
name: browser-use-form-fill
description: Use when a user asks Codex to fill, enter, copy, import, or check data in a website, web system, online form, government portal, finance/tax portal, CRM, spreadsheet-backed form, or already logged-in browser page.
---

# Browser Use Form Fill

Help non-technical users put their data into a website. Hide CLI details unless debugging is needed. The user should only need to provide a website/page and data.

## User-Facing Behavior

Use plain language. Do not ask the user to understand `browser-use`, element indices, Chrome profiles, CDP, or command lines.

Ask only for missing essentials:

- Website/page to open, unless already clear.
- Data to fill, unless already provided.
- Whether they are logged in, only if the page requires login and the state is unknown.

If login is needed, open a visible browser and ask the user to log in manually. Continue after they say login is done.

Never ask the user to send passwords, SMS/OTP codes, QR approval links, UKey PINs, certificate passwords, face verification data, or similar secrets in chat. Have the user complete those steps directly in the visible browser window.

## Tooling

Use `browser-use` CLI. Do not clone the browser-use repository. Do not write Python scripts unless the user explicitly asks.

Before the first browser action on a user's computer, run the bundled environment check:

```bash
python skills/browser-use-form-fill/scripts/check_browser_env.py
```

If this skill is installed outside the repository, resolve the script relative to this `SKILL.md` file. The script checks whether `browser-use` or `uvx` is available and whether Google Chrome, Microsoft Edge, or Chromium is installed. If the script reports `NOT READY`, explain the missing item in plain language and help the user fix that before continuing.

Choose commands in this order:

1. If installed, use `browser-use`.
2. Else if available, use `uvx --python 3.11 browser-use`.
3. Else ask for permission in plain language to install the browser automation tool, then use the official installer:

```bash
curl -fsSL https://browser-use.com/cli/install.sh | bash
```

After installation, run diagnostics:

```bash
browser-use doctor
```

## Opening Logged-In Sites

For normal company users, prefer a visible browser using the browser where they normally log in. Google Chrome and Microsoft Edge are both acceptable.

When the user's normal browser is Chrome, prefer:

```bash
browser-use --headed --profile Default open "https://example.com"
```

or, without global install:

```bash
uvx --python 3.11 browser-use --headed --profile Default open "https://example.com"
```

When the user's normal browser is Edge, first try the same visible browser workflow. If the opened window does not show the logged-in account, ask the user to log in manually in that visible browser window. Use profile enumeration, custom profile paths, or CDP only for technical users who are comfortable with browser setup details.

If the user insists on an already-open tab, explain briefly that Codex can only control a browser session that browser-use can connect to. Use Chrome remote debugging/CDP only when the user is comfortable with that setup.

## Fill Workflow

1. Convert the user's input into clear field/value pairs. For files, inspect the file first and extract the relevant rows/fields.
2. Open the page visibly with the chosen browser-use command.
3. Run `state` to inspect labels, inputs, buttons, dropdowns, and page text.
4. Match values to fields by visible label, placeholder, nearby text, table header, ARIA name, section title, and business context.
5. Fill with `input`, choose dropdowns with `select`, click checkboxes/radios/navigation with `click`, and upload files with `upload`.
6. Re-run `state`, `get value`, or take a `screenshot` after meaningful steps.
7. Stop on the filled page, draft page, or review page for the user to inspect.

## Guardrails

Do not invent missing data. If a required value is missing or a field mapping is unclear, stop and ask for that specific value.

Never click final or destructive actions unless the user explicitly confirms in the current turn. Treat these as stop points:

```text
提交, 确认提交, 申报, 确认申报, 缴款, 支付, 签名, 签章, 发送,
删除, 作废, 红冲, 确认抵扣, submit, confirm, pay, sign, delete
```

Ordinary navigation such as `下一步`, `继续`, `保存草稿`, `Continue`, `Next`, and `Save draft` is allowed when needed to fill or reach a review page.

## Failure Handling

If browser-use says the session is running with a different config, close that browser-use session and reopen with the intended flags.

If an element is missing, scroll, wait for the page, or run `state` again.

If the website blocks automation, asks for CAPTCHA, UKey, QR code, SMS, certificate, or face verification, pause and ask the user to complete it manually in the visible browser.

If the data is too messy to map safely, summarize what is understood and ask for a cleaner file or confirmation.

## Final Response

Keep the final response short and employee-friendly:

- What page is open.
- What was filled.
- What was skipped or needs review.
- Screenshot path if taken.
- State that the browser is left open for the user to check.
