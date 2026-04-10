# X Scraper & AI Newsletter Agent

An autonomous intelligence pipeline that reads your Twitter/X activities (Likes and Bookmarks) and compiles them into a deeply synthesized, context-aware newsletter via Claude 3.5 Sonnet.

## Architecture Highlights
- **Deterministic Edge-Extraction:** Uses Playwright for HTML pages and dual-route memory-buffer parsing for PDFs (using `pypdf`) to bypass paywalls securely. 
- **The Brain (`brain.json`):** Tracks your entire reading history to guarantee a Zero-Redundancy workflow and inject past memory context into semantic prompt evaluations.
- **Dynamic Routing:** Supports native extraction for long-form raw tweets (>400 chars) while ignoring shallow engagement tweets.
- **LLM-as-a-Judge Eval:** Features a standalone `eval_hallucinations.py` script that grades generated output for factual deviation to maintain an ironclad pipeline.

## Execution
This pipeline is designed to act completely autonomously via GitHub Actions. It runs on a cron schedule natively, logs in safely using encrypted stored cookies, extracts exactly up to ~50 novel units of data unread by the system, updates the knowledge graph, and commits the state variables right back to the `main` branch.

## Setup Locally
1. `source setup.sh` to install playwright, anthropic, and pypdf dependencies.
2. Ensure you have populated `.env` or set shell variables for `ANTHROPIC_API_KEY` and `GMAIL_APP_PASSWORD`.
3. Run `python scraper.py` followed by `python newsletter.py`. 
4. Check your email for the AI summary loop!
