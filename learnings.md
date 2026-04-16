# Architectural Learnings & Bug Index

This document tracks all foundational bugs, edge cases, and design constraints encountered while scaling the X Scraper & AI Newsletter Agent. 
It preserves these learnings so future iterations do not functionally regress or repeat past architectural errors.

---

### 1. GitHub Actions Permissions Failure (Exit Code 128 / HTTP 403)
- **The Bug:** By default, GitHub Actions workflows orchestrating the `GITHUB_TOKEN` only operate with generic `read` privileges unless specifically overridden. When `scraper.yml` attempted to push changes to the `brain.json` state map back to the `main` branch, GitHub aggressively rejected the transaction throwing a fatal Access Denied (403) code.
- **The Fix:** Hard-declared the write layer at the job level inside `.github/workflows/scraper.yml` using:
  ```yaml
  permissions:
    contents: write
  ```

### 2. Generative JSON Syntax Crashes (Unterminated String)
- **The Bug:** When the Claude 3.5 Sonnet LLM outputted its forced conversational summaries, it frequently generated unescaped internal control characters or errant newlines (e.g. carriage returns inside quote tags). The python `json.loads` module is extremely strict by default and threw a fatal `json.decoder.JSONDecodeError` crash.
- **The Fix:** Loosened the JSON parser's inherent strictness in `newsletter.py` by configuring `json.loads(response_text, strict=False)`. This allowed Python to dynamically tolerate invalid control characters embedded inside otherwise perfectly valid JSON structures.

### 3. Chronological Filtering Blindspots (Timestamp Mismatches)
- **The Bug:** The original `scraper.py` utilized a 3-day time filter. However, X only exports the `created_at` timestamp of the *tweet itself*, not the time the user actually *Liked* it. Consequently, if the user liked a tweet today that was originally posted 4 days ago, the script would prematurely terminate and permanently ignore the article.
- **The Fix:** Eliminated arbitrary chronological bounding entirely. Migrated to a purely Stateful Execution mechanism using `brain.json` tracking exactly what was seen coupled with a hard numerical extraction limit (~50 items per batch).

### 4. Playwright PDF Render Timeouts
- **The Bug:** Attempting to direct `async_playwright` headless instances into URLs hosting raw PDFs natively caused execution hangs, erratic rendering downloads, or outright total timeouts (as there isn't a typical DOM to evaluate).
- **The Fix:** Designed a "Dual-Route Extraction Protocol." Before booting up Playwright, the pipeline leverages the `requests` library to execute a lightweight `HEAD` peek at the URL. If `Content-Type: application/pdf` or `.pdf` extension is detected, the system safely bypasses headless rendering completely, fetching the byte stream and converting text natively via the `pypdf` module.

### 5. Infinite URL Duplication Loops (Tracking Parameters)
- **The Bug:** If an author shared an article as `example.com`, and a week later another author shared the *exact same article* as `example.com?utm_source=twitter&ref=social`, the script viewed them as two entirely disconnected entities and hallucinated redundant expensive AI summaries for both.
- **The Fix:** Wrote `normalize_url()` logic inside `newsletter.py` to aggressively strip common tracking parameters, enabling deterministic de-duplication inside the `seen_articles` tracker.

### 6. Summary Context Bloat 
- **The Architecture Constraint:** While feeding the prior 3 context summaries of a specific Topic Category directly back into Claude enables brilliant generative continuity, it presents a long-term API token bloat condition. 
- **Future Considerations:** The repository `spec.md` officially acknowledges the future requirement to migrate to a scalable Time-To-Live (TTL) memory drop, or vectorized RAG extraction when token generation costs aggressively hit thresholds.

### 7. Gmail SMTP Auth Failure (535 '5.7.8 Username and Password not accepted')
- **The Bug:** Google displays freshly generated App Passwords formatted with spaces for readability (e.g. `abcd efgh ijkl mnop`). When a user copied the string verbatim into the `GMAIL_APP_PASSWORD` GitHub Secret, the embedded whitespace was forwarded as-is to `smtplib.SMTP.login()`, and Gmail's SMTP endpoint rejected the credentials with a `535 5.7.8` authentication error. To make matters worse, the previous `except Exception` block swallowed the auth error silently and let `newsletter.py` exit 0, so the workflow's `Alert Failure` step never fired — the scraper appeared to "succeed" while never delivering the newsletter. The dead-code check `if GMAIL_APP_PASSWORD == "PUT_YOUR_APP_PASSWORD_HERE"` also didn't match any real placeholder (`.env.example` uses `"your_app_password"`), so the graceful-skip branch never triggered either.
- **The Fix:** At env-load time, normalize the secret with `"".join(value.split())` which strips leading/trailing whitespace AND inline spaces — collapsing `"  abcd efgh ijkl mnop  "` to the 16-character `"abcdefghijklmnop"` Gmail actually expects. Replaced the dead placeholder check with a real "unset or default" guard (`not GMAIL_APP_PASSWORD or SENDER_EMAIL == "your_email@gmail.com"`), added a dedicated `SMTPAuthenticationError` branch that re-raises after printing the most common root causes (regular password vs. App Password, 2FA not enabled, sender mismatch), and applied the same hygiene to `alert_failure.py` so the failure notifier itself can't fall victim to the same class of bug.
