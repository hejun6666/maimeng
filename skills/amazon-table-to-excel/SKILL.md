---
name: amazon-table-to-excel
description: Exports tables from Amazon and Amazon Seller Central webpages to Excel using browser-use and deterministic DOM extraction. Use when the user gives an Amazon/Seller Central link or asks to export webpage tables, fee tables, pricing tables, or HTML tables to XLSX.
---

# Amazon Table To Excel

Export all webpage tables from an Amazon or Seller Central page into an Excel workbook.

## Employee-friendly rule

This skill is for non-technical coworkers who only know how to ask Codex for help. Do the technical work yourself. Do not show shell commands, browser-use details, profile names, DOM details, or Python package names unless debugging with a technical owner.

The coworker should only need to provide an Amazon URL and follow plain-language browser instructions.

## Workflow

1. Get the URL if the user did not provide one.
2. Open the page visibly with `browser-use`, preferring a real browser profile:

```bash
browser-use --headed --profile Default open "<url>"
```

If `browser-use` is missing but `uvx` exists:

```bash
uvx --python 3.11 browser-use --headed --profile Default open "<url>"
```

If both are missing, install browser-use first:

```bash
curl -fsSL https://browser-use.com/cli/install.sh | bash
browser-use doctor
```

3. Tell the user in Chinese:

```text
我已经打开这个亚马逊页面。
如果浏览器里出现登录、验证码、店铺选择或站点选择，请你直接在浏览器里完成。
当页面已经显示你要导出的表格时，回到 Codex 输入：好了，继续。
```

Accept only clear continue phrases such as `done`, `continue`, `done continue`, `好了`, `继续`, or `好了继续`.

4. After the user confirms the page is ready, resolve the helper path from this skill directory and run it. Do not use the developer machine path.

```bash
python3 "$HOME/.codex/skills/amazon-table-to-excel/scripts/export_tables.py" --open-file
```

On Windows PowerShell, use the equivalent installed path:

```powershell
python "$env:USERPROFILE\.codex\skills\amazon-table-to-excel\scripts\export_tables.py" --open-file
```

5. Reply with the output workbook path and table count. Keep the message short.

Example final response for coworkers:

```text
已导出 3 个表格，Excel 文件在这里：
/Users/you/Downloads/amazon-fee-table-20260603-153000.xlsx

我已经帮你打开文件，可以直接检查。
```

## Guardrails

- Never ask for passwords, OTPs, 2FA codes, QR approvals, security questions, or account secrets.
- Let the user complete login and verification directly in the visible browser.
- Export only the current webpage. Do not crawl sidebar links or related articles.
- Do not guess table values. Workbook cells must come from webpage DOM text.
- The helper may auto-scroll and click safe display-only controls such as `show more`, `expand`, `load more`, `展开`, `查看更多`, and `加载更多`.
- Never click destructive or business-changing controls such as submit, save, edit, delete, buy, pay, confirm, or their Chinese equivalents.
- If no tables are found, explain that the current page may not contain DOM tables and ask the user to verify the page.
- If installation is needed, explain only: `我需要先准备导出工具，第一次会多花一点时间。`
- If the browser opens on a login or verification page, pause and wait for the user's clear continue phrase.
- If a command fails, translate the failure into plain language and ask the user to try again only when needed.

## Notes

The helper script writes one workbook to the user's Downloads folder by default. The first sheet is an index; each detected table is exported to its own sheet with merged cells preserved where `rowspan` or `colspan` exists.
