# Personal AI Newsletter Agent

An autonomous intelligence pipeline that reads your Twitter/X activities (Likes and Bookmarks) and compiles them into a deeply synthesized, context-aware email newsletter using your choice of `GPT-4o` or `Claude-3.5-Sonnet`.

By organizing raw social media timelines into persistent semantic groupings, your newsletter becomes a continuous Knowledge Graph — dynamically reading newly saved tweets and contrasting them against past reads.

---

## 🚀 Features

- **Multi-Tenant LLM Support:** Use either OpenAI (`gpt-4o`) or Anthropic (`claude-3-5-sonnet`) by simply toggling an environment flag.
- **Paywall & PDF Evasion:** Leverages dual-route memory-buffer parsing (utilizing Playwright HTML extraction or `pypdf` native byte streaming) to bypass captchas securely.
- **Zero-Redundancy "Brain":** The local `brain.json` ensures you never receive an AI summary for the same article twice, even if the URL parameters change or it's tweeted by a different user.
- **Pure-Automation:** Fully deployable natively through GitHub Actions chron-jobs. No local server required.

---

## 🛠 Installation Guide

Because this repository is fully functional, you can fork it right now and set it up as your personal daily digest inside 5 minutes.

### 1. Fork this Repository
Click `Fork` in the top right to create your personal instance.

### 2. Configure GitHub Secrets
Navigate to your repository **Settings > Secrets and variables > Actions**.

You must create the following Repository Secrets mapped perfectly to the templates below. These act as the hidden remote values for your automated cloud runs:
- `SENDER_EMAIL` -> The Gmail address you are sending *from*.
- `RECEIVER_EMAIL` -> The email address you want to *read* the newsletter on.
- `GMAIL_APP_PASSWORD` -> Google strictly requires an App Password (not your core password). [Create one here](https://myaccount.google.com/apppasswords).
- `AI_PROVIDER` -> Type either `openai` or `anthropic`.
- `OPENAI_API_KEY` -> (If using `openai`) Your OpenAI API Key payload.
- `ANTHROPIC_API_KEY` -> (If using `anthropic`) Your Anthropic API Key payload.
- `X_COOKIES_JSON` -> Your exported Twitter cookies.

### 3. Local Execution (Optional)
If you prefer running this locally on your machine rather than through GitHub actions:
1. `source setup.sh` to install playwright, anthropic, openai, and pypdf dependencies.
2. Rename `.env.example` to `.env` and fill in your keys.
3. Run `python scraper.py` followed by `python newsletter.py`. 

### 4. Setting up the GitHub Cron Job
By default, the `.github/workflows/scraper.yml` is scheduled to automatically scrape your Twitter Likes/Bookmarks and drop the newsletter into your inbox twice a week at `02:30 UTC`. 

You can manually trigger it at any point by going to the `Actions` tab on GitHub, selecting "Scrape & Send Newsletter", and clicking **Run workflow**.
