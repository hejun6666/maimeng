---
name: amazon-listing-auto-copywriter
description: Use when creating Amazon US or CA listing copy from a user's own product basics, especially when the user wants Codex to automatically research public competitor listings, extract Amazon front-end signals, and produce titles, bullets, descriptions, search terms, verification checklists, and compliance notes without paid marketplace APIs.
---

# Amazon Listing Auto Copywriter

## Goal

Turn a user's rough product description into an Amazon-ready copy package for Amazon US or Amazon CA by automatically collecting public competitor listing data first. This skill is for operator review and acceleration: generate strong drafts, surface assumptions, and mark facts that still need verification.

## Hard Rules

- Do not use paid LinkFox, SellerSprite, SIF, ABA, or other paid marketplace APIs.
- Do not ask the user to provide competitor URLs, screenshots, copied bullets, or manual competitor data.
- Always collect public competitor data before writing final copy.
- Do not produce final listing copy unless the research brief contains at least 5 effective competitors.
- Use competitor listings to learn structure, keywords, customer-facing angles, and candidate opportunities.
- Do not treat competitor facts as confirmed facts for the user's product.
- Output copy-ready English first. The English copy block must contain only content that could be pasted into Amazon fields.
- Output one English version only: **Amazon Copy - Enhanced Candidate Version**. Do not output a confirmed/conservative fallback unless the user explicitly asks for it.
- After the English copy block, output a Chinese copy reference section that translates the English title, every bullet, description, and backend search terms one-to-one for operators to read.
- Put verification warnings, competitor insights, and operator notes after the Chinese copy reference section.
- If scraping fails for one route, automatically try alternate search terms, URL forms, fetcher types, device headers, and parsing strategies.
- Do not solve CAPTCHAs, bypass logins, or run high-volume crawling. Use caching and polite delays.

## Supported Scope

- Marketplaces: Amazon US (`amazon.com`) and Amazon CA (`amazon.ca`).
- Language: clean English listing copy first, then Chinese copy reference, then Chinese explanation and review notes.
- Categories: all product categories, with risk-based claim controls.
- Default marketplace: US when the user does not specify a site.
- Competitor target: retain 5 effective competitors.

## Workflow

1. **Structure the user's product basics**
   - Convert free-form input into a product brief:
     - product category
     - marketplace: US or CA
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

2. **Generate research queries**
   - Build 3-8 Amazon search queries from the product brief.
   - Include core product terms, use-case terms, attribute terms, and likely buyer language.
   - For US and CA, use English queries.

3. **Collect competitor data**
   - Run `scripts/amazon_collect_brief.py` with the product brief JSON.
   - The script must:
     - search Amazon public pages
     - extract candidate ASINs and product URLs
    - parse `bought in past month` when available
    - parse `Best Sellers Rank` / BSR category rank when available, especially specific subcategory ranks such as `#2 in Baby Playards`
    - visit candidate detail pages
    - extract title, bullets, price, rating, review count, image count, public sales heat, and BSR signals
    - rank competitors by relevance, public sales heat, BSR/subcategory rank, review signals, listing completeness, and diversity
    - keep 5 effective competitors
   - Prefer competitors with both Amazon front-end `bought in past month` and strong BSR/subcategory rank signals.
   - Treat specific subcategory rankings as especially valuable when they match the user's product, because they indicate category-level competitiveness.
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
   - Produce one English copy version:
     - **Amazon Copy - Enhanced Candidate Version**: the main operator-facing draft. Write in a strong but compliant US-native Amazon listing style using competitor-derived high-frequency opportunities; directly copyable only after the Chinese verification checklist confirms the mapped claims.
   - Do not output **Amazon Copy - Confirmed Version** unless the user explicitly asks for a conservative fallback.
   - Bullets should be conversion-oriented, not official-sounding summaries:
     - Start each bullet with a benefit-led mini headline, such as `Room to Crawl, Play & Explore:`.
     - Target roughly 45-75 words per bullet unless the category requires stricter compliance.
     - Use buyer scenes, pain points, and outcomes before feature support.
     - Blend competitor patterns deeply: keywords, angle structure, repeated buyer language, and scenarios, but do not copy competitor sentences.
   - For enhanced titles, use keyword + scenario + result language, not keyword stuffing alone.
   - Do not insert `[待核实]`, Chinese comments, footnotes, or explanatory brackets into any English copy field.
   - Immediately after the English copy, provide **中文文案对照** with a complete one-to-one Chinese translation of each English field. This section is for operator reading only and is not Amazon copy.
   - Chinese copy reference must translate the English copy directly and fully:
     - Translate the title as one title.
     - Translate each bullet under the same number.
     - Translate the full product description.
     - Translate backend search terms as term meanings or a phrase-by-phrase Chinese equivalent.
   - Do not summarize, shorten, explain intent, or add new claims in the Chinese copy reference.
   - Track unconfirmed facts in the Chinese operator review section instead, mapped to exact English fields and bullet numbers.

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

Use this structure in the final response. The first section must be a clean English copy block for copying into Amazon. Then provide a one-to-one Chinese translation. Put verification notes after that.

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

## 中文文案对照

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

### 后台搜索词含义
...

## 中文运营复核区
### 抓取依据

| ASIN | Title | Bought Past Month | Best Sellers Rank | Rating | Reviews | Images | Why Selected |
|---|---|---:|---|---:|---:|---:|---|

### 竞品洞察

...

### 关键词池

- Core terms:
- Attribute terms:
- Use-case terms:
- Long-tail terms:

### 待核实清单
| 对应位置 | 待核实内容 | 为什么要核实 | 来源 | 建议动作 |
|---|---|---|---|---|

### 合规 / 风险备注

...
```

## Copy Rules

- See `references/copy-rules.md` for title, bullet, description, and backend keyword rules.
- See `references/category-risk.md` for risk-tier handling and prohibited claims.
- See `references/scraping-strategy.md` for the free public-data collection strategy.

## Script Usage

Create a product brief JSON and run:

```bash
echo '{"marketplace":"US","product":"foldable baby playpen","features":["50 x 50 inch","foldable","mat included","pull rings"],"audience":"babies and toddlers","scenarios":["indoor","outdoor"]}' | python scripts/amazon_collect_brief.py
```

The script writes a JSON brief to stdout. Use that brief as the factual basis for the copy package.

Run local validation:

```bash
python scripts/self_test.py
```
