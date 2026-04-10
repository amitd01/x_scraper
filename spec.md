# X Scraper & AI Newsletter Agent: Technical Specification

## 1. Core Design Principles
1. **Zero-Redundancy:** The system should never spend LLM tokens summarizing an article that was already processed in the past, regardless of who tweeted it or how many times it was retweeted.
2. **Deterministic Tracking:** Core logic should rely on deterministic state (`brain.json` & URL normalization) rather than unreliable chronological constraints (e.g., tweet creation time).
3. **Resiliency over Brittleness:** The pipeline gracefully handles broken links, paywalls, and cookie banners without throwing fatal errors.
4. **Contextual Nuance:** Over time, the newsletter transitions from simple isolated summaries to a cohesive context tree, recognizing themes across the user's reading history.

## 2. End-State Architecture

The fully realized application consists of a two-stage automated pipeline mediated by a persistent Knowledge Graph ("The Brain").

- **Stage 1: The Scraper (`scraper.py`)** 
  - Authenticates into X using GitHub Secrets/local cookies.
  - Recursively fetches the user's Bookmarks and Likes.
  - Queries `brain.json` to bypass previously parsed tweets, capping execution at ~50 unread items.
  - Outputs lightweight extraction `.csv` manifests.

- **Stage 2: The Digest Generator (`newsletter.py`)**
  - Resolves shortened `t.co` URLs and drops aggressively tracking parameters (URL Normalization).
  - Queries `brain.json` against resolved URLs.
  - If unseen: Triggers Playwright headless extraction, evaluates content, and requests Claude 3.5 LLM summarization.
  - If a research paper is detected, outputs *Approach & Findings*. Otherwise outputs a contextual digest.
  - Updates `brain.json` and transmits the final markdown/HTML digest via email.

## 3. The "Brain" (Memory System)
A structured `brain.json` stored in the repository and updated via GitHub Actions.
```json
{
  "seen_tweets": ["https://x.com/user/status/123", ...],
  "seen_articles": ["https://hackernoon.com/article-slug", ...],
  "topics": {
     "AI Agents": ["https://hackernoon.com/article-slug", ...] 
  }
}
```

## 4. Evaluation Framework
Robust evaluations (evals) ensure continuous pipeline health.

**Deterministic Evals**
- **URL Normalization Check:** Verify `example.com?utm=twitter` and `example.com` resolve to the identical `seen_articles` hash.
- **Paywall/Banner Resiliency:** Ensure `extract_text_from_url()` returns identifiable errors instead of extracting standard "Please enable cookies" boilerplate.
- **Circuit Breaker:** Assert the system forcefully halts execution if `brain.json` fails to load.

**Generative Evals (LLM-as-a-judge)**
- **Persona Check:** Evaluator model confirms if research paper summaries strictly follow the "Approach and Findings" template.
- **Hallucination Rate:** Evaluator model checks if the output summary invented facts not present in the extracted payload.

## 5. Sprint Execution Plan

### Sprint 1: Foundation & "The Brain" (Completed)
- Remove `cutoff_date` logic from `scraper.py`, replacing it with a deterministic ~50-item hard limit.
- Introduce `brain.json` implementation to track `seen_tweets` and `seen_articles`.
- Add simple URL normalization to strip UTM parameters.
- Update `scraper.yml` to automatically `git commit` and push `brain.json` back to `main`.

### Sprint 2: Hardening & Deterministic Evals (Completed)
- Implement strict error boundaries around Playwright extractions (recognizing cookie banners or broken sites).
- Improve Python console logging to clarify exactly why a tweet was skipped.
- Native `pypdf` integration utilizing dual-route extraction to bypass headless rendering of PDFs.

### Sprint 3: Enhanced Prompts & Generative Evals (Completed)
- Revise the Claude prompt inside `newsletter.py` to handle edge cases including standalone raw text tweets natively over 400 characters.
- Introduce a lightweight LLM-as-a-judge eval script (`eval_hallucinations.py`) in the repository to continuously monitor hallucination and formatting compliance.

### Sprint 4: "Contextual Nuance" & Clustering (Completed)
- Evolve `brain.json` into semantic topic clusters extracting the real summaries.
- The LLM prompt injects prior context to dynamically contrast new inputs iteratively.
- Newsletters formulate coherent "Chapters" grouping data categorically.

**Future Review Note:** Managing Bloatware in Memory and Context Retrieval. As `brain.json` scales over time, the `topics` storage will exponentially increase the token overhead of context injection. Future iterations must implement rigorous strategies like vectorized embeddings (RAG), strict time-based TTL limits (e.g., dropping summaries older than 90 days), or multi-layered summarization of the summaries to combat "context bloatware".
