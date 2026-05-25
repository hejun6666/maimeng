---
name: amazon-ai-shopping-listing-copywriter
description: Use when creating Amazon US, CA, UK, or DE listing copy that should stay conversion-focused while improving AI shopping assistant, Rufus, Alexa for Shopping, AI Shopping Guides, Help Me Decide, and GEO-style understanding, matching, and citation readiness without paid marketplace APIs.
---

# Amazon AI Shopping Listing Copywriter

## Goal

Turn a user's rough product description into Amazon-ready listing copy for Amazon US, CA, UK, or DE, after collecting public competitor listing data, while adding an **AI Shopping Readiness** layer. The output should still read like strong Amazon copy for humans, but it should also be easier for Amazon AI shopping systems to understand, match to buyer questions, and quote as a product explanation.

This skill is for operator review and acceleration. It cannot guarantee ranking, recommendation, indexing, or inclusion by Amazon AI systems.

## Hard Rules

- Do not use paid LinkFox, SellerSprite, SIF, ABA, or other paid marketplace APIs.
- Do not ask the user to provide competitor URLs, screenshots, copied bullets, or manual competitor data.
- Always collect public competitor data before writing final copy.
- Do not produce final listing copy unless the research brief contains at least 5 effective competitors.
- Codex is responsible for market understanding. The script is only a crawler, parser, and ranker.
- Use competitor listings to learn structure, keywords, buyer language, customer-facing angles, and candidate opportunities.
- Do not treat competitor facts as confirmed facts for the user's product.
- Output one marketplace-language copy version only: **Amazon Copy - AI Shopping Enhanced Candidate Version**.
- The first copy block must contain only content that could be pasted into Amazon fields for the target marketplace. Do not put Chinese, `[needs verification]`, `[待核实]`, tables, footnotes, AI/GEO explanations, or operator notes inside that copy block.
- Never write claims such as `AI recommended`, `Rufus optimized`, `Alexa recommended`, `GEO guaranteed`, `guaranteed ranking`, or similar inside Amazon copy.
- After the marketplace-language copy block, output a complete one-to-one Chinese copy reference for operators to read.
- Put verification warnings, competitor insights, AI Shopping Readiness notes, and operator checks after the Chinese copy reference section.
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

## What AI Shopping Readiness Means

Amazon's AI shopping surfaces, including Rufus/Alexa for Shopping, AI Shopping Guides, and Help Me Decide-style experiences, can use product details, reviews, Q&A, catalog attributes, and buyer context to answer questions and compare products. This skill improves readiness by making listing copy:

- entity-clear: product type, audience, use cases, attributes, included items, and limits are explicit
- question-answerable: common buyer questions are naturally answered in title, bullets, and description
- semantically rich: synonyms, scenario language, and decision terms are covered without keyword stuffing
- citation-friendly: sentences are specific enough for an AI answer to summarize or quote
- compliant: unverified, regulated, medical, safety, or absolute claims stay out of copy unless confirmed

Do not call this a guarantee of AI recommendation. Call it **AI Shopping Readiness** or **Rufus/GEO-friendly structure** in operator notes only.

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
   - `relevanceTerms`: short terms used to reject obvious mismatches before final ranking and to score title/category relevance. Relevance is a guardrail, not the main ranking brain.
   - `targetCategories`: likely BSR subcategories. Matching specific subcategory ranks should be weighted heavily when found.
   - US/CA: use English queries.
   - UK: use English queries with light British localisation, such as `colour`, `organise`, and `school stationery` when natural.
   - DE: use both English and German queries. Example for highlighters: `highlighter pens`, `Textmarker`, `Leuchtmarker`, `Textmarker Set`, `Marker Stifte`, `Textmarker Schule Buero`.

3. **Generate AI Shopping inputs**
   - Before writing copy, Codex must generate:
     - `aiShoppingQuestions`: 8-15 natural buyer questions an Amazon AI assistant might answer.
     - `recommendationTriggers`: 10-20 phrases that connect the product to buyer intent, scenarios, audiences, and decision moments.
     - `attributeEntityMap`: product entities and attributes that should be explicit, such as product type, audience, material, size, compatibility, quantity, power source, included items, care, and limitations.
     - `buyerDecisionMatrix`: the main purchase criteria buyers compare in this category.
   - These inputs guide copy. They are not pasted as a visible FAQ inside Amazon copy unless that format is natural for the category.
   - If a fact is unknown, mark it for operator verification instead of inventing it.

4. **Collect competitor data**
   - Run `scripts/amazon_collect_brief.py` with the product brief JSON, including the model-generated fields above.
   - The script must:
     - search Amazon public pages
     - extract candidate ASINs and product URLs
     - use `researchQueries` when provided; fallback query generation is only a last resort
     - parse `bought in past month` / local equivalent when available
     - parse `Best Sellers Rank` / BSR category rank when available, especially specific subcategory ranks such as `#2 in Baby Playards`
     - visit candidate detail pages
     - extract title, bullets, price, rating, review count, image count, public sales heat, and BSR signals
     - reject candidates whose title and BSR categories do not match `relevanceTerms` or `targetCategories`, even if they have strong BSR or bought-past-month signals
     - rank competitors primarily by BSR/subcategory rank and public sales heat, then relevance, review signals, listing completeness, and diversity
     - keep 5 effective competitors
   - Prefer competitors with both Amazon front-end bought-past-month signals and strong BSR/subcategory rank signals.
   - Treat specific subcategory rankings as the strongest competitor-selection signal when they match the user's product.
   - If fewer than 5 competitors have monthly-bought and BSR signals, supplement with highly relevant, highly reviewed, high-rated, complete listings.
   - Label which competitors had monthly-bought signals, BSR signals, image count, and listing completeness signals.

5. **Build the copy brief**
   - Summarize:
     - competitor titles
     - competitor BSR / subcategory ranks
     - repeated benefit angles
     - repeated feature angles
     - common specs and accessories
     - likely keywords
     - buyer questions competitors answer directly or indirectly
     - AI recommendation trigger phrases
     - candidate opportunity claims requiring verification
   - Separate:
     - confirmed product facts from the user
     - competitor-derived candidate facts
     - unsupported risky claims

6. **Draft the copy**
   - Produce exactly these marketplace-language modules first:
     1. Product Title
     2. 5 Bullet Points
     3. Product Description
     4. Backend Search Terms
   - Produce one main copy version:
     - **Amazon Copy - AI Shopping Enhanced Candidate Version**: the main operator-facing draft. For US/CA write strong but compliant North American English; for UK write lightly localised British English; for DE write German Amazon listing copy.
   - Do not output **Amazon Copy - Confirmed Version** unless the user explicitly asks for a conservative fallback.
   - Bullets should be conversion-oriented, not official-sounding summaries:
     - Start each bullet with a benefit-led mini headline, such as `Room to Crawl, Play & Explore:`.
     - Target roughly 45-75 words per bullet unless the category requires stricter compliance.
     - Use buyer scenes, pain points, and outcomes before feature support.
     - Blend competitor patterns deeply: keywords, angle structure, repeated buyer language, and scenarios, but do not copy competitor sentences.
   - Assign the 5 bullets these AI-readable roles unless the category needs a different order:
     1. core buyer promise and who the product is for
     2. key product attributes, build, material, compatibility, or safety-related facts
     3. use experience, setup, maintenance, portability, storage, or daily convenience
     4. scenarios, audience segments, giftability, or comparison context
     5. included items, value, care, support, limitations, or differentiation
   - For enhanced titles, use keyword + audience/scenario + key attribute/result language, not keyword stuffing alone.
   - The product description should read like a short buying-guide answer: who it is for, what problem it solves, why the attributes matter, and what the operator still must verify if facts are unknown.
   - Immediately after the marketplace-language copy, provide **Chinese Copy Reference / 中文文案对照** with a complete one-to-one Chinese translation of each field. This section is for operator reading only and is not Amazon copy.
   - Chinese copy reference must translate the marketplace-language copy directly and fully:
     - Translate the title as one title.
     - Translate each bullet under the same number.
     - Translate the full product description.
     - Translate backend search terms as term meanings or a phrase-by-phrase Chinese equivalent.
   - Do not summarize, shorten, explain intent, or add new claims in the Chinese copy reference.
   - Track unconfirmed facts in the Chinese operator review section instead, mapped to exact marketplace-language fields and bullet numbers.

7. **Run checks**
   - Use `scripts/copy_safety_check.py` when candidate copy is available.
   - Use `scripts/ai_recommendation_check.py` when candidate copy and AI Shopping inputs are available.
   - Check for:
     - overclaiming
     - regulated claims
     - unsupported certifications
     - direct competitor copying
     - excessive keyword stuffing
     - repeated phrases across bullets
     - unaddressed buyer questions
     - missing product type, audience, attribute, scenario, or limitation signals
     - prohibited AI/GEO promise language

## Output Format

Use this structure in the final response. The first section must be a clean marketplace-language copy block for copying into Amazon. Then provide a one-to-one Chinese translation. Put verification notes and AI Shopping Readiness notes after that.

```markdown
## Amazon Copy - AI Shopping Enhanced Candidate Version

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

### AI 推荐理解度 / Rufus-GEO 友好检查

| 买家可能问法 | 文案中是否回答 | 对应位置 | 是否需运营核实 |
|---|---|---|---|

### AI 推荐触发词建议

- 场景型:
- 人群型:
- 问题型:
- 属性型:
- 对比型:

### 待核实清单

| 文案位置 | 需要核实的说法 | 依据/来源 | 风险 | 建议处理 |
|---|---|---|---|---|

### 合规 / 风险说明

...
```

## Copy Rules

- See `references/copy-rules.md` for title, bullet, description, and backend keyword rules.
- See `references/ai-recommendation-rules.md` for AI Shopping / Rufus-GEO readiness rules.
- See `references/category-risk.md` for risk-tier handling and prohibited claims.
- See `references/scraping-strategy.md` for the free public-data collection strategy.

## Script Usage

Create a product brief JSON with model-generated search inputs and AI Shopping inputs, then run:

```bash
echo '{"marketplace":"US","product":"highlighter pens","productType":"highlighter pens","researchQueries":["highlighter pens","chisel tip highlighters","assorted highlighters","highlighter set school office","journaling highlighters"],"relevanceTerms":["highlighter","highlighters","chisel tip","marker"],"targetCategories":["Liquid Highlighters"],"aiShoppingQuestions":["What highlighters are good for school and office notes?","Do these highlighters work for journaling?","Are they easy to use for color coding?"],"recommendationTriggers":["highlighter pens for students","office color coding","journaling highlighters","chisel tip markers"],"features":["assorted colors","chisel tip"],"audience":"students and office users","scenarios":["school","office","journaling"]}' | python scripts/amazon_collect_brief.py
```

The script writes a JSON brief to stdout. Use that brief as the factual basis for the copy package.

Run copy checks:

```bash
python scripts/copy_safety_check.py '{"copy":"...","competitorTexts":["..."]}'
python scripts/ai_recommendation_check.py '{"title":"...","bullets":["..."],"description":"...","backendSearchTerms":"...","aiShoppingQuestions":["..."],"recommendationTriggers":["..."],"attributeEntityMap":{"audience":"students"}}'
```

Run local validation:

```bash
python scripts/self_test.py
```
