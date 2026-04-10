# The Brain: Contextual Memory Engine

The X Scraper relies on `brain.json` to be the source-of-truth for its entity extraction process.

## Design
`brain.json` avoids infinite looping or expensive redundant LLM API calls by providing a strict barrier.

1. **`seen_tweets` (Exact Hash Tracker):**
   When `scraper.py` runs, it scans X for Liked and Bookmarked URLs. When one is successfully extracted, it is pushed here. The scraper will hard-stop iterating when it bounds into an already recorded tweet string.
 
2. **`seen_articles` (Underlying Root Tracker):**
   `newsletter.py` takes raw URLs sourced from X embeddings. It automatically resolves them, purges tracking parameters (like `?utm_source`), and documents the clean URL inside here. This guarantees that if a completely different user tweets the exact same article days later, your system catches it and rejects generating a redundant summary.

3. **`topics` (Knowledge Graph Hub):**
   The Claude 3.5 model automatically analyzes new articles and tags them dynamically against an array of established Semantic Topic keys (e.g. `AI Agents`, `Venture Capital`, `Startups`). 
   It then logs the finalized generated summary back under that Topic Header array list directly within `brain.json`.

## Performance Constraints
**Context Tokens Bloatware Note:**
As the system uses the 3 most recently summarized documents on any given matched topic to prime the LLM prompt for relational output ("Compare this new AI article against the prior AI summary we evaluated"), the system relies on linear string injection. As time goes on, to strictly curb API bloat and scaling limits, the Knowledge Graph is currently gated behind slicing constraints. 

In future states, transitioning the `topics` field into an embedded vector approach or introducing a 90-day memory TTL (time-to-live) purge will be necessary.
