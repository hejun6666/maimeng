---
name: amazon-listing-auto-copywriter
description: Use when creating Amazon US, CA, UK, or DE listing copy from a user's own product basics, especially when Codex should research public competitor listings and produce Amazon-ready copy, Chinese operator references, verification checklists, and compliance notes without paid marketplace APIs.
---

# Amazon Listing Auto Copywriter

## Goal

Turn a user's rough product description into an Amazon-ready copy package for Amazon US, CA, UK, or DE by collecting public competitor listing data first. This skill is for operator review and acceleration: generate strong drafts, surface assumptions, and mark facts that still need verification.

## Hard Rules

- Do not use paid LinkFox, SellerSprite, SIF, ABA, or other paid marketplace APIs.
- Do not ask the user to provide competitor URLs, screenshots, copied bullets, or manual competitor data.
- Always collect public competitor data before writing final copy.
- Do not produce final listing copy unless the research brief contains at least 5 effective competitors.
- Codex is responsible for market understanding. The script is only a crawler, parser, and ranker.
- Use competitor listings to learn structure, keywords, buyer language, customer-facing angles, and candidate opportunities.
- Do not treat competitor facts as confirmed facts for the user's product.
- Output one marketplace-language copy version only: **Amazon Copy - Enhanced Candidate Version**. Do not output a confirmed/conservative fallback unless the user explicitly asks for it.
- The first copy block must contain only content that could be pasted into Amazon fields for the target marketplace. Do not put Chinese, `[待核实]`, tables, footnotes, or explanations inside that copy block.
- After the marketplace-language copy block, output a Chinese copy reference section that translates the title, every bullet, description, and backend search terms one-to-one for operators to read.
- Put verification warnings, competitor insights, and operator notes after the Chinese copy reference section.
- If scraping fails for one route, automatically try alternate model-generated search terms, URL forms, fetcher types, device headers, and parsing strategies.
- Do not solve CAPTCHAs, bypass logins, or run high-volume crawling. Use caching and polite delays.

## Supported Scope

- Marketplaces: Amazon US (`amazon.com`), Amazon CA (`amazon.ca`), Amazon UK (`amazon.co.uk`), and Amazon DE (`amazon.de`).
- Language:
  - US: English with US Amazon wording.
  - CA: English with North American wording.
  - UK: English with light British localisation where natural.
  - DE: German main copy. Add English reference only if the user asks.
- All outputs must include a complete one-to-one Chinese copy reference and Chinese operator review notes.
- Categories: all product categories, with risk-based claim controls.
- Default marketplace: US when the user does not specify a site.
- Competitor target: retain 5 effective competitors.

## Workflow

1. **Structure the user's product basics**
   - Convert free-form input into a product brief:
     - product category
     - marketplace: US, CA, UK, or DE
     - product type
     - core features
     - known specifications
     - materials
     - size / capacity / quantity
     - included accessories
     - target user
     - use scenarios
     - known claims or certifications
     - unknown facts
   - Keep missing facts as unknown. Do not invent them.

2. **Generate model-led research inputs**
   - Codex must generate `researchQueries`, `relevanceTerms`, and `targetCategories` before running the script.
   - The script must not be used as the market-understanding layer. Do not rely on it to discover local buyer search terms from a raw Chinese product name.
   - `researchQueries`: marketplace-local Amazon search terms. Use 5-12 queries covering product type, attribute terms, use cases, synonyms, and buyer language.
   - `relevanceTerms`: short terms used only to filter obvious mismatches and score title/category relevance. Relevance is a guardrail, not the main ranking brain.
   - `targetCategories`: likely BSR subcategories. Matching specific subcategory ranks should be weighted heavily when found.
   - US/CA: use English queries.
   - UK: use English queries with light British localisation, such as `colour`, `organise`, and `school stationery` when natural.
   - DE: use both English and German queries. Example for highlighters: `highlighter pens`, `Textmarker`, `Leuchtmarker`, `Textmarker Set`, `Marker Stifte`, `Textmarker Schule Buero`.

3. **Collect competitor data**
   - Run `scripts/amazon_collect_brief.py` with the product brief JSON, including the model-generated fields above.
   - The script must:
     - search Amazon public pages
     - extract candidate ASINs and product URLs
     - use `researchQueries` when provided; fallback query generation is only a last resort
     - parse `bought in past month` / local equivalent when available
     - parse `Best Sellers Rank` / BSR category rank when available, especially specific subcategory ranks such as `#2 in Baby Playards`
     - visit candidate detail pages
     - extract title, bullets, price, rating, review count, image count, public sales heat, and BSR signals
     - rank competitors primarily by BSR/subcategory rank and public sales heat, then relevance, review signals, listing completeness, and diversity
     - keep 5 effective competitors
   - Prefer competitors with both Amazon front-end bought-past-month signals and strong BSR/subcategory rank signals.
   - Treat specific subcategory rankings as the strongest competitor-selection signal when they match the user's product.
   - If fewer than 5 competitors have monthly-bought and BSR signals, supplement with highly relevant, highly reviewed, high-rated, complete listings.
   - Label which competitors had monthly-bought signals, BSR signals, image count, and listing completeness signals.

4. **Build the copy brief**
   - Summarize:
     - competitor titles
     - competitor BSR / subcategory ranks
     - repeated benefit angles
     - repeated feature angles
     - common specs and accessories
     - likely keywords
     - candidate opportunity claims requiring verification
   - Separate:
     - confirmed product facts from the user
     - competitor-derived candidate facts
     - unsupported risky claims

5. **Draft the copy**
   - Produce exactly these modules:
     1. Product Title
     2. 5 Bullet Points
     3. Product Description
     4. Backend Search Terms
     5. Competitor Insight Summary
     6. Keyword Pool
     7. Verification Checklist
     8. Compliance / Risk Notes
   - Produce one main copy version:
     - **Amazon Copy - Enhanced Candidate Version**: the main operator-facing draft. For US/CA write strong but compliant North American English; for UK write lightly localised British English; for DE write German Amazon listing copy.
   - Do not output **Amazon Copy - Confirmed Version** unless the user explicitly asks for a conservative fallback.
   - Bullets should be conversion-oriented, not official-sounding summaries:
     - Start each bullet with a benefit-led mini headline, such as `Room to Crawl, Play & Explore:`.
     - Target roughly 45-75 words per bullet unless the category requires stricter compliance.
     - Use buyer scenes, pain points, and outcomes before feature support.
     - Blend competitor patterns deeply: keywords, angle structure, repeated buyer language, and scenarios, but do not copy competitor sentences.
   - For enhanced titles, use keyword + scenario + result language, not keyword stuffing alone.
   - Immediately after the marketplace-language copy, provide **Chinese Copy Reference / 中文文案对照** with a complete one-to-one Chinese translation of each field. This section is for operator reading only and is not Amazon copy.
   - Chinese copy reference must translate the marketplace-language copy directly and fully:
     - Translate the title as one title.
     - Translate each bullet under the same number.
     - Translate the full product description.
     - Translate backend search terms as term meanings or a phrase-by-phrase Chinese equivalent.
   - Do not summarize, shorten, explain intent, or add new claims in the Chinese copy reference.
   - Track unconfirmed facts in the Chinese operator review section instead, mapped to exact marketplace-language fields and bullet numbers.

6. **Run checks**
   - Use `scripts/copy_safety_check.py` when candidate copy is available.
   - Check for:
     - overclaiming
     - regulated claims
     - unsupported certifications
     - direct competitor copying
     - excessive keyword stuffing
     - repeated phrases across bullets

## Output Format

Use this structure in the final response. The first section must be a clean marketplace-language copy block for copying into Amazon. Then provide a one-to-one Chinese translation. Put verification notes after that.

```markdown
## Amazon Copy - Enhanced Candidate Version

### Product Title
...

### Bullet Points
1. ...
2. ...
3. ...
4. ...
5. ...

### Product Description
...

### Backend Search Terms
...

## Chinese Copy Reference / 中文文案对照

### 标题
...

### 五点
1. ...
2. ...
3. ...
4. ...
5. ...

### 产品描述
...

### 后台搜索词
...

## 中文运营复核区

### 竞品选择依据

| ASIN | Title | Bought Past Month | Best Sellers Rank | Rating | Reviews | Images | Why Selected |
|---|---|---:|---|---:|---:|---:|---|

### 竞品洞察总结

...

### 关键词池

- Core terms:
- Attribute terms:
- Use-case terms:
- Long-tail terms:

### 待核实清单

| 文案位置 | 需要核实的说法 | 依据/来源 | 风险 | 建议处理 |
|---|---|---|---|---|

### 合规 / 风险说明

...
```

## Copy Rules

- See `references/copy-rules.md` for title, bullet, description, and backend keyword rules.
- See `references/category-risk.md` for risk-tier handling and prohibited claims.
- See `references/scraping-strategy.md` for the free public-data collection strategy.

## Script Usage

Create a product brief JSON with model-generated search inputs and run:

```bash
echo '{"marketplace":"US","product":"highlighter pens","productType":"highlighter pens","researchQueries":["highlighter pens","chisel tip highlighters","assorted highlighters","highlighter set school office","journaling highlighters"],"relevanceTerms":["highlighter","highlighters","chisel tip","marker"],"targetCategories":["Liquid Highlighters"],"features":["assorted colors","chisel tip"],"audience":"students and office users","scenarios":["school","office","journaling"]}' | python scripts/amazon_collect_brief.py
```

The script writes a JSON brief to stdout. Use that brief as the factual basis for the copy package.

Run local validation:

```bash
python scripts/self_test.py
```
