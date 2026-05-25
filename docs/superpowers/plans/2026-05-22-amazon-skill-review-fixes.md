# Amazon Skill Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the review gaps in `amazon-listing-auto-copywriter` so marketplace routing, competitor relevance guardrails, UK/DE parsing, and packaging rules match the agreed skill design.

**Architecture:** Keep Codex/model as the market-understanding layer and keep `amazon_collect_brief.py` as crawler/parser/ranker. Add small focused helper functions for marketplace normalization, localized parsing, relevance guardrails, and fetch headers rather than introducing a larger framework. Remove generated Word/PDF artifacts from git; the repo should contain source docs and skill code only.

**Tech Stack:** Python standard library, current skill script structure, `scripts/self_test.py`, Markdown documentation, git.

---

## File Structure

- Modify: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\skills\amazon-listing-auto-copywriter\scripts\amazon_collect_brief.py`
  - Responsible for marketplace normalization, public Amazon fetching, parsing, candidate ranking, and JSON output.
- Modify: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\skills\amazon-listing-auto-copywriter\scripts\self_test.py`
  - Responsible for fast local regression tests covering the script behavior.
- Modify: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\skills\amazon-listing-auto-copywriter\SKILL.md`
  - Responsible for the agent-facing workflow and output constraints.
- Modify: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\skills\amazon-listing-auto-copywriter\references\scraping-strategy.md`
  - Responsible for detailed research/scraping/ranking rules.
- Modify: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\docs\amazon-listing-skill-usage.md`
  - Responsible for operator-facing usage instructions.
- Modify: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\README.md`
  - Responsible for repo overview and install links.
- Modify: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\.gitignore`
  - Responsible for excluding generated local manuals and cache files.
- Remove from git tracking:
  - `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\docs\Amazon Listing 自动文案 Skill 使用手册.docx`
  - `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\docs\Amazon Listing 自动文案 Skill 使用手册.pdf`
- Optional generated deliverable outside git:
  - `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\Amazon Listing 自动文案 Skill 使用手册.docx`

---

### Task 1: Add Regression Tests For Review Gaps

**Files:**
- Modify: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\skills\amazon-listing-auto-copywriter\scripts\self_test.py`

- [ ] **Step 1: Write failing tests for Chinese marketplace names**

Add this test below `test_marketplace_normalization()`:

```python
def test_chinese_marketplace_normalization():
    assert normalize_marketplace("美国站")["domain"] == "amazon.com"
    assert normalize_marketplace("加拿大站")["domain"] == "amazon.ca"
    assert normalize_marketplace("英国站")["domain"] == "amazon.co.uk"
    assert normalize_marketplace("德国站")["domain"] == "amazon.de"
    assert normalize_marketplace("Amazon 德国")["domain"] == "amazon.de"
```

Add the call in `main()`:

```python
    test_chinese_marketplace_normalization()
```

- [ ] **Step 2: Write failing tests for relevance guardrail**

Add this test below `test_bsr_and_bought_drive_competitor_selection()`:

```python
def test_relevance_guardrail_blocks_wrong_category_winner():
    irrelevant_bestseller = {
        "asin": "B0DOGTOY001",
        "title": "Dog Chew Toy for Aggressive Chewers",
        "query": "highlighter pens",
        "boughtInPastMonth": 20000,
        "hasBoughtSignal": True,
        "bestSellerRanks": [{"rank": 1, "category": "Pet Supplies"}],
        "rating": 4.8,
        "reviews": 50000,
        "bulletCount": 5,
        "price": "9.99",
        "imageCount": 8,
    }
    relevant_listing = {
        "asin": "B0HIGHLIGHT",
        "title": "Chisel Tip Highlighter Pens Assorted Colors",
        "query": "highlighter pens",
        "boughtInPastMonth": None,
        "hasBoughtSignal": False,
        "bestSellerRanks": [],
        "rating": 4.5,
        "reviews": 500,
        "bulletCount": 5,
        "price": "6.99",
        "imageCount": 8,
    }
    ranked = rank_candidates(
        [irrelevant_bestseller, relevant_listing],
        relevance_terms=["highlighter", "chisel tip"],
        target_categories=["Liquid Highlighters"],
        desired_count=2,
    )
    assert [item["asin"] for item in ranked] == ["B0HIGHLIGHT"]
```

Add the call in `main()`:

```python
    test_relevance_guardrail_blocks_wrong_category_winner()
```

- [ ] **Step 3: Write failing tests for German parsing**

Add this test below `test_bsr_rank_parsing()`:

```python
def test_german_listing_signal_parsing():
    html = """
    <span id="productTitle">Textmarker Set Pastellfarben</span>
    <span>4,6 von 5 Sternen</span>
    <span id="acrCustomerReviewText">1.234 Sternebewertungen</span>
    <span class="a-price-whole">8</span><span class="a-price-fraction">99</span>
    <span>1.000+ Mal im letzten Monat gekauft</span>
    <tr><th>Amazon Bestseller-Rang</th><td>Nr. 1 in Textmarker</td></tr>
    """
    listing = parse_listing_html(html, "B0TEXTMARK", "https://www.amazon.de/dp/B0TEXTMARK")
    assert listing["rating"] == 4.6
    assert listing["reviews"] == 1234
    assert listing["price"] == "8.99"
    assert listing["boughtInPastMonth"] == 1000
    assert listing["bestSellerRanks"] == [{"rank": 1, "category": "Textmarker"}]
```

Add the call in `main()`:

```python
    test_german_listing_signal_parsing()
```

- [ ] **Step 4: Write failing test for Scrapling language header forwarding**

Add `Request` import support is not needed. Add this test near the other tests:

```python
def test_fetch_url_passes_accept_language_to_scrapling(monkeypatch=None):
    # Lightweight monkeypatch without pytest: replace the module-level try_scrapling
    # and verify fetch_url passes the marketplace language through that path.
    import amazon_collect_brief as module

    calls = []
    original = module.try_scrapling

    def fake_try_scrapling(url, mode="fetcher", accept_language="en-US,en;q=0.9"):
        calls.append((url, mode, accept_language))
        return module.FetchResult(url=url, html="<html>ok</html>", fetcher="fake")

    try:
        module.try_scrapling = fake_try_scrapling
        result = module.fetch_url(
            "https://www.amazon.de/s?k=Textmarker",
            accept_language="de-DE,de;q=0.9,en;q=0.7",
        )
    finally:
        module.try_scrapling = original

    assert result.fetcher == "fake"
    assert calls[0][2] == "de-DE,de;q=0.9,en;q=0.7"
```

Add the call in `main()`:

```python
    test_fetch_url_passes_accept_language_to_scrapling()
```

- [ ] **Step 5: Run tests and verify they fail**

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'; python 'skills\amazon-listing-auto-copywriter\scripts\self_test.py'
```

Expected before implementation:

```text
AssertionError
```

At least one of the new tests should fail because current code maps Chinese marketplace names to US, allows irrelevant high-BSR items to win, and does not pass `accept_language` into `try_scrapling`.

---

### Task 2: Fix Marketplace Normalization

**Files:**
- Modify: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\skills\amazon-listing-auto-copywriter\scripts\amazon_collect_brief.py`
- Test: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\skills\amazon-listing-auto-copywriter\scripts\self_test.py`

- [ ] **Step 1: Replace `normalize_marketplace` with explicit alias matching**

Replace the existing `normalize_marketplace()` function with:

```python
def normalize_marketplace(value: str | None) -> dict[str, str]:
    if not value:
        return MARKETPLACES["US"]

    raw = str(value).strip()
    upper = raw.upper()
    if upper in MARKETPLACES:
        return MARKETPLACES[upper]

    lower = raw.lower()
    aliases = {
        "US": ["amazon.com", "us", "usa", "united states", "america", "美国", "美国站", "美站"],
        "CA": ["amazon.ca", "ca", "canada", "加拿大", "加拿大站", "加站"],
        "UK": ["amazon.co.uk", "uk", "gb", "united kingdom", "britain", "england", "英国", "英国站", "英站"],
        "DE": ["amazon.de", "de", "germany", "deutschland", "德国", "德国站", "德站"],
    }
    for code, values in aliases.items():
        if any(alias in lower or alias in raw for alias in values):
            return MARKETPLACES[code]
    return MARKETPLACES["US"]
```

- [ ] **Step 2: Run marketplace tests**

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'; python 'skills\amazon-listing-auto-copywriter\scripts\self_test.py'
```

Expected after this task:

```text
Chinese marketplace normalization passes.
Other new tests may still fail.
```

- [ ] **Step 3: Commit**

Run:

```powershell
git add skills/amazon-listing-auto-copywriter/scripts/amazon_collect_brief.py skills/amazon-listing-auto-copywriter/scripts/self_test.py
git commit -m "fix: normalize localized Amazon marketplaces"
```

---

### Task 3: Make Relevance A Real Guardrail

**Files:**
- Modify: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\skills\amazon-listing-auto-copywriter\scripts\amazon_collect_brief.py`
- Test: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\skills\amazon-listing-auto-copywriter\scripts\self_test.py`

- [ ] **Step 1: Add category relevance helper**

Add this function below `score_relevance()`:

```python
def score_category_relevance(
    ranks: list[dict[str, Any]],
    relevance_terms: list[str],
    target_categories: list[str] | None = None,
) -> float:
    if not ranks:
        return 0.0
    target_categories = target_categories or []
    categories = " ".join(str(item.get("category", "")) for item in ranks).lower()
    category_words = tokenize_for_match(categories)
    targets = [target.lower() for target in target_categories]
    if any(target and target in categories for target in targets):
        return 1.0
    if not relevance_terms:
        return 0.0
    matches = 0
    for term in [term.lower() for term in relevance_terms]:
        term_words = set(re.findall(r"[a-zA-Z0-9]+", term))
        if term in categories or (term_words and term_words <= category_words):
            matches += 1
    return matches / max(len(relevance_terms), 1)
```

- [ ] **Step 2: Add candidate guardrail helper**

Add this function below `score_category_relevance()`:

```python
def passes_relevance_guardrail(
    item: dict[str, Any],
    relevance_terms: list[str],
    target_categories: list[str] | None = None,
) -> bool:
    if not relevance_terms and not target_categories:
        return True
    title_relevance = score_relevance(str(item.get("title", "")), relevance_terms)
    category_relevance = score_category_relevance(
        item.get("bestSellerRanks", []),
        relevance_terms,
        target_categories,
    )
    query_relevance = score_relevance(str(item.get("query", "")), relevance_terms)
    item["guardrailRelevanceScore"] = round(max(title_relevance, category_relevance, query_relevance), 4)
    return title_relevance > 0 or category_relevance > 0
```

Important: do not let `query_relevance` alone pass the guardrail. Query text only explains where the candidate came from; title or BSR category must still prove the candidate itself is relevant.

- [ ] **Step 3: Apply guardrail inside `rank_candidates`**

In `rank_candidates()`, insert this at the start of the item loop:

```python
        if not passes_relevance_guardrail(item, relevance_terms, target_categories):
            continue
```

The top of the loop should become:

```python
    for item in candidates:
        if not passes_relevance_guardrail(item, relevance_terms, target_categories):
            continue
        relevance = score_relevance(item.get("title", ""), relevance_terms)
```

- [ ] **Step 4: Run relevance tests**

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'; python 'skills\amazon-listing-auto-copywriter\scripts\self_test.py'
```

Expected after this task:

```text
self_test: OK
```

If German parsing or Scrapling tests still fail because those tasks are not implemented yet, verify this specific behavior manually:

```powershell
@'
import sys
sys.path.insert(0, r'skills\amazon-listing-auto-copywriter\scripts')
from amazon_collect_brief import rank_candidates
items = [
    {'asin':'BAD','title':'Dog Chew Toy for Aggressive Chewers','query':'highlighter pens','boughtInPastMonth':20000,'hasBoughtSignal':True,'bestSellerRanks':[{'rank':1,'category':'Pet Supplies'}],'rating':4.8,'reviews':50000,'bulletCount':5,'price':'9.99','imageCount':8},
    {'asin':'GOOD','title':'Chisel Tip Highlighter Pens Assorted Colors','query':'highlighter pens','boughtInPastMonth':None,'hasBoughtSignal':False,'bestSellerRanks':[],'rating':4.5,'reviews':500,'bulletCount':5,'price':'6.99','imageCount':8},
]
print([x['asin'] for x in rank_candidates(items, ['highlighter','chisel tip'], ['Liquid Highlighters'], 2)])
'@ | python -
```

Expected:

```text
['GOOD']
```

- [ ] **Step 5: Commit**

Run:

```powershell
git add skills/amazon-listing-auto-copywriter/scripts/amazon_collect_brief.py skills/amazon-listing-auto-copywriter/scripts/self_test.py
git commit -m "fix: enforce competitor relevance guardrail"
```

---

### Task 4: Improve UK/DE Public Signal Parsing

**Files:**
- Modify: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\skills\amazon-listing-auto-copywriter\scripts\amazon_collect_brief.py`
- Test: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\skills\amazon-listing-auto-copywriter\scripts\self_test.py`

- [ ] **Step 1: Add localized integer parsing helper**

Add below `parse_count_number()`:

```python
def parse_int_number(value: str) -> int:
    return int(parse_count_number(value))
```

- [ ] **Step 2: Replace `extract_rating` with English and German support**

Replace `extract_rating()` with:

```python
def extract_rating(text: str | None) -> float | None:
    if not text:
        return None
    cleaned = clean_text(text)
    patterns = [
        r"(\d+(?:\.\d+)?)\s+out\s+of\s+5\s+stars",
        r"(\d+(?:,\d+)?)\s+von\s+5\s+Sternen",
    ]
    for pattern in patterns:
        match = re.search(pattern, cleaned, re.I)
        if match:
            return float(match.group(1).replace(",", "."))
    return None
```

- [ ] **Step 3: Replace `extract_review_count` with English and German support**

Replace `extract_review_count()` with:

```python
def extract_review_count(text: str | None) -> int | None:
    if not text:
        return None
    text = clean_text(text)
    patterns = [
        r'id="acrCustomerReviewText"[^>]*>\s*([\d,.]+)',
        r"([\d,.]+)\s+(?:ratings|reviews)",
        r"([\d,.]+)\s+(?:Sternebewertungen|Bewertungen|Rezensionen)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return parse_int_number(match.group(1))
    return None
```

- [ ] **Step 4: Replace `money_from_html` with comma-aware parsing**

Replace `money_from_html()` with:

```python
def money_from_html(html: str) -> str:
    whole = re.search(r'class="a-price-whole">\s*([\d,.]+)', html)
    frac = re.search(r'class="a-price-fraction">\s*(\d{2})', html)
    if whole:
        whole_value = whole.group(1).replace(".", "").replace(",", "")
        cents = frac.group(1) if frac else "00"
        return f"{whole_value}.{cents}"
    offscreen = re.search(r'class="a-offscreen">\s*([^<]+)', html)
    if not offscreen:
        return ""
    raw = clean_text(offscreen.group(1))
    amount = re.search(r"([\d,.]+)", raw)
    if not amount:
        return raw
    return f"{parse_count_number(amount.group(1)):.2f}"
```

- [ ] **Step 5: Run parsing tests**

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'; python 'skills\amazon-listing-auto-copywriter\scripts\self_test.py'
```

Expected:

```text
self_test: OK
```

- [ ] **Step 6: Commit**

Run:

```powershell
git add skills/amazon-listing-auto-copywriter/scripts/amazon_collect_brief.py skills/amazon-listing-auto-copywriter/scripts/self_test.py
git commit -m "fix: parse localized Amazon listing signals"
```

---

### Task 5: Forward Marketplace Language To Scrapling Fetchers

**Files:**
- Modify: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\skills\amazon-listing-auto-copywriter\scripts\amazon_collect_brief.py`
- Test: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\skills\amazon-listing-auto-copywriter\scripts\self_test.py`

- [ ] **Step 1: Update `try_scrapling` signature and header usage**

Replace the function definition and fetch calls in `try_scrapling()` with this implementation:

```python
def try_scrapling(
    url: str,
    mode: str = "fetcher",
    accept_language: str = "en-US,en;q=0.9",
) -> FetchResult | None:
    try:
        from scrapling.fetchers import DynamicFetcher, Fetcher, StealthyFetcher  # type: ignore
    except Exception:
        return None

    headers = {
        "Accept-Language": accept_language,
        "User-Agent": random.choice(USER_AGENTS),
    }

    try:
        try:
            if mode == "stealth":
                page = StealthyFetcher.fetch(url, headless=True, timeout=30000, headers=headers)
            elif mode == "dynamic":
                page = DynamicFetcher.fetch(url, headless=True, timeout=30000, headers=headers)
            else:
                page = Fetcher.get(url, timeout=30, headers=headers)
        except TypeError:
            if mode == "stealth":
                page = StealthyFetcher.fetch(url, headless=True, timeout=30000)
            elif mode == "dynamic":
                page = DynamicFetcher.fetch(url, headless=True, timeout=30000)
            else:
                page = Fetcher.get(url, timeout=30)

        body = getattr(page, "body", b"")
        if isinstance(body, bytes):
            html = body.decode(getattr(page, "encoding", None) or "utf-8", errors="ignore")
        else:
            html = str(page)
        status = getattr(page, "status", None)
        if html:
            return FetchResult(url=url, html=html, fetcher=f"scrapling:{mode}", status=status)
    except Exception as exc:
        return FetchResult(url=url, html="", fetcher=f"scrapling:{mode}", error=str(exc))
    return None
```

- [ ] **Step 2: Update `fetch_url` to pass `accept_language` into `try_scrapling`**

Replace:

```python
        result = try_scrapling(url, mode)
```

With:

```python
        result = try_scrapling(url, mode, accept_language=accept_language)
```

- [ ] **Step 3: Run fetch header test**

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'; python 'skills\amazon-listing-auto-copywriter\scripts\self_test.py'
```

Expected:

```text
self_test: OK
```

- [ ] **Step 4: Commit**

Run:

```powershell
git add skills/amazon-listing-auto-copywriter/scripts/amazon_collect_brief.py skills/amazon-listing-auto-copywriter/scripts/self_test.py
git commit -m "fix: pass marketplace language to Amazon fetchers"
```

---

### Task 6: Remove Generated Manuals From Git And Update Packaging Rules

**Files:**
- Modify: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\.gitignore`
- Modify: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\README.md`
- Modify: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\docs\amazon-listing-skill-usage.md`
- Remove from git tracking:
  - `docs/Amazon Listing 自动文案 Skill 使用手册.docx`
  - `docs/Amazon Listing 自动文案 Skill 使用手册.pdf`

- [ ] **Step 1: Update `.gitignore`**

Add these lines:

```gitignore
# Generated local operator manuals; keep source docs in git instead.
docs/*.docx
docs/*.pdf
!docs/*.md
```

- [ ] **Step 2: Update README to remove Word/PDF links**

Replace the `## 使用文档` section in `README.md` with:

```markdown
## 使用文档

- [Amazon Listing 自动文案 Skill 使用说明](docs/amazon-listing-skill-usage.md)

如需 Word 版手册，由 Codex 单独生成并发送，不纳入 git。
```

- [ ] **Step 3: Add source-doc note to usage manual**

Add this after the first paragraph in `docs/amazon-listing-skill-usage.md`:

```markdown
> 维护说明：这个 Markdown 是 git 中的手册源文件。后续如需 Word 版，只单独生成给使用者，不提交到 git；不再生成 PDF。
```

- [ ] **Step 4: Remove generated binary manuals from git only**

Run:

```powershell
git rm --cached "docs/Amazon Listing 自动文案 Skill 使用手册.docx" "docs/Amazon Listing 自动文案 Skill 使用手册.pdf"
```

Expected:

```text
rm 'docs/Amazon Listing 自动文案 Skill 使用手册.docx'
rm 'docs/Amazon Listing 自动文案 Skill 使用手册.pdf'
```

The local files may remain on disk, but `git status --short` should show them as deleted from git tracking and ignored afterwards.

- [ ] **Step 5: Commit**

Run:

```powershell
git add .gitignore README.md docs/amazon-listing-skill-usage.md
git commit -m "chore: keep generated manuals out of git"
```

---

### Task 7: Update Skill Docs With The Fixed Guardrail Semantics

**Files:**
- Modify: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\skills\amazon-listing-auto-copywriter\SKILL.md`
- Modify: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo\skills\amazon-listing-auto-copywriter\references\scraping-strategy.md`

- [ ] **Step 1: Tighten guardrail wording in `SKILL.md`**

In the competitor collection section, replace:

```markdown
- `relevanceTerms`: short terms used only to filter obvious mismatches and score title/category relevance. Relevance is a guardrail, not the main ranking brain.
```

With:

```markdown
- `relevanceTerms`: short terms used to reject obvious mismatches before final ranking and to score title/category relevance. Relevance is a guardrail, not the main ranking brain.
```

Add this bullet under the script ranking bullets:

```markdown
     - reject candidates whose title and BSR categories do not match `relevanceTerms` or `targetCategories`, even if they have strong BSR or bought-past-month signals
```

- [ ] **Step 2: Tighten guardrail wording in `scraping-strategy.md`**

Replace:

```markdown
Use relevance primarily as a guardrail against wrong products. Do not let title keyword overlap outrank strong category-level BSR and bought-past-month signals.
```

With:

```markdown
Use relevance as a hard guardrail against wrong products before ranking. A candidate should pass through when its title or BSR category matches `relevanceTerms` or `targetCategories`. Do not let an unrelated product win only because it has strong BSR or bought-past-month signals. Among relevant products, do not let weak title keyword overlap outrank strong matching-category BSR and bought-past-month signals.
```

- [ ] **Step 3: Commit**

Run:

```powershell
git add skills/amazon-listing-auto-copywriter/SKILL.md skills/amazon-listing-auto-copywriter/references/scraping-strategy.md
git commit -m "docs: clarify competitor relevance guardrail"
```

---

### Task 8: Final Verification And Upload Package

**Files:**
- Verify: entire repo
- Create/update outside git: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\maimeng-skill-repo-upload.zip`
- Optional create outside git: `C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\Amazon Listing 自动文案 Skill 使用手册.docx`

- [ ] **Step 1: Run self-test**

Run:

```powershell
$env:PYTHONIOENCODING='utf-8'; python 'skills\amazon-listing-auto-copywriter\scripts\self_test.py'
```

Expected:

```text
self_test: OK
```

- [ ] **Step 2: Run targeted behavior smoke test**

Run:

```powershell
@'
import sys
sys.path.insert(0, r'skills\amazon-listing-auto-copywriter\scripts')
from amazon_collect_brief import normalize_marketplace, rank_candidates
print(normalize_marketplace("德国站")["code"])
items = [
    {'asin':'BAD','title':'Dog Chew Toy for Aggressive Chewers','query':'highlighter pens','boughtInPastMonth':20000,'hasBoughtSignal':True,'bestSellerRanks':[{'rank':1,'category':'Pet Supplies'}],'rating':4.8,'reviews':50000,'bulletCount':5,'price':'9.99','imageCount':8},
    {'asin':'GOOD','title':'Chisel Tip Highlighter Pens Assorted Colors','query':'highlighter pens','boughtInPastMonth':None,'hasBoughtSignal':False,'bestSellerRanks':[],'rating':4.5,'reviews':500,'bulletCount':5,'price':'6.99','imageCount':8},
]
print([x['asin'] for x in rank_candidates(items, ['highlighter','chisel tip'], ['Liquid Highlighters'], 2)])
'@ | python -
```

Expected:

```text
DE
['GOOD']
```

- [ ] **Step 3: Confirm no generated manuals are tracked**

Run:

```powershell
git status --short
git ls-files | Select-String -Pattern '\.docx$|\.pdf$'
```

Expected:

```text
No tracked .docx or .pdf files.
```

- [ ] **Step 4: Rebuild upload zip from git HEAD**

Run:

```powershell
git archive --format=zip -o '..\maimeng-skill-repo-upload.zip' HEAD
```

Expected:

```text
maimeng-skill-repo-upload.zip exists and does not contain generated docx/pdf manuals.
```

Check:

```powershell
tar -tf '..\maimeng-skill-repo-upload.zip' | Select-String -Pattern '\.docx$|\.pdf$'
```

Expected:

```text
No output.
```

- [ ] **Step 5: Generate Word manual only if user asks**

If a Word manual is requested, generate it outside the git repo at:

```text
C:\Users\迈萌2\Documents\Codex\2026-05-21\https-skill-linkfox-com-cli-install\Amazon Listing 自动文案 Skill 使用手册.docx
```

Do not generate a PDF. Do not add the Word file to git.

- [ ] **Step 6: Final commit if verification changed files**

If any tracked file changed during final verification, run:

```powershell
git add <changed tracked files>
git commit -m "chore: finalize Amazon skill review fixes"
```

If nothing changed, do not create an empty commit.

---

## Self-Review

**Spec coverage:**  
This plan covers all review findings: Chinese marketplace routing, true relevance guardrail, DE localized parsing, Scrapling language forwarding, docs semantics, no PDF, and Word not tracked in git.

**Placeholder scan:**  
No `TBD`, `TODO`, or unspecified test instructions remain. Each task has exact files, code snippets, commands, and expected results.

**Type consistency:**  
New functions use existing `dict[str, Any]`, `list[dict[str, Any]]`, `list[str]`, and `FetchResult` patterns. `rank_candidates()` signature remains backward-compatible with the current changed version.

---

## Execution Options

Plan complete and saved to `docs/superpowers/plans/2026-05-22-amazon-skill-review-fixes.md`. Two execution options:

**1. Subagent-Driven (recommended)** - Dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints.
