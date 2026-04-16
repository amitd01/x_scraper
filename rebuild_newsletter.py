"""
Rebuild and re-send a newsletter from brain.json without re-scraping or re-calling the LLM.

Use case: yesterday's scheduled run scraped + summarized successfully but the SMTP delivery
failed (see learnings.md #7). The summaries are already persisted in brain.json's `topics`
section; this script diffs the current brain.json against a prior git revision, extracts
the entries added between the two, and emails them using newsletter.py's send_email().

Usage:
    python rebuild_newsletter.py                    # diff against the commit before the most recent brain.json change
    python rebuild_newsletter.py --since b293376    # diff an explicit SHA
    python rebuild_newsletter.py --dry-run          # print markdown, skip email
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime

import markdown

BRAIN_FILE = "brain.json"


def load_brain_at(ref):
    """Load brain.json at a given git ref. Returns {} if the file didn't exist there."""
    try:
        raw = subprocess.check_output(
            ["git", "show", f"{ref}:{BRAIN_FILE}"],
            stderr=subprocess.DEVNULL,
        ).decode()
        return json.loads(raw)
    except subprocess.CalledProcessError:
        return {}


def default_since_ref():
    """Return the commit SHA immediately before the most recent change to brain.json.

    Using 'HEAD~1' as a default is brittle: once non-brain commits (e.g. code fixes,
    merge commits) land on top of the last bot commit, 'HEAD~1' no longer points at
    a brain.json change and the diff produces nothing. Instead we ask git for the
    two most recent commits that actually touched brain.json and return the older
    one — that's always the correct "prior brain.json state" for recovery.
    """
    try:
        out = subprocess.check_output(
            ["git", "log", "-n", "2", "--format=%H", "--", BRAIN_FILE],
            stderr=subprocess.DEVNULL,
        ).decode().strip().splitlines()
        if len(out) >= 2:
            return out[1]
    except subprocess.CalledProcessError:
        pass
    return "HEAD~1"


def load_brain_current():
    with open(BRAIN_FILE, "r") as f:
        return json.load(f)


def diff_topics(prior, current):
    """Return {topic: [entries]} containing entries present in `current` but not `prior`.

    Matches on URL within each topic so re-ordering doesn't produce false positives.
    """
    new_by_topic = {}
    prior_topics = prior.get("topics", {})
    for topic, entries in current.get("topics", {}).items():
        prior_urls = {e.get("url") for e in prior_topics.get(topic, [])}
        fresh = [e for e in entries if e.get("url") not in prior_urls]
        if fresh:
            new_by_topic[topic] = fresh
    return new_by_topic


def build_markdown(new_by_topic):
    date_str = datetime.now().strftime("%Y-%m-%d")
    md = f"# 🗞️ X/Twitter Contextual Digest (Rebuild)\n"
    md += f"**Generated on:** {date_str}\n\n"
    md += (
        "_This digest was reconstructed from cached summaries in `brain.json` "
        "after an SMTP delivery failure. The original tweet metadata "
        "(author, source, raw text) was not persisted, so only the URL and "
        "synthesis are shown per entry._\n\n"
    )
    md += "---\n\n"

    for topic, entries in new_by_topic.items():
        md += f"## 📚 Chapter: {topic}\n\n"
        for idx, entry in enumerate(entries, 1):
            md += f"### {idx}. [{entry.get('url', '(no url)')}]({entry.get('url', '#')})\n\n"
            md += f"**Contextual Synthesis & Findings:**\n\n"
            md += f"{entry.get('summary', '(no summary)')}\n\n"
        md += "---\n\n"
    return md


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--since",
        default=None,
        help="Git ref to diff brain.json against. Defaults to the commit immediately before the most recent brain.json change (auto-detected from git log).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the markdown and skip sending the email",
    )
    args = parser.parse_args()

    since_ref = args.since or default_since_ref()
    if not args.since:
        print(f"Auto-detected --since={since_ref} (commit before the most recent brain.json change)")

    prior = load_brain_at(since_ref)
    current = load_brain_current()

    new_by_topic = diff_topics(prior, current)
    total = sum(len(v) for v in new_by_topic.values())

    if total == 0:
        print(f"No new topic entries between {since_ref} and HEAD — nothing to rebuild.")
        return 0

    print(
        f"Rebuilding newsletter from {total} cached summaries across "
        f"{len(new_by_topic)} chapter(s) (diff: {since_ref}..HEAD):"
    )
    for topic, entries in new_by_topic.items():
        print(f"  📚 {topic}: {len(entries)} entries")

    md_content = build_markdown(new_by_topic)

    date_str = datetime.now().strftime("%Y-%m-%d")
    md_filename = f"Newsletter_Rebuild_{date_str}.md"
    with open(md_filename, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"\n✅ Rebuilt markdown written to: {md_filename}")

    if args.dry_run:
        print("--dry-run: skipping email send.")
        return 0

    # Lazy import so --dry-run works even if newsletter.py's heavier deps
    # (playwright / pypdf / anthropic) aren't installed in the local env.
    from newsletter import send_email

    html_content = markdown.markdown(md_content)
    send_email(html_content, md_content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
