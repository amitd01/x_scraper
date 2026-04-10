import asyncio
import csv
import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

from playwright.async_api import async_playwright
import anthropic
import markdown
import requests
import io
import pypdf

# Email Configuration
SENDER_EMAIL = "amitdas@gmail.com"
RECEIVER_EMAIL = "amit.das@think360.ai"
# You'll need a Gmail App Password, NOT your regular password.
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "pdxo suuj selu yndk")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "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")
client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

BRAIN_FILE = "brain.json"

def load_brain():
    if os.path.exists(BRAIN_FILE):
        try:
            with open(BRAIN_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {"seen_tweets": [], "seen_articles": [], "topics": {}}

def save_brain(data):
    with open(BRAIN_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def normalize_url(url):
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    keys_to_remove = [k for k in qs if k.startswith('utm_') or k == 'ref']
    for k in keys_to_remove:
        del qs[k]
    new_query = urlencode(qs, doseq=True)
    return urlunparse(parsed._replace(query=new_query))

import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

async def extract_text_from_url(page, url):
    try:
        # First check headers to find out the real URL and content type using requests
        resp = requests.head(url, allow_redirects=True, timeout=15, verify=False)
        content_type = resp.headers.get('Content-Type', '').lower()
        actual_url = resp.url
        
        # If it's a PDF, bypass Playwright entirely
        if 'application/pdf' in content_type or actual_url.lower().endswith('.pdf'):
            print(f"    📄 PDF Detected. Downloading and parsing byte stream...")
            pdf_resp = requests.get(actual_url, timeout=30, verify=False)
            pdf_resp.raise_for_status()
            reader = pypdf.PdfReader(io.BytesIO(pdf_resp.content))
            text_blocks = []
            for i, pdf_page in enumerate(reader.pages):
                page_text = pdf_page.extract_text()
                if page_text:
                    text_blocks.append(page_text)
            
            extracted_text = "\n".join(text_blocks)
            return extracted_text[:20000], actual_url

        # Otherwise, proceed with Playwright for HTML
        await page.goto(actual_url, wait_until="domcontentloaded", timeout=15000)
        await page.wait_for_timeout(2000)
        text = await page.evaluate("document.body.innerText")
        return text, actual_url
    except Exception as e:
        print(f"    ⚠️ Failed to fetch {url}: {e}")
        return "", url

def generate_summary(text, url, brain_data, is_tweet_only=False):
    if not text.strip():
        return {"topic_category": "Uncategorized", "summary": "Could not extract readable content from the page."}

    existing_topics = list(brain_data.get("topics", {}).keys())
    topics_context_str = ", ".join(existing_topics) if existing_topics else "None yet"
    
    prior_context_str = ""
    all_past = []
    for t_list in brain_data.get("topics", {}).values():
        all_past.extend(t_list)
    
    if all_past:
        prior_context_str = "PREVIOUS SUMMARIES (Use these to connect themes globally!):\n"
        for past_item in all_past[-3:]:
             prior_context_str += f"- {past_item['summary'][:200]}...\n"

    base_instruction = f"""
    You are an expert research assistant organizing an ongoing newsletter into a Knowledge Graph. 
    CURRENT TRACKED TOPIC CHAPTERS: {topics_context_str}
    
    {prior_context_str}
    
    INSTRUCTIONS:
    1. Determine the single most applicable 'topic_category' for this text. You can reuse an existing chapter or create a concise new one (e.g. 'Startups', 'AI Agents').
    2. Summarize the text. If it overlaps with any PREVIOUS SUMMARIES, explicitly state how it updates, contrasts, or adds to that prior perspective! Use conversational nuance.
    3. Output EXCLUSIVELY in valid JSON format in exactly this structure:
    {{
        "topic_category": "Topic Name",
        "summary": "Your detailed synthesis here..."
    }}
    """
    
    if is_tweet_only:
        prompt = f"""
        {base_instruction}
        4. Since this is a raw tweet excerpt, explicitly summarize the core narrative under 150 words.
        
        TWEET TO SUMMARIZE:
        {text[:20000]} 
        """
    else:
        prompt = f"""
        {base_instruction}
        4. If it's a research paper, ensure you explicitly state **APPROACH** and **FINDINGS**. Otherwise write a cohesive ~250-word contextual synthesis.
        
        TEXT TO SUMMARIZE:
        {text[:20000]} 
        """
    
    try:
        message = client.messages.create(
            model="claude-sonnet-4-6", 
            max_tokens=600,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        response_text = message.content[0].text
        
        if "```json" in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif "```" in response_text:
            response_text = response_text.split('```')[1].strip()
            
        return json.loads(response_text)
    except Exception as e:
        print(f"Error generating summary or parsing JSON: {e}")
        return {"topic_category": "Uncategorized", "summary": "Error generating summary"}

def send_email(html_content, markdown_content):
    if GMAIL_APP_PASSWORD == "PUT_YOUR_APP_PASSWORD_HERE":
        print("\n⚠️  Skipping email sending: Please put your Gmail App Password in newsletter.py to enable email delivery.")
        return
        
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Your Recent X Highlights'
        msg['From'] = SENDER_EMAIL
        msg['To'] = RECEIVER_EMAIL

        part1 = MIMEText(markdown_content, 'plain')
        
        # Adding some basic CSS to the HTML to make it look like a professional newsletter
        html_template = f"""
        <html>
          <head>
            <style>
              body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; background-color: #f4f6f8; }}
              .container {{ background-color: #ffffff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }}
              h1 {{ color: #1DA1F2; border-bottom: 2px solid #1DA1F2; padding-bottom: 10px; }}
              h2 {{ color: #2C3E50; margin-top: 30px; }}
              h3 {{ color: #34495E; font-size: 1.1em; }}
              a {{ color: #1DA1F2; text-decoration: none; }}
              blockquote {{ border-left: 4px solid #1DA1F2; margin: 20px 0; padding: 15px 20px; color: #555; background: #f8fafc; border-radius: 0 4px 4px 0; font-style: italic; }}
              hr {{ border: 0; border-top: 1px solid #eaeaea; margin: 30px 0; }}
              .footer {{ text-align: center; margin-top: 40px; font-size: 0.85em; color: #888; }}
            </style>
          </head>
          <body>
            <div class="container">
              {html_content}
              <div class="footer">
                Automated by Antigravity X Scraper Pipeline
              </div>
            </div>
          </body>
        </html>
        """
        part2 = MIMEText(html_template, 'html')

        msg.attach(part1)
        msg.attach(part2)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, GMAIL_APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print("✅ Email transmitted successfully to " + RECEIVER_EMAIL + "!")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

async def main():
    brain_data = load_brain()
    
    print("Reading X Data CSVs...")
    items = []
    
    for filename in ['bookmarks.csv', 'likes.csv']:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # check if embedded_links exists and is not empty
                    if row.get('embedded_links'):
                        links = [l.strip() for l in row['embedded_links'].split(',') if l.strip()]
                        if links:
                            row['links_list'] = links
                            row['source'] = filename.replace('.csv', '').capitalize()
                            items.append(row)
                    else:
                        # Pure text tweet logic
                        if len(row.get('text', '')) > 400:
                            row['links_list'] = []  # No external links
                            row['source'] = filename.replace('.csv', '').capitalize()
                            items.append(row)
                        
    if not items:
        print("No items with embedded links found in the CSVs.")
        print("Make sure you run scraper.py first!")
        return
        
    print(f"Found {len(items)} tweets with embedded links.")
    
    results = []
    
    async with async_playwright() as p:
        # We'll run this headless since we don't need to log in to read random web articles
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        for idx, item in enumerate(items, 1):
            print(f"\n[{idx}/{len(items)}] Processing tweet by {item['author']} from {item['source']}...")
            summaries = []
            
            if item.get('links_list'):
                for link in item['links_list']:
                    print(f"  -> Fetching link: {link}")
                    text, actual_url = await extract_text_from_url(page, link)
                    
                    norm_url = normalize_url(actual_url)
                    if norm_url in brain_data.get("seen_articles", []):
                        print(f"  -> Skipping [Already Summarized Previously]: {norm_url}")
                        continue
                    
                    print(f"  -> Generating AI summary for: {actual_url}")
                    summary_data = generate_summary(text, actual_url, brain_data)
                    
                    summaries.append({
                        'original_url': link,
                        'actual_url': norm_url,
                        'topic_category': summary_data.get('topic_category', 'Uncategorized'),
                        'summary': summary_data.get('summary', 'Error')
                    })
                    
                    cat = summary_data.get('topic_category', 'Uncategorized')
                    brain_data.setdefault("topics", {}).setdefault(cat, []).append({
                        "url": norm_url,
                        "summary": summary_data.get('summary', 'Error')
                    })
                    
                    brain_data.setdefault("seen_articles", []).append(norm_url)
            else:
                # Text-only tweet > 400 chars
                tweet_url = item['url']
                norm_url = normalize_url(tweet_url)
                if norm_url in brain_data.get("seen_articles", []):
                    print(f"  -> Skipping [Already Summarized Text Tweet]: {norm_url}")
                    continue
                    
                print(f"  -> Generating AI summary for pure long-form text tweet: {tweet_url}")
                summary_data = generate_summary(item['text'], tweet_url, brain_data, is_tweet_only=True)
                
                summaries.append({
                    'original_url': tweet_url,
                    'actual_url': norm_url,
                    'topic_category': summary_data.get('topic_category', 'Uncategorized'),
                    'summary': summary_data.get('summary', 'Error')
                })
                
                cat = summary_data.get('topic_category', 'Uncategorized')
                brain_data.setdefault("topics", {}).setdefault(cat, []).append({
                    "url": norm_url,
                    "summary": summary_data.get('summary', 'Error')
                })
                
                brain_data.setdefault("seen_articles", []).append(norm_url)
            
            if summaries:
                item['summaries'] = summaries
                results.append(item)
            else:
                print(f"  -> Skipping Tweet: Existing content already processed in the past.")
                
        await browser.close()
        
    # Save brain after processing all links
    save_brain(brain_data)
        
    if not results:
        print("\nNo new articles to summarize. All links were already present in brain.json.")
        return
        
    date_str = datetime.now().strftime("%Y-%m-%d")
    md_filename = f"Newsletter_{date_str}.md"
    
    print("\nDrafting Newsletter...")
    md_content = f"# 🗞️ X/Twitter Contextual Digest\n"
    md_content += f"**Generated on:** {date_str}\n\n"
    md_content += "---\n\n"
    
    chapters = {}
    for item in results:
        for summary_info in item['summaries']:
            cat = summary_info['topic_category']
            chapters.setdefault(cat, []).append({
                'tweet_url': item['url'],
                'author': item['author'],
                'source': item['source'],
                'tweet_text': item['text'],
                'actual_url': summary_info['actual_url'],
                'summary': summary_info['summary']
            })
            
    for topic, entries in chapters.items():
        md_content += f"## 📚 Chapter: {topic}\n\n"
        for idx, entry in enumerate(entries, 1):
            url_display = entry['actual_url'] if entry['actual_url'] else entry['tweet_url']
            md_content += f"### {idx}. Tweet by {entry['author']} ({entry['source']})\n"
            md_content += f"**Source Info:** [Original Tweet]({entry['tweet_url']}) | [Actual URL]({url_display})\n\n"
            
            form_text = entry['tweet_text'].replace('\n', '\n> ')
            md_content += f"> {form_text}\n\n"
            
            md_content += f"**Contextual Synthesis & Findings:**\n\n"
            md_content += f"{entry['summary']}\n\n"
        md_content += "---\n\n"
        
    with open(md_filename, 'w', encoding='utf-8') as f:
        f.write(md_content)
            
    print(f"\n✅ Newsletter successfully generated locally: {md_filename}")
    
    # Convert to HTML and send email
    print("Formatting email HTML...")
    html_content = markdown.markdown(md_content)
    send_email(html_content, md_content)

if __name__ == "__main__":
    asyncio.run(main())
