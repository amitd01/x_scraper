# Sprint 4 Task Tracking

- [ ] Update `spec.md`
    - [ ] Add bloatware management note for future
- [x] Update `newsletter.py` Prompts
    - [x] Inject existing topics from `brain.json`
    - [x] Inject last 3 summaries from the relevant topic
    - [x] Instruct Claude to output JSON (`topic_category` and `summary`)
- [x] Update `newsletter.py` Parsing
    - [x] Safely parse the JSON response from Claude
    - [x] Append the summary content explicitly back into `brain.json` under `topics`
    - [x] Group final markdown drafting visually by Chapters
- [x] Verification
    - [x] Execute `newsletter.py` to ensure it successfully clusters and generates the relational summary
