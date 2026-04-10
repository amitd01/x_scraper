# Sprint 4 Implementation Plan: Contextual Nuance & Semantic Clustering

This final sprint transforms the newsletter from a disconnected list of bullet points into a cohesive, historically-aware narrative.

## Proposed Architecture

### 1. Evolving `brain.json` Storage
Currently, the `"topics": {}` stub in `brain.json` is empty. We will enrich this by saving not just the URL, but the actual finalized summary in a categorized key structure. 
- *Target Structure:*
  ```json
  "topics": {
    "AI Agents": [
       {"url": "example.com/ai", "summary": "AI agents are replacing..."}
    ],
    "Venture Capital": [
       {"url": "...", "summary": "..."}
    ]
  }
  ```

### 2. Upgrading `newsletter.py` and the Generative Prompt
Extracting summaries will transition into a two-tiered system:
- **Injection:** Before calling Claude 3.5 Sonnet, the Python script will inject the current `topics` keys (e.g. "Currently tracked topics: AI Agents, Venture Capital, Startups").
- **Classification & Synthesis Prompting:** Claude will now be instructed to output its summarized findings in a predictable JSON layout:
  ```json
  {
    "topic_category": "AI Agents",
    "summary": "This article discusses..." 
  }
  ```
- **Context Injection:** When we fetch the prompt for Claude, we will inject **last week's summaries of the matched topic**. The new prompt instruction will state: *"We have previously read [X]. How does this new article contrast, update, or challenge our prior knowledge on this specific topic?"*

#### [MODIFY] [newsletter.py](file:///Users/amitdas/Downloads/WIP%20Work/Antigravity/x_scraper/newsletter.py)
We will rewrite the drafting loop at the bottom of the script. Instead of iterating `results` chronologically, the newsletter markdown generator will group insights by `topic_category` to create thematic "chapters" in the final email.

## Verification Plan
1. We will reset `brain.json` topics and feed it two separate tweets chronologically related to the same topic (e.g., two tweets about OpenAI).
2. We will evaluate the final `Newsletter_YYYY-MM-DD.md` output to guarantee the secondary tweet references the context of the first tweet.
3. Verify that `topics` populated dynamically in `brain.json`.

## User Review Required
> [!IMPORTANT]
> Injecting past summaries into the prompt will consume more context tokens. I will institute a "sliding window" (e.g., retrieving only the 3 most recent summaries for a given topic) to prevent context bloat and out-of-control API scaling costs.

Does this semantic clustering approach align completely with your vision for Sprint 4?
